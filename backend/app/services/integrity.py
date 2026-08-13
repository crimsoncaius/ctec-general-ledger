import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import JournalEntry, JournalLine, JournalStatus, PeriodBalance


def run_integrity_checks(db: Session, company_id: uuid.UUID) -> list[dict[str, object]]:
    posted = db.execute(
        select(
            JournalEntry.fiscal_period_id,
            JournalLine.account_id,
            JournalLine.currency_code,
            func.sum(JournalLine.debit_base),
            func.sum(JournalLine.credit_base),
            func.sum(JournalLine.debit_original),
            func.sum(JournalLine.credit_original),
        )
        .join(JournalLine, JournalLine.entry_id == JournalEntry.id)
        .where(
            JournalEntry.company_id == company_id,
            JournalEntry.status == JournalStatus.POSTED,
        )
        .group_by(
            JournalEntry.fiscal_period_id,
            JournalLine.account_id,
            JournalLine.currency_code,
        )
    ).all()
    recomputed = {
        (period_id, account_id, currency): tuple(Decimal(value or 0) for value in values)
        for period_id, account_id, currency, *values in posted
    }
    stored_rows = db.scalars(
        select(PeriodBalance).where(PeriodBalance.company_id == company_id)
    ).all()
    stored = {
        (row.fiscal_period_id, row.account_id, row.currency_code): (
            row.debit_base,
            row.credit_base,
            row.debit_original,
            row.credit_original,
        )
        for row in stored_rows
    }
    mismatches = []
    for key in sorted(set(recomputed) | set(stored), key=lambda item: tuple(map(str, item))):
        if recomputed.get(key, (Decimal("0"),) * 4) != stored.get(key, (Decimal("0"),) * 4):
            mismatches.append(
                {
                    "period_id": str(key[0]),
                    "account_id": str(key[1]),
                    "currency": key[2],
                    "ledger": list(map(str, recomputed.get(key, (Decimal("0"),) * 4))),
                    "stored": list(map(str, stored.get(key, (Decimal("0"),) * 4))),
                }
            )

    balance = db.execute(
        select(
            func.coalesce(func.sum(JournalLine.debit_base), 0),
            func.coalesce(func.sum(JournalLine.credit_base), 0),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(
            JournalEntry.company_id == company_id,
            JournalEntry.status == JournalStatus.POSTED,
        )
    ).one()
    return [
        {
            "name": "posted_ledger_balances",
            "ok": Decimal(balance[0]) == Decimal(balance[1]),
            "debit": str(balance[0]),
            "credit": str(balance[1]),
        },
        {
            "name": "period_balance_reconciliation",
            "ok": not mismatches,
            "mismatches": mismatches,
        },
    ]
