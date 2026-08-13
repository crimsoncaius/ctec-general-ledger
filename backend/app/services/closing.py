import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Account,
    AccountType,
    ClosingEvent,
    Company,
    FiscalPeriod,
    FiscalYear,
    JournalBatch,
    JournalEntry,
    JournalLine,
    JournalStatus,
    PeriodStatus,
)
from app.schemas import ClosePreview, CloseRequest, CloseResult, CompensatingCloseRequest
from app.services.accounting import next_number, post_batch, quantize
from app.services.audit import record_audit


def _close_context(
    db: Session, company_id: uuid.UUID, fiscal_year_id: uuid.UUID, opening_period_id: uuid.UUID
) -> tuple[Company, FiscalYear, list[FiscalPeriod], FiscalPeriod, Account]:
    company = db.get(Company, company_id)
    fiscal_year = db.scalar(
        select(FiscalYear).where(
            FiscalYear.company_id == company_id, FiscalYear.id == fiscal_year_id
        )
    )
    if company is None or fiscal_year is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fiscal year not found")
    periods = list(
        db.scalars(
            select(FiscalPeriod)
            .where(
                FiscalPeriod.company_id == company_id,
                FiscalPeriod.fiscal_year_id == fiscal_year.id,
            )
            .order_by(FiscalPeriod.period_no)
        ).all()
    )
    if not periods:
        raise HTTPException(status.HTTP_409_CONFLICT, "Fiscal year has no periods")
    opening_period = db.scalar(
        select(FiscalPeriod).where(
            FiscalPeriod.company_id == company_id, FiscalPeriod.id == opening_period_id
        )
    )
    if (
        opening_period is None
        or opening_period.status != PeriodStatus.OPEN
        or opening_period.start_date <= fiscal_year.end_date
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Opening period must be an open company period after the closing fiscal year",
        )
    retained = db.scalar(
        select(Account).where(
            Account.company_id == company_id,
            Account.account_type == AccountType.RETAINED_EARNINGS,
            Account.active.is_(True),
            Account.postable.is_(True),
        )
    )
    if retained is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "One active retained-earnings account is required"
        )
    return company, fiscal_year, periods, opening_period, retained


