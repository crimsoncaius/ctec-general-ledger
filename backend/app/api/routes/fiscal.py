from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.deps import AccessContext, DbSession, require
from app.models import FiscalPeriod, FiscalYear
from app.schemas import FiscalPeriodOut, FiscalYearCreate, FiscalYearOut
from app.services.audit import record_audit

router = APIRouter(prefix="/fiscal", tags=["fiscal calendars"])


@router.get("/years", response_model=list[FiscalYearOut])
def list_years(
    db: DbSession, context: AccessContext = Depends(require("fiscal.view"))
) -> list[FiscalYear]:
    return list(
        db.scalars(
            select(FiscalYear)
            .where(FiscalYear.company_id == context.company_id)
            .order_by(FiscalYear.start_date)
        ).all()
    )


@router.get("/periods", response_model=list[FiscalPeriodOut])
def list_periods(
    db: DbSession, context: AccessContext = Depends(require("fiscal.view"))
) -> list[FiscalPeriod]:
    return list(
        db.scalars(
            select(FiscalPeriod)
            .where(FiscalPeriod.company_id == context.company_id)
            .order_by(FiscalPeriod.start_date, FiscalPeriod.period_no)
        ).all()
    )


@router.post("/years", status_code=201)
def create_year(
    payload: FiscalYearCreate,
    db: DbSession,
    context: AccessContext = Depends(require("fiscal.manage")),
) -> dict[str, object]:
    fiscal_year = FiscalYear(
        company_id=context.company_id,
        label=payload.label,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    db.add(fiscal_year)
    db.flush()
    for period in payload.periods:
        db.add(
            FiscalPeriod(
                company_id=context.company_id,
                fiscal_year_id=fiscal_year.id,
                period_no=period.period_no,
                label=period.label,
                start_date=period.start_date,
                end_date=period.end_date,
            )
        )
    record_audit(
        db,
        company_id=context.company_id,
        actor_id=context.user.id,
        action="fiscal.year.created",
        entity_type="fiscal_year",
        entity_id=str(fiscal_year.id),
        after={"label": fiscal_year.label, "period_count": len(payload.periods)},
    )
    db.commit()
    return {"id": fiscal_year.id, "period_count": len(payload.periods)}
