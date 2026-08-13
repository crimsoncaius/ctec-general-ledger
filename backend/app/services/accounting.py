import hashlib
import json
import uuid
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Account,
    AccountType,
    Company,
    FiscalPeriod,
    JournalBatch,
    JournalEntry,
    JournalLine,
    JournalStatus,
    NumberSequence,
    PeriodBalance,
    PeriodStatus,
    PostingEvent,
)
from app.schemas import JournalBatchCreate, ReversalRequest
from app.services.audit import record_audit


def quantize(value: Decimal, company: Company) -> Decimal:
    quantum = Decimal(1).scaleb(-company.rounding_places)
    rounding = ROUND_HALF_EVEN if company.use_bankers_rounding else ROUND_HALF_UP
    return value.quantize(quantum, rounding=rounding)


def next_number(db: Session, company_id: uuid.UUID, name: str, default_prefix: str) -> str:
    sequence = db.scalar(
        select(NumberSequence)
        .where(NumberSequence.company_id == company_id, NumberSequence.name == name)
        .with_for_update()
    )
    if sequence is None:
        sequence = NumberSequence(
            company_id=company_id, name=name, prefix=default_prefix, next_value=1, padding=6
        )
        db.add(sequence)
        db.flush()
    value = f"{sequence.prefix}{sequence.next_value:0{sequence.padding}d}"
    sequence.next_value += 1
    return value


def _get_company(db: Session, company_id: uuid.UUID) -> Company:
    company = db.get(Company, company_id)
    if company is None or not company.active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    return company


def _validate_period(
    db: Session, company_id: uuid.UUID, period_id: uuid.UUID, posting_date: date
) -> FiscalPeriod:
    period = db.scalar(
        select(FiscalPeriod).where(
            FiscalPeriod.company_id == company_id, FiscalPeriod.id == period_id
        )
    )
    if period is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Fiscal period not found")
    if period.status != PeriodStatus.OPEN:
        raise HTTPException(status.HTTP_409_CONFLICT, "Fiscal period is not open")
    if not (period.start_date <= posting_date <= period.end_date):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Posting date does not fall within the selected fiscal period",
        )
    return period


def _entry_totals(entry: JournalEntry) -> tuple[Decimal, Decimal]:
    return (
        sum((line.debit_base for line in entry.lines), Decimal("0")),
        sum((line.credit_base for line in entry.lines), Decimal("0")),
    )


def validate_entry(db: Session, entry: JournalEntry, company: Company) -> tuple[Decimal, Decimal]:
    if len(entry.lines) < 2:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "At least two lines are required"
        )
    _validate_period(db, entry.company_id, entry.fiscal_period_id, entry.posting_date)
    account_ids = {line.account_id for line in entry.lines}
    accounts = {
        account.id: account
        for account in db.scalars(
            select(Account).where(
                Account.company_id == entry.company_id,
                Account.id.in_(account_ids),
                Account.active.is_(True),
            )
        )
    }
    if set(accounts) != account_ids:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Every journal line must reference an active account in this company",
        )
    for line in entry.lines:
        account = accounts[line.account_id]
        if not account.postable or account.account_type == AccountType.TITLE:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"Account {account.code} is not postable",
            )
        if (line.debit_base > 0) == (line.credit_base > 0):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "Every line must contain exactly one positive debit or credit",
            )
    debit, credit = _entry_totals(entry)
    if debit <= 0 or quantize(debit, company) != quantize(credit, company):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Journal is not balanced in base currency: debit={debit} credit={credit}",
        )
    return quantize(debit, company), quantize(credit, company)


