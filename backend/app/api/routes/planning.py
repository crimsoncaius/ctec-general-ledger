import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.deps import AccessContext, DbSession, require
from app.models import Account, Budget, FiscalPeriod, JournalBatch
from app.schemas import (
    BudgetOut,
    BudgetUpsert,
    ClosePreview,
    CloseRequest,
    CloseResult,
    CompensatingCloseRequest,
    JournalBatchOut,
)
from app.services.audit import record_audit
from app.services.closing import close_fiscal_year, close_preview, compensate_close

router = APIRouter(tags=["budgets and fiscal close"])


@router.get("/budgets", response_model=list[BudgetOut])
def list_budgets(
    db: DbSession,
    scenario: str | None = None,
    context: AccessContext = Depends(require("budgets.manage")),
) -> list[Budget]:
    statement = select(Budget).where(Budget.company_id == context.company_id)
    if scenario:
        statement = statement.where(Budget.scenario == scenario)
    return list(db.scalars(statement.order_by(Budget.scenario, Budget.fiscal_period_id)).all())


@router.put("/budgets", response_model=BudgetOut)
def upsert_budget(
    payload: BudgetUpsert,
    db: DbSession,
    context: AccessContext = Depends(require("budgets.manage")),
) -> Budget:
    period = db.scalar(
        select(FiscalPeriod.id).where(
            FiscalPeriod.company_id == context.company_id,
            FiscalPeriod.id == payload.fiscal_period_id,
        )
    )
    account = db.scalar(
        select(Account.id).where(
            Account.company_id == context.company_id,
            Account.id == payload.account_id,
            Account.active.is_(True),
        )
    )
    if period is None or account is None:
        from fastapi import HTTPException

        raise HTTPException(422, "Budget period and account must belong to this company")
    budget = db.scalar(
        select(Budget).where(
            Budget.company_id == context.company_id,
            Budget.fiscal_period_id == payload.fiscal_period_id,
            Budget.account_id == payload.account_id,
            Budget.scenario == payload.scenario,
            Budget.currency_code == payload.currency_code.upper(),
        )
    )
    before = None
    if budget is None:
        budget = Budget(company_id=context.company_id, **payload.model_dump())
        budget.currency_code = budget.currency_code.upper()
        db.add(budget)
    else:
        before = {"amount": str(budget.amount)}
        budget.amount = payload.amount
    db.flush()
    record_audit(
        db,
        company_id=context.company_id,
        actor_id=context.user.id,
        action="budget.upserted",
        entity_type="budget",
        entity_id=str(budget.id),
        before=before,
        after={"scenario": budget.scenario, "amount": str(budget.amount)},
    )
    db.commit()
    return budget


@router.post("/fiscal/years/{fiscal_year_id}/close-preview", response_model=ClosePreview)
def preview_close(
    fiscal_year_id: uuid.UUID,
    payload: CloseRequest,
    db: DbSession,
    context: AccessContext = Depends(require("fiscal.close")),
) -> ClosePreview:
    return close_preview(db, context.company_id, fiscal_year_id, payload.opening_period_id)


@router.post("/fiscal/years/{fiscal_year_id}/close", response_model=CloseResult)
def close_year(
    fiscal_year_id: uuid.UUID,
    payload: CloseRequest,
    db: DbSession,
    context: AccessContext = Depends(require("fiscal.close")),
) -> CloseResult:
    return close_fiscal_year(db, context.company_id, fiscal_year_id, context.user.id, payload)


@router.post("/fiscal/years/{fiscal_year_id}/compensate-close", response_model=JournalBatchOut)
def compensate_year_close(
    fiscal_year_id: uuid.UUID,
    payload: CompensatingCloseRequest,
    db: DbSession,
    context: AccessContext = Depends(require("fiscal.close")),
) -> JournalBatch:
    return compensate_close(db, context.company_id, fiscal_year_id, context.user.id, payload)
