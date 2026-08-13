import csv
import hashlib
import io
import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import TypedDict

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select

from app.deps import AccessContext, DbSession, require
from app.models import Account, AccountType, Currency, FiscalPeriod, OperationJob, RunStatus
from app.schemas import JournalBatchCreate, JournalEntryCreate, JournalLineCreate
from app.services.accounting import create_batch
from app.services.audit import record_audit

router = APIRouter(prefix="/imports", tags=["controlled imports"])
MAX_IMPORT_BYTES = 5 * 1024 * 1024


class ImportEntryHeader(TypedDict):
    entry_date: date
    posting_date: date
    fiscal_period_id: uuid.UUID
    reference: str
    description: str


async def _read_csv(upload: UploadFile) -> tuple[bytes, list[dict[str, str]]]:
    content = await upload.read(MAX_IMPORT_BYTES + 1)
    if len(content) > MAX_IMPORT_BYTES:
        raise HTTPException(413, "Import file exceeds 5 MB")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(422, "CSV must be UTF-8 encoded") from exc
    try:
        return content, list(csv.DictReader(io.StringIO(text)))
    except csv.Error as exc:
        raise HTTPException(422, f"Invalid CSV: {exc}") from exc


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _prior_digest(db: DbSession, company_id: uuid.UUID, kind: str, digest: str) -> bool:
    jobs = db.scalars(
        select(OperationJob).where(
            OperationJob.company_id == company_id,
            OperationJob.kind == kind,
            OperationJob.status == RunStatus.SUCCEEDED,
        )
    ).all()
    return any(job.parameters.get("source_digest") == digest for job in jobs)


def _account_rows(
    db: DbSession, company_id: uuid.UUID, rows: list[dict[str, str]], mode: str
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    currencies = set(db.scalars(select(Currency.code)).all())
    existing = {
        account.code: account
        for account in db.scalars(select(Account).where(Account.company_id == company_id)).all()
    }
    normalized: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows, start=2):
        try:
            code = row.get("code", "").strip()
            name = row.get("name", "").strip()
            account_type = AccountType(row.get("account_type", "").strip().lower())
            currency = row.get("currency_code", "").strip().upper()
            postable = row.get("postable", "true").strip().lower() in {"1", "true", "yes", "y"}
            if not code or not name:
                raise ValueError("code and name are required")
            if code in seen:
                raise ValueError("duplicate code in file")
            if currency not in currencies:
                raise ValueError("unknown currency")
            if account_type == AccountType.TITLE:
                postable = False
            if code in existing and mode == "create":
                raise ValueError("account already exists")
            seen.add(code)
            normalized.append(
                {
                    "code": code,
                    "name": name,
                    "account_type": account_type,
                    "currency_code": currency,
                    "postable": postable,
                }
            )
        except (ValueError, KeyError) as exc:
            errors.append({"row": index, "message": str(exc), "data": row})
    return normalized, errors


@router.post("/accounts/preview")
async def preview_accounts(
    db: DbSession,
    file: UploadFile = File(...),
    mode: str = Query(default="create", pattern="^(create|upsert)$"),
    context: AccessContext = Depends(require("accounts.import")),
) -> dict[str, object]:
    content, rows = await _read_csv(file)
    normalized, errors = _account_rows(db, context.company_id, rows, mode)
    return {
        "source_digest": _digest(content),
        "rows": len(rows),
        "valid": len(normalized),
        "errors": errors,
        "sample": normalized[:20],
    }


@router.post("/accounts/apply")
async def apply_accounts(
    db: DbSession,
    file: UploadFile = File(...),
    mode: str = Query(default="create", pattern="^(create|upsert)$"),
    context: AccessContext = Depends(require("accounts.import")),
) -> dict[str, object]:
    content, rows = await _read_csv(file)
    digest = _digest(content)
    if _prior_digest(db, context.company_id, "account_import", digest):
        raise HTTPException(409, "This exact account file was already applied")
    normalized, errors = _account_rows(db, context.company_id, rows, mode)
    if errors:
        raise HTTPException(422, {"message": "Import validation failed", "errors": errors})
    try:
        created = updated = 0
        for values in normalized:
            account = db.scalar(
                select(Account).where(
                    Account.company_id == context.company_id, Account.code == values["code"]
                )
            )
            if account is None:
                db.add(Account(company_id=context.company_id, **values))
                created += 1
            else:
                account.name = str(values["name"])
                account.account_type = values["account_type"]  # type: ignore[assignment]
                account.currency_code = str(values["currency_code"])
                account.postable = bool(values["postable"])
                updated += 1
        job = OperationJob(
            company_id=context.company_id,
            kind="account_import",
            status=RunStatus.SUCCEEDED,
            requested_by_id=context.user.id,
            parameters={"source_digest": digest, "filename": file.filename, "mode": mode},
            progress=100,
            result={"created": created, "updated": updated, "rows": len(rows)},
        )
        db.add(job)
        record_audit(
            db,
            company_id=context.company_id,
            actor_id=context.user.id,
            action="import.accounts.applied",
            entity_type="operation_job",
            entity_id=str(job.id),
            metadata={"digest": digest, "created": created, "updated": updated},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"operation_id": job.id, **(job.result or {})}


