import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.deps import AccessContext, DbSession, require
from app.models import Account, AccountType, JournalEntry, JournalLine, JournalStatus
from app.schemas import AccountCreate, AccountOut, AccountUpdate
from app.services.audit import record_audit

router = APIRouter(prefix="/accounts", tags=["chart of accounts"])


@router.get("", response_model=list[AccountOut])
def list_accounts(
    db: DbSession, context: AccessContext = Depends(require("accounts.view"))
) -> list[Account]:
    return list(
        db.scalars(
            select(Account).where(Account.company_id == context.company_id).order_by(Account.code)
        ).all()
    )


@router.post("", response_model=AccountOut, status_code=201)
def create_account(
    payload: AccountCreate,
    db: DbSession,
    context: AccessContext = Depends(require("accounts.create")),
) -> Account:
    account = Account(company_id=context.company_id, **payload.model_dump())
    db.add(account)
    db.flush()
    record_audit(
        db,
        company_id=context.company_id,
        actor_id=context.user.id,
        action="account.created",
        entity_type="account",
        entity_id=str(account.id),
        after=payload.model_dump(mode="json"),
    )
    db.commit()
    return account


@router.put("/{account_id}", response_model=AccountOut)
def update_account(
    account_id: uuid.UUID,
    payload: AccountUpdate,
    db: DbSession,
    context: AccessContext = Depends(require("accounts.update")),
) -> Account:
    account = db.scalar(
        select(Account).where(Account.company_id == context.company_id, Account.id == account_id)
    )
    if account is None:
        raise HTTPException(404, "Account not found")
    if account.account_type == AccountType.TITLE and payload.postable:
        raise HTTPException(422, "Title accounts cannot be postable")
    if account.account_type == AccountType.RETAINED_EARNINGS and not payload.active:
        raise HTTPException(409, "Retained earnings cannot be deactivated")
    if account.active and not payload.active:
        pending = db.scalar(
            select(JournalLine.id)
            .join(
                JournalEntry,
                (JournalEntry.company_id == JournalLine.company_id)
                & (JournalEntry.id == JournalLine.entry_id),
            )
            .where(
                JournalLine.company_id == context.company_id,
                JournalLine.account_id == account.id,
                JournalEntry.status.in_(
                    [JournalStatus.DRAFT, JournalStatus.VALIDATED, JournalStatus.APPROVED]
                ),
            )
            .limit(1)
        )
        if pending is not None:
            raise HTTPException(409, "Account is referenced by an unposted journal")
    before = {"name": account.name, "postable": account.postable, "active": account.active}
    account.name = payload.name
    account.postable = payload.postable
    account.active = payload.active
    record_audit(
        db,
        company_id=context.company_id,
        actor_id=context.user.id,
        action="account.updated",
        entity_type="account",
        entity_id=str(account.id),
        before=before,
        after=payload.model_dump(),
    )
    db.commit()
    return account
