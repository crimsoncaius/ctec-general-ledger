import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.deps import AccessContext, DbSession, require
from app.models import JournalBatch, JournalEntry
from app.schemas import (
    BulkJournalRequest,
    BulkResult,
    JournalBatchCreate,
    JournalBatchOut,
    JournalEntryOut,
    ReversalRequest,
)
from app.services.accounting import (
    approve_batch,
    copy_batch,
    create_batch,
    delete_draft_batch,
    load_batch,
    post_batch,
    replace_draft_batch,
    reverse_entry,
    transition_validate,
)

router = APIRouter(prefix="/journals", tags=["journals"])


@router.get("", response_model=list[JournalBatchOut])
def list_batches(
    db: DbSession, context: AccessContext = Depends(require("journals.view"))
) -> list[JournalBatch]:
    ids = db.scalars(
        select(JournalBatch.id)
        .where(JournalBatch.company_id == context.company_id)
        .order_by(JournalBatch.created_at.desc())
        .limit(100)
    ).all()
    return [load_batch(db, context.company_id, batch_id) for batch_id in ids]


@router.post("", response_model=JournalBatchOut, status_code=201)
def add_batch(
    payload: JournalBatchCreate,
    db: DbSession,
    context: AccessContext = Depends(require("journals.create")),
) -> JournalBatch:
    return create_batch(db, company_id=context.company_id, user_id=context.user.id, payload=payload)


@router.get("/{batch_id}", response_model=JournalBatchOut)
def get_batch(
    batch_id: uuid.UUID,
    db: DbSession,
    context: AccessContext = Depends(require("journals.view")),
) -> JournalBatch:
    return load_batch(db, context.company_id, batch_id)


@router.put("/{batch_id}", response_model=JournalBatchOut)
def update_batch(
    batch_id: uuid.UUID,
    payload: JournalBatchCreate,
    db: DbSession,
    context: AccessContext = Depends(require("journals.update")),
) -> JournalBatch:
    return replace_draft_batch(
        db,
        company_id=context.company_id,
        batch_id=batch_id,
        user_id=context.user.id,
        payload=payload,
    )


@router.delete("/{batch_id}", status_code=204)
def delete_batch(
    batch_id: uuid.UUID,
    db: DbSession,
    context: AccessContext = Depends(require("journals.delete")),
) -> None:
    delete_draft_batch(db, context.company_id, batch_id, context.user.id)


@router.post("/{batch_id}/copy", response_model=JournalBatchOut, status_code=201)
def copy_batch_route(
    batch_id: uuid.UUID,
    db: DbSession,
    context: AccessContext = Depends(require("journals.create")),
) -> JournalBatch:
    return copy_batch(db, context.company_id, batch_id, context.user.id)


@router.post("/{batch_id}/validate", response_model=JournalBatchOut)
def validate_batch_route(
    batch_id: uuid.UUID,
    db: DbSession,
    context: AccessContext = Depends(require("journals.validate")),
) -> JournalBatch:
    return transition_validate(db, context.company_id, batch_id, context.user.id)


@router.post("/{batch_id}/approve", response_model=JournalBatchOut)
def approve_batch_route(
    batch_id: uuid.UUID,
    db: DbSession,
    context: AccessContext = Depends(require("journals.approve")),
) -> JournalBatch:
    return approve_batch(
        db,
        context.company_id,
        batch_id,
        context.user.id,
        "journals.self_approve" in context.capabilities,
    )


@router.post("/{batch_id}/post", response_model=JournalBatchOut)
def post_batch_route(
    batch_id: uuid.UUID,
    db: DbSession,
    context: AccessContext = Depends(require("journals.post")),
) -> JournalBatch:
    return post_batch(db, context.company_id, batch_id, context.user.id)


@router.get("/entries/inquiry", response_model=list[JournalEntryOut])
def entry_inquiry(
    db: DbSession,
    account_id: uuid.UUID | None = None,
    context: AccessContext = Depends(require("journals.inquire")),
) -> list[JournalEntry]:
    statement = (
        select(JournalEntry)
        .where(JournalEntry.company_id == context.company_id)
        .order_by(JournalEntry.posting_date.desc(), JournalEntry.entry_no.desc())
        .limit(500)
    )
    if account_id is not None:
        statement = statement.where(JournalEntry.lines.any(account_id=account_id))
    return list(db.scalars(statement).all())


@router.post("/entries/{entry_id}/reverse", response_model=JournalBatchOut, status_code=201)
def reverse_entry_route(
    entry_id: uuid.UUID,
    payload: ReversalRequest,
    db: DbSession,
    context: AccessContext = Depends(require("journals.reverse")),
) -> JournalBatch:
    return reverse_entry(db, context.company_id, entry_id, context.user.id, payload)


@router.post("/bulk", response_model=BulkResult)
def bulk_journal_action(
    payload: BulkJournalRequest,
    db: DbSession,
    context: AccessContext = Depends(require("journals.view")),
) -> BulkResult:
    required = {
        "validate": "journals.validate",
        "approve": "journals.approve",
        "post": "journals.post",
    }[payload.action]
    if required not in context.capabilities:
        raise HTTPException(403, f"Capability required: {required}")
    succeeded: list[uuid.UUID] = []
    failed: list[dict[str, object]] = []
    for batch_id in payload.batch_ids:
        try:
            if payload.action == "validate":
                transition_validate(db, context.company_id, batch_id, context.user.id)
            elif payload.action == "approve":
                approve_batch(
                    db,
                    context.company_id,
                    batch_id,
                    context.user.id,
                    "journals.self_approve" in context.capabilities,
                )
            else:
                post_batch(db, context.company_id, batch_id, context.user.id)
            succeeded.append(batch_id)
        except HTTPException as exc:
            db.rollback()
            failed.append(
                {"batch_id": str(batch_id), "status": exc.status_code, "detail": exc.detail}
            )
        except Exception as exc:
            db.rollback()
            failed.append({"batch_id": str(batch_id), "status": 500, "detail": str(exc)})
    return BulkResult(succeeded=succeeded, failed=failed)
