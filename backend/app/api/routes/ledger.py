import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends

from app.deps import AccessContext, DbSession, require
from app.schemas import IntegrityResult, TrialBalanceRow
from app.services.accounting import trial_balance
from app.services.audit import record_audit
from app.services.integrity import run_integrity_checks

router = APIRouter(prefix="/ledger", tags=["ledger inquiry and integrity"])


@router.get("/trial-balance/{period_id}", response_model=list[TrialBalanceRow])
def get_trial_balance(
    period_id: uuid.UUID,
    db: DbSession,
    context: AccessContext = Depends(require("journals.inquire")),
) -> list[TrialBalanceRow]:
    return [
        TrialBalanceRow(
            account_id=row.id,
            code=row.code,
            name=row.name,
            debit=Decimal(row.debit),
            credit=Decimal(row.credit),
            net=Decimal(row.debit) - Decimal(row.credit),
        )
        for row in trial_balance(db, context.company_id, period_id)
    ]


@router.post("/integrity", response_model=IntegrityResult)
def integrity(
    db: DbSession,
    context: AccessContext = Depends(require("integrity.run")),
) -> IntegrityResult:
    checks = run_integrity_checks(db, context.company_id)
    record_audit(
        db,
        company_id=context.company_id,
        actor_id=context.user.id,
        action="ledger.integrity_checked",
        entity_type="company",
        entity_id=str(context.company_id),
        metadata={"ok": all(bool(check["ok"]) for check in checks)},
    )
    db.commit()
    return IntegrityResult(ok=all(bool(check["ok"]) for check in checks), checks=checks)