def create_batch(
    db: Session,
    *,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: JournalBatchCreate,
    commit: bool = True,
) -> JournalBatch:
    company = _get_company(db, company_id)
    batch = JournalBatch(
        company_id=company_id,
        batch_no=payload.batch_no or next_number(db, company_id, "batch", "B-"),
        description=payload.description,
        created_by_id=user_id,
    )
    db.add(batch)
    db.flush()
    for entry_payload in payload.entries:
        _validate_period(db, company_id, entry_payload.fiscal_period_id, entry_payload.posting_date)
        entry = JournalEntry(
            company_id=company_id,
            batch_id=batch.id,
            entry_no=next_number(db, company_id, "entry", "J-"),
            entry_date=entry_payload.entry_date,
            posting_date=entry_payload.posting_date,
            fiscal_period_id=entry_payload.fiscal_period_id,
            reference=entry_payload.reference,
            description=entry_payload.description,
            created_by_id=user_id,
        )
        db.add(entry)
        db.flush()
        for index, line_payload in enumerate(entry_payload.lines, start=1):
            debit_base = quantize(line_payload.debit * line_payload.exchange_rate, company)
            credit_base = quantize(line_payload.credit * line_payload.exchange_rate, company)
            entry.lines.append(
                JournalLine(
                    company_id=company_id,
                    line_no=index,
                    account_id=line_payload.account_id,
                    description=line_payload.description,
                    currency_code=line_payload.currency_code.upper(),
                    exchange_rate=line_payload.exchange_rate,
                    debit_original=line_payload.debit,
                    credit_original=line_payload.credit,
                    debit_base=debit_base,
                    credit_base=credit_base,
                )
            )
        validate_entry(db, entry, company)
    record_audit(
        db,
        company_id=company_id,
        actor_id=user_id,
        action="journal.batch.created",
        entity_type="journal_batch",
        entity_id=str(batch.id),
        after={"batch_no": batch.batch_no, "status": batch.status.value},
    )
    if commit:
        db.commit()
    else:
        db.flush()
    return load_batch(db, company_id, batch.id)


def replace_draft_batch(
    db: Session,
    *,
    company_id: uuid.UUID,
    batch_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: JournalBatchCreate,
) -> JournalBatch:
    company = _get_company(db, company_id)
    batch = db.scalar(
        select(JournalBatch)
        .options(selectinload(JournalBatch.entries).selectinload(JournalEntry.lines))
        .where(JournalBatch.company_id == company_id, JournalBatch.id == batch_id)
        .with_for_update()
    )
    if batch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Journal batch not found")
    if batch.status not in {JournalStatus.DRAFT, JournalStatus.REJECTED}:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Only draft or rejected batches can be edited"
        )
    before = {"description": batch.description, "entries": len(batch.entries)}
    for entry in list(batch.entries):
        db.delete(entry)
    db.flush()
    batch.description = payload.description
    batch.status = JournalStatus.DRAFT
    batch.version += 1
    for entry_payload in payload.entries:
        _validate_period(db, company_id, entry_payload.fiscal_period_id, entry_payload.posting_date)
        entry = JournalEntry(
            company_id=company_id,
            batch_id=batch.id,
            entry_no=next_number(db, company_id, "entry", "J-"),
            entry_date=entry_payload.entry_date,
            posting_date=entry_payload.posting_date,
            fiscal_period_id=entry_payload.fiscal_period_id,
            reference=entry_payload.reference,
            description=entry_payload.description,
            created_by_id=user_id,
        )
        db.add(entry)
        db.flush()
        for index, line_payload in enumerate(entry_payload.lines, start=1):
            entry.lines.append(
                JournalLine(
                    company_id=company_id,
                    line_no=index,
                    account_id=line_payload.account_id,
                    description=line_payload.description,
                    currency_code=line_payload.currency_code.upper(),
                    exchange_rate=line_payload.exchange_rate,
                    debit_original=line_payload.debit,
                    credit_original=line_payload.credit,
                    debit_base=quantize(line_payload.debit * line_payload.exchange_rate, company),
                    credit_base=quantize(line_payload.credit * line_payload.exchange_rate, company),
                )
            )
        validate_entry(db, entry, company)
    record_audit(
        db,
        company_id=company_id,
        actor_id=user_id,
        action="journal.batch.updated",
        entity_type="journal_batch",
        entity_id=str(batch.id),
        before=before,
        after={"description": batch.description, "entries": len(payload.entries)},
    )
    db.commit()
    return load_batch(db, company_id, batch.id)


def delete_draft_batch(
    db: Session, company_id: uuid.UUID, batch_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    batch = load_batch(db, company_id, batch_id)
    if batch.status not in {JournalStatus.DRAFT, JournalStatus.REJECTED}:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Only draft or rejected batches can be deleted"
        )
    record_audit(
        db,
        company_id=company_id,
        actor_id=user_id,
        action="journal.batch.deleted",
        entity_type="journal_batch",
        entity_id=str(batch.id),
        before={"batch_no": batch.batch_no, "description": batch.description},
    )
    db.delete(batch)
    db.commit()