def _journal_payload(
    db: DbSession, company_id: uuid.UUID, rows: list[dict[str, str]], filename: str
) -> tuple[JournalBatchCreate | None, list[dict[str, object]]]:
    accounts = {
        account.code: account.id
        for account in db.scalars(select(Account).where(Account.company_id == company_id)).all()
    }
    periods = {
        str(period.id): period
        for period in db.scalars(
            select(FiscalPeriod).where(FiscalPeriod.company_id == company_id)
        ).all()
    }
    grouped: dict[str, list[JournalLineCreate]] = defaultdict(list)
    headers: dict[str, ImportEntryHeader] = {}
    errors: list[dict[str, object]] = []
    for index, row in enumerate(rows, start=2):
        try:
            key = row.get("group_key", "").strip()
            account_code = row.get("account_code", "").strip()
            period_id = row.get("fiscal_period_id", "").strip()
            if not key or account_code not in accounts or period_id not in periods:
                raise ValueError(
                    "group_key, company account_code, and fiscal_period_id are required"
                )
            line = JournalLineCreate(
                account_id=accounts[account_code],
                description=row.get("line_description", "").strip(),
                currency_code=row.get("currency_code", "").strip().upper(),
                exchange_rate=Decimal(row.get("exchange_rate", "1")),
                debit=Decimal(row.get("debit", "0")),
                credit=Decimal(row.get("credit", "0")),
            )
            posting_date = date.fromisoformat(row.get("posting_date", ""))
            grouped[key].append(line)
            headers.setdefault(
                key,
                {
                    "entry_date": date.fromisoformat(row.get("entry_date", "")),
                    "posting_date": posting_date,
                    "fiscal_period_id": uuid.UUID(period_id),
                    "reference": row.get("reference", "").strip(),
                    "description": row.get("description", "").strip() or f"Imported {key}",
                },
            )
            if headers[key]["posting_date"] != posting_date:
                raise ValueError("all rows in a group must share posting_date")
        except (ValueError, InvalidOperation) as exc:
            errors.append({"row": index, "message": str(exc), "data": row})
    if errors:
        return None, errors
    try:
        entries = [
            JournalEntryCreate(
                entry_date=headers[key]["entry_date"],
                posting_date=headers[key]["posting_date"],
                fiscal_period_id=headers[key]["fiscal_period_id"],
                reference=headers[key]["reference"],
                description=headers[key]["description"],
                lines=lines,
            )
            for key, lines in grouped.items()
        ]
        return JournalBatchCreate(description=f"CSV import: {filename}", entries=entries), []
    except ValueError as exc:
        return None, [{"row": 0, "message": str(exc)}]


@router.post("/journals/preview")
async def preview_journals(
    db: DbSession,
    file: UploadFile = File(...),
    context: AccessContext = Depends(require("journals.import")),
) -> dict[str, object]:
    content, rows = await _read_csv(file)
    payload, errors = _journal_payload(db, context.company_id, rows, file.filename or "upload.csv")
    return {
        "source_digest": _digest(content),
        "rows": len(rows),
        "entries": len(payload.entries) if payload else 0,
        "errors": errors,
    }


@router.post("/journals/apply")
async def apply_journals(
    db: DbSession,
    file: UploadFile = File(...),
    context: AccessContext = Depends(require("journals.import")),
) -> dict[str, object]:
    content, rows = await _read_csv(file)
    digest = _digest(content)
    if _prior_digest(db, context.company_id, "journal_import", digest):
        raise HTTPException(409, "This exact journal file was already applied")
    payload, errors = _journal_payload(db, context.company_id, rows, file.filename or "upload.csv")
    if errors or payload is None:
        raise HTTPException(422, {"message": "Import validation failed", "errors": errors})
    try:
        batch = create_batch(
            db,
            company_id=context.company_id,
            user_id=context.user.id,
            payload=payload,
            commit=False,
        )
        job = OperationJob(
            company_id=context.company_id,
            kind="journal_import",
            status=RunStatus.SUCCEEDED,
            requested_by_id=context.user.id,
            parameters={"source_digest": digest, "filename": file.filename},
            progress=100,
            result={"batch_id": str(batch.id), "entries": len(payload.entries), "rows": len(rows)},
        )
        db.add(job)
        record_audit(
            db,
            company_id=context.company_id,
            actor_id=context.user.id,
            action="import.journals.applied",
            entity_type="journal_batch",
            entity_id=str(batch.id),
            metadata={"digest": digest, "rows": len(rows)},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"operation_id": job.id, **(job.result or {})}
