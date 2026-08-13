import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select

from app.deps import AccessContext, DbSession, require
from app.models import ReportRun, RunStatus
from app.schemas import ReportRequest, ReportRunOut
from app.services.audit import record_audit
from app.services.reporting import ReportData, build_report, export_report

router = APIRouter(prefix="/reports", tags=["standard reports"])


def _execute_report(
    db: DbSession,
    context: AccessContext,
    request: ReportRequest,
) -> tuple[ReportRun, ReportData]:
    run = ReportRun(
        company_id=context.company_id,
        report_type=request.report_type,
        parameters=request.parameters,
        status=RunStatus.RUNNING,
        requested_by_id=context.user.id,
    )
    db.add(run)
    db.flush()
    try:
        report = build_report(db, context.company_id, request.report_type, request.parameters)
        run.status = RunStatus.SUCCEEDED
        run.result_digest = report.digest
        record_audit(
            db,
            company_id=context.company_id,
            actor_id=context.user.id,
            action="report.completed",
            entity_type="report_run",
            entity_id=str(run.id),
            metadata={
                "type": request.report_type,
                "format": request.format,
                "digest": report.digest,
                "rows": len(report.rows),
            },
        )
        db.commit()
        return run, report
    except Exception as exc:
        db.rollback()
        failed = ReportRun(
            id=run.id,
            company_id=context.company_id,
            report_type=request.report_type,
            parameters=request.parameters,
            status=RunStatus.FAILED,
            requested_by_id=context.user.id,
            error=str(exc)[:2000],
        )
        db.merge(failed)
        db.commit()
        raise


def _response(
    run: ReportRun, report: ReportData, output_format: str
) -> Response | dict[str, object]:
    if output_format == "json":
        return {
            "run_id": str(run.id),
            "title": report.title,
            "digest": report.digest,
            "columns": report.columns,
            "rows": report.rows,
        }
    content, media_type, extension = export_report(report, output_format)
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{run.report_type}-{run.id}.{extension}"',
            "X-Report-Run-ID": str(run.id),
            "X-Report-Digest": report.digest,
        },
    )


@router.post("/run", response_model=None)
def run_report(
    request: ReportRequest,
    db: DbSession,
    context: AccessContext = Depends(require("reports.run")),
) -> Response | dict[str, object]:
    run, report = _execute_report(db, context, request)
    return _response(run, report, request.format)


@router.get("/runs", response_model=list[ReportRunOut])
def list_runs(
    db: DbSession,
    context: AccessContext = Depends(require("reports.run")),
) -> list[ReportRun]:
    return list(
        db.scalars(
            select(ReportRun)
            .where(
                ReportRun.company_id == context.company_id,
                ReportRun.report_definition_id.is_(None),
            )
            .order_by(ReportRun.created_at.desc())
            .limit(200)
        ).all()
    )


@router.post("/runs/{run_id}/reproduce", response_model=None)
def reproduce_run(
    run_id: uuid.UUID,
    db: DbSession,
    output_format: str = Query(default="json", pattern="^(json|csv|xlsx|pdf)$"),
    context: AccessContext = Depends(require("reports.run")),
) -> Response | dict[str, object]:
    previous = db.scalar(
        select(ReportRun).where(ReportRun.company_id == context.company_id, ReportRun.id == run_id)
    )
    if previous is None:
        raise HTTPException(404, "Report run not found")
    request = ReportRequest(
        report_type=previous.report_type,
        parameters=previous.parameters,
        format=output_format,
    )
    run, report = _execute_report(db, context, request)
    return _response(run, report, output_format)