def copy_batch(
    db: Session, company_id: uuid.UUID, batch_id: uuid.UUID, user_id: uuid.UUID
) -> JournalBatch:
    source = load_batch(db, company_id, batch_id)
    payload = JournalBatchCreate.model_validate(
        {
            "description": f"Copy of {source.description}"[:250],
            "entries": [
                {
                    "entry_date": entry.entry_date,
                    "posting_date": entry.posting_date,
                    "fiscal_period_id": entry.fiscal_period_id,
                    "reference": entry.reference,
                    "description": f"Copy of {entry.description}"[:250],
                    "lines": [
                        {
                            "account_id": line.account_id,
                            "description": line.description,
                            "currency_code": line.currency_code,
                            "exchange_rate": line.exchange_rate,
                            "debit": line.debit_original,
                            "credit": line.credit_original,
                        }
                        for line in entry.lines
                    ],
                }
                for entry in source.entries
            ],
        }
    )
    copied = create_batch(db, company_id=company_id, user_id=user_id, payload=payload, commit=False)
    record_audit(
        db,
        company_id=company_id,
        actor_id=user_id,
        action="journal.batch.copied",
        entity_type="journal_batch",
        entity_id=str(copied.id),
        metadata={"source_batch_id": str(source.id)},
    )
    db.commit()
    return load_batch(db, company_id, copied.id)


def load_batch(db: Session, company_id: uuid.UUID, batch_id: uuid.UUID) -> JournalBatch:
    batch = db.scalar(
        select(JournalBatch)
        .options(selectinload(JournalBatch.entries).selectinload(JournalEntry.lines))
        .where(JournalBatch.company_id == company_id, JournalBatch.id == batch_id)
    )
    if batch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Journal batch not found")
    return batch


def transition_validate(
    db: Session, company_id: uuid.UUID, batch_id: uuid.UUID, user_id: uuid.UUID
) -> JournalBatch:
    batch = load_batch(db, company_id, batch_id)
    if batch.status not in {JournalStatus.DRAFT, JournalStatus.REJECTED}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only draft or rejected batches validate")
    company = _get_company(db, company_id)
    for entry in batch.entries:
        validate_entry(db, entry, company)
        entry.status = JournalStatus.VALIDATED
    batch.status = JournalStatus.VALIDATED
    batch.version += 1
    record_audit(
        db,
        company_id=company_id,
        actor_id=user_id,
        action="journal.batch.validated",
        entity_type="journal_batch",
        entity_id=str(batch.id),
    )
    db.commit()
    return load_batch(db, company_id, batch_id)


def approve_batch(
    db: Session,
    company_id: uuid.UUID,
    batch_id: uuid.UUID,
    user_id: uuid.UUID,
    allow_self_approval: bool,
) -> JournalBatch:
    batch = load_batch(db, company_id, batch_id)
    if batch.status != JournalStatus.VALIDATED:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only validated batches can be approved")
    if batch.created_by_id == user_id and not allow_self_approval:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Maker-checker approval requires another user"
        )
    now = datetime.now(UTC)
    for entry in batch.entries:
        entry.status = JournalStatus.APPROVED
    batch.status = JournalStatus.APPROVED
    batch.approved_by_id = user_id
    batch.approved_at = now
    batch.version += 1
    record_audit(
        db,
        company_id=company_id,
        actor_id=user_id,
        action="journal.batch.approved",
        entity_type="journal_batch",
        entity_id=str(batch.id),
    )
    db.commit()
    return load_batch(db, company_id, batch_id)


def _line_digest(entry: JournalEntry) -> str:
    payload = [
        {
            "line": line.line_no,
            "account": str(line.account_id),
            "currency": line.currency_code,
            "rate": str(line.exchange_rate),
            "debit": str(line.debit_base),
            "credit": str(line.credit_base),
        }
        for line in entry.lines
    ]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def post_batch(
    db: Session,
    company_id: uuid.UUID,
    batch_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    commit: bool = True,
) -> JournalBatch:
    batch = db.scalar(
        select(JournalBatch)
        .options(selectinload(JournalBatch.entries).selectinload(JournalEntry.lines))
        .where(JournalBatch.company_id == company_id, JournalBatch.id == batch_id)
        .with_for_update()
    )
    if batch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Journal batch not found")
    if batch.status != JournalStatus.APPROVED:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only approved batches can be posted")
    company = _get_company(db, company_id)
    now = datetime.now(UTC)
    for entry in batch.entries:
        debit, credit = validate_entry(db, entry, company)
        for line in entry.lines:
            balance = db.scalar(
                select(PeriodBalance)
                .where(
                    PeriodBalance.company_id == company_id,
                    PeriodBalance.fiscal_period_id == entry.fiscal_period_id,
                    PeriodBalance.account_id == line.account_id,
                    PeriodBalance.currency_code == line.currency_code,
                )
                .with_for_update()
            )
            if balance is None:
                balance = PeriodBalance(
                    company_id=company_id,
                    fiscal_period_id=entry.fiscal_period_id,
                    account_id=line.account_id,
                    currency_code=line.currency_code,
                    debit_base=Decimal("0"),
                    credit_base=Decimal("0"),
                    debit_original=Decimal("0"),
                    credit_original=Decimal("0"),
                )
                db.add(balance)
            balance.debit_base += line.debit_base
            balance.credit_base += line.credit_base
            balance.debit_original += line.debit_original
            balance.credit_original += line.credit_original
        entry.status = JournalStatus.POSTED
        entry.posted_at = now
        db.add(
            PostingEvent(
                company_id=company_id,
                entry_id=entry.id,
                posted_by_id=user_id,
                debit_total=debit,
                credit_total=credit,
                digest=_line_digest(entry),
            )
        )
    batch.status = JournalStatus.POSTED
    batch.posted_at = now
    batch.version += 1
    record_audit(
        db,
        company_id=company_id,
        actor_id=user_id,
        action="journal.batch.posted",
        entity_type="journal_batch",
        entity_id=str(batch.id),
        metadata={"entries": len(batch.entries)},
    )
    if commit:
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
    else:
        db.flush()
    return load_batch(db, company_id, batch_id)