def _year_account_nets(
    db: Session, company_id: uuid.UUID, fiscal_year_id: uuid.UUID
) -> list[tuple[Account, Decimal]]:
    rows = db.execute(
        select(
            Account, func.coalesce(func.sum(JournalLine.debit_base - JournalLine.credit_base), 0)
        )
        .join(JournalLine, JournalLine.account_id == Account.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .join(FiscalPeriod, FiscalPeriod.id == JournalEntry.fiscal_period_id)
        .where(
            Account.company_id == company_id,
            JournalEntry.company_id == company_id,
            JournalEntry.status == JournalStatus.POSTED,
            FiscalPeriod.fiscal_year_id == fiscal_year_id,
        )
        .group_by(Account.id)
        .order_by(Account.code)
    ).all()
    return [(account, Decimal(net)) for account, net in rows]


def close_preview(
    db: Session,
    company_id: uuid.UUID,
    fiscal_year_id: uuid.UUID,
    opening_period_id: uuid.UUID,
) -> ClosePreview:
    company, fiscal_year, periods, opening_period, retained = _close_context(
        db, company_id, fiscal_year_id, opening_period_id
    )
    nets = _year_account_nets(db, company_id, fiscal_year_id)
    profit_loss = quantize(
        sum(
            (net for account, net in nets if account.account_type == AccountType.REVENUE_EXPENSE),
            Decimal("0"),
        ),
        company,
    )
    closing_accounts = [
        account
        for account, net in nets
        if account.account_type == AccountType.REVENUE_EXPENSE and net
    ]
    opening_nets: dict[uuid.UUID, Decimal] = {
        account.id: quantize(net, company)
        for account, net in nets
        if account.account_type != AccountType.REVENUE_EXPENSE and net
    }
    opening_nets[retained.id] = quantize(
        opening_nets.get(retained.id, Decimal("0")) + profit_loss, company
    )
    opening_nets = {key: value for key, value in opening_nets.items() if value}
    return ClosePreview(
        fiscal_year_id=fiscal_year.id,
        closing_period_id=periods[-1].id,
        opening_period_id=opening_period.id,
        profit_loss=profit_loss,
        retained_earnings_account_id=retained.id,
        closing_lines=len(closing_accounts) + (1 if profit_loss else 0),
        opening_lines=len(opening_nets),
        balanced=quantize(sum(opening_nets.values(), Decimal("0")), company) == 0,
    )


def _append_line(
    entry: JournalEntry,
    *,
    account_id: uuid.UUID,
    currency_code: str,
    net: Decimal,
    description: str,
) -> None:
    entry.lines.append(
        JournalLine(
            company_id=entry.company_id,
            line_no=len(entry.lines) + 1,
            account_id=account_id,
            description=description,
            currency_code=currency_code,
            exchange_rate=Decimal("1"),
            debit_original=max(net, Decimal("0")),
            credit_original=max(-net, Decimal("0")),
            debit_base=max(net, Decimal("0")),
            credit_base=max(-net, Decimal("0")),
        )
    )


def close_fiscal_year(
    db: Session,
    company_id: uuid.UUID,
    fiscal_year_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: CloseRequest,
) -> CloseResult:
    existing = db.scalar(
        select(ClosingEvent).where(
            ClosingEvent.company_id == company_id,
            ClosingEvent.fiscal_year_id == fiscal_year_id,
        )
    )
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Fiscal year already has a close event")
    company, fiscal_year, periods, opening_period, retained = _close_context(
        db, company_id, fiscal_year_id, payload.opening_period_id
    )
    if fiscal_year.closed_at is not None or any(
        period.status == PeriodStatus.CLOSED for period in periods
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "Fiscal year is already closed")
    preview = close_preview(db, company_id, fiscal_year_id, payload.opening_period_id)
    if not preview.balanced:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Opening balances do not reconcile; run integrity checks before closing",
        )
    nets = _year_account_nets(db, company_id, fiscal_year_id)
    batch: JournalBatch | None = None
    closing_entry: JournalEntry | None = None
    opening_entry: JournalEntry | None = None
    now = datetime.now(UTC)
    try:
        if preview.closing_lines or preview.opening_lines:
            batch = JournalBatch(
                company_id=company_id,
                batch_no=next_number(db, company_id, "batch", "B-"),
                description=f"Fiscal close {fiscal_year.label}: {payload.reason}",
                status=JournalStatus.APPROVED,
                created_by_id=user_id,
                approved_by_id=user_id,
                approved_at=now,
            )
            db.add(batch)
            db.flush()
        if preview.closing_lines:
            assert batch is not None
            closing_entry = JournalEntry(
                company_id=company_id,
                batch_id=batch.id,
                entry_no=next_number(db, company_id, "entry", "J-"),
                entry_date=fiscal_year.end_date,
                posting_date=fiscal_year.end_date,
                fiscal_period_id=periods[-1].id,
                reference=f"CLOSE:{fiscal_year.label}"[:80],
                description=f"Close profit and loss to retained earnings — {fiscal_year.label}",
                status=JournalStatus.APPROVED,
                created_by_id=user_id,
            )
            db.add(closing_entry)
            db.flush()
            for account, net in nets:
                if account.account_type == AccountType.REVENUE_EXPENSE and net:
                    _append_line(
                        closing_entry,
                        account_id=account.id,
                        currency_code=company.base_currency_code,
                        net=-quantize(net, company),
                        description=f"Close {account.code}",
                    )
            if preview.profit_loss:
                _append_line(
                    closing_entry,
                    account_id=retained.id,
                    currency_code=company.base_currency_code,
                    net=preview.profit_loss,
                    description="Transfer current-year result",
                )
        opening_values: dict[uuid.UUID, Decimal] = {
            account.id: quantize(net, company)
            for account, net in nets
            if account.account_type != AccountType.REVENUE_EXPENSE and net
        }
        opening_values[retained.id] = quantize(
            opening_values.get(retained.id, Decimal("0")) + preview.profit_loss, company
        )
        opening_values = {key: value for key, value in opening_values.items() if value}
        if opening_values:
            assert batch is not None
            opening_entry = JournalEntry(
                company_id=company_id,
                batch_id=batch.id,
                entry_no=next_number(db, company_id, "entry", "J-"),
                entry_date=opening_period.start_date,
                posting_date=opening_period.start_date,
                fiscal_period_id=opening_period.id,
                reference=f"OPEN:{fiscal_year.label}"[:80],
                description=f"Reconciled opening balances after {fiscal_year.label}",
                status=JournalStatus.APPROVED,
                created_by_id=user_id,
            )
            db.add(opening_entry)
            db.flush()
            for account_id, net in sorted(opening_values.items(), key=lambda item: str(item[0])):
                _append_line(
                    opening_entry,
                    account_id=account_id,
                    currency_code=company.base_currency_code,
                    net=net,
                    description=f"Opening balance from {fiscal_year.label}",
                )
        if batch is not None:
            post_batch(db, company_id, batch.id, user_id, commit=False)
        for period in periods:
            period.status = PeriodStatus.CLOSED
        fiscal_year.closed_at = now
        close_event = ClosingEvent(
            company_id=company_id,
            fiscal_year_id=fiscal_year.id,
            retained_earnings_account_id=retained.id,
            closing_entry_id=closing_entry.id if closing_entry else None,
            opening_entry_id=opening_entry.id if opening_entry else None,
            closed_by_id=user_id,
            parameters={"reason": payload.reason, "opening_period_id": str(opening_period.id)},
            reconciliation=preview.model_dump(mode="json"),
        )
        db.add(close_event)
        db.flush()
        record_audit(
            db,
            company_id=company_id,
            actor_id=user_id,
            action="fiscal.year.closed",
            entity_type="fiscal_year",
            entity_id=str(fiscal_year.id),
            metadata={"closing_event_id": str(close_event.id), **preview.model_dump(mode="json")},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return CloseResult(
        **preview.model_dump(),
        closing_event_id=close_event.id,
        batch_id=batch.id if batch else None,
        closing_entry_id=closing_entry.id if closing_entry else None,
        opening_entry_id=opening_entry.id if opening_entry else None,
    )


def compensate_close(
    db: Session,
    company_id: uuid.UUID,
    fiscal_year_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: CompensatingCloseRequest,
) -> JournalBatch:
    close_event = db.scalar(
        select(ClosingEvent).where(
            ClosingEvent.company_id == company_id,
            ClosingEvent.fiscal_year_id == fiscal_year_id,
        )
    )
    if close_event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Close event not found")
    if close_event.reversed_by_entry_id is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Close event is already compensated")
    period = db.scalar(
        select(FiscalPeriod).where(
            FiscalPeriod.company_id == company_id,
            FiscalPeriod.id == payload.fiscal_period_id,
        )
    )
    if (
        period is None
        or period.status != PeriodStatus.OPEN
        or not (period.start_date <= payload.posting_date <= period.end_date)
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Compensation must post into an open company period containing the posting date",
        )
    original_ids = [
        item for item in (close_event.closing_entry_id, close_event.opening_entry_id) if item
    ]
    originals = list(
        db.scalars(
            select(JournalEntry)
            .options(selectinload(JournalEntry.lines))
            .where(
                JournalEntry.company_id == company_id,
                JournalEntry.id.in_(original_ids),
                JournalEntry.status == JournalStatus.POSTED,
            )
            .order_by(JournalEntry.posting_date)
        ).all()
    )
    if not originals:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Close event has no ledger effects to compensate"
        )
    now = datetime.now(UTC)
    batch = JournalBatch(
        company_id=company_id,
        batch_no=next_number(db, company_id, "batch", "B-"),
        description=f"Compensating close: {payload.reason}",
        status=JournalStatus.APPROVED,
        created_by_id=user_id,
        approved_by_id=user_id,
        approved_at=now,
    )
    db.add(batch)
    db.flush()
    reversals: list[JournalEntry] = []
    try:
        for original in originals:
            reversal = JournalEntry(
                company_id=company_id,
                batch_id=batch.id,
                entry_no=next_number(db, company_id, "entry", "J-"),
                entry_date=payload.posting_date,
                posting_date=payload.posting_date,
                fiscal_period_id=period.id,
                reference=f"COMP:{original.entry_no}"[:80],
                description=f"Compensate {original.entry_no}: {payload.reason}",
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
                        description=f"Compensation: {line.description}"[:250],
                        currency_code=line.currency_code,
                        exchange_rate=line.exchange_rate,
                        debit_original=line.credit_original,
                        credit_original=line.debit_original,
                        debit_base=line.credit_base,
                        credit_base=line.debit_base,
                    )
                )
            reversals.append(reversal)
        post_batch(db, company_id, batch.id, user_id, commit=False)
        close_event.reversed_by_entry_id = reversals[0].id
        close_event.parameters = {
            **close_event.parameters,
            "compensation_reason": payload.reason,
            "compensated_at": now.isoformat(),
            "compensation_entries": [str(item.id) for item in reversals],
        }
        record_audit(
            db,
            company_id=company_id,
            actor_id=user_id,
            action="fiscal.close.compensated",
            entity_type="closing_event",
            entity_id=str(close_event.id),
            metadata={"entries": [str(item.id) for item in reversals]},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return batch