def reverse_entry(
    db: Session,
    company_id: uuid.UUID,
    entry_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: ReversalRequest,
) -> JournalBatch:
    original = db.scalar(
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .where(JournalEntry.company_id == company_id, JournalEntry.id == entry_id)
    )
    if original is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Journal entry not found")
    if original.status != JournalStatus.POSTED:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only posted entries can be reversed")
    existing = db.scalar(
        select(JournalEntry.id).where(
            JournalEntry.company_id == company_id, JournalEntry.reversal_of_id == original.id
        )
    )
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This entry already has a reversal")

    _validate_period(db, company_id, payload.fiscal_period_id, payload.posting_date)
    now = datetime.now(UTC)
    batch = JournalBatch(
        company_id=company_id,
        batch_no=next_number(db, company_id, "batch", "B-"),
        description=f"Reversal of {original.entry_no}: {payload.reason}",
        status=JournalStatus.APPROVED,
        created_by_id=user_id,
        approved_by_id=user_id,
        approved_at=now,
    )
    db.add(batch)
    db.flush()
    reversal = JournalEntry(
        company_id=company_id,
        batch_id=batch.id,
        entry_no=next_number(db, company_id, "entry", "J-"),
        entry_date=payload.posting_date,
        posting_date=payload.posting_date,
        fiscal_period_id=payload.fiscal_period_id,
        reference=f"REV:{original.entry_no}"[:80],
        description=f"Reversal of {original.entry_no}: {payload.reason}",
        status=JournalStatus.APPROVED,
        reversal_of_id=original.id,
        created_by_id=user_id,
    )
    db.add(reversal)
    db.flush()
    for line in original.lines:
        reversal.lines.append(
            JournalLine(
                company_id=company_id,
                line_no=line.line_no,
                account_id=line.account_id,
                description=f"Reversal: {line.description}"[:250],
                currency_code=line.currency_code,
                exchange_rate=line.exchange_rate,
                debit_original=line.credit_original,
                credit_original=line.debit_original,
                debit_base=line.credit_base,
                credit_base=line.debit_base,
            )
        )
    record_audit(
        db,
        company_id=company_id,
        actor_id=user_id,
        action="journal.entry.reversal_created",
        entity_type="journal_entry",
        entity_id=str(reversal.id),
        metadata={"reversal_of": str(original.id), "reason": payload.reason},
    )
    return post_batch(db, company_id, batch.id, user_id)


def trial_balance(db: Session, company_id: uuid.UUID, period_id: uuid.UUID):  # type: ignore[no-untyped-def]
    return db.execute(
        select(
            Account.id,
            Account.code,
            Account.name,
            func.coalesce(func.sum(PeriodBalance.debit_base), 0).label("debit"),
            func.coalesce(func.sum(PeriodBalance.credit_base), 0).label("credit"),
        )
        .outerjoin(
            PeriodBalance,
            (PeriodBalance.company_id == Account.company_id)
            & (PeriodBalance.account_id == Account.id)
            & (PeriodBalance.fiscal_period_id == period_id),
        )
        .where(Account.company_id == company_id, Account.account_type != AccountType.TITLE)
        .group_by(Account.id, Account.code, Account.name)
        .order_by(Account.code)
    ).all()
