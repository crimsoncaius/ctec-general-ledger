import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select

from app.deps import AccessContext, DbSession, require
from app.models import ReportDefinition, ReportRun, RunStatus
from app.schemas import (
    CustomReportCreate,
    CustomReportDefinitionData,
    CustomReportOut,
    CustomReportPreview,
    CustomReportRunRequest,
    CustomReportUpdate,
    LegacyConversionPreview,
    LegacyReportImport,
    ReportRunOut,
)
from app.services.audit import record_audit
from app.services.custom_reports import (
    FormulaError,
    build_custom_report,
    validate_definition_formulas,
)
from app.services.legacy_reports import convert_legacy_report
from app.services.reporting import ReportData, export_report

router = APIRouter(prefix="/custom-reports", tags=["custom reports"])


def _definition(
    db: DbSession,
    company_id: uuid.UUID,
    definition_id: uuid.UUID,
    *,
    lock: bool = False,
) -> ReportDefinition:
    statement = select(ReportDefinition).where(
        ReportDefinition.company_id == company_id, ReportDefinition.id == definition_id
    )
    if lock:
        statement = statement.with_for_update()
    report = db.scalar(statement)
    if report is None:
        raise HTTPException(404, "Custom report not found")
    return report


def _validate(definition: CustomReportDefinitionData) -> None:
    try:
        validate_definition_formulas(definition)
    except FormulaError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("", response_model=list[CustomReportOut])
def list_definitions(
    db: DbSession,
    templates: bool | None = Query(default=None),
    context: AccessContext = Depends(require("reports.custom.run")),
) -> list[ReportDefinition]:
    statement = select(ReportDefinition).where(ReportDefinition.company_id == context.company_id)
    if templates is not None:
        statement = statement.where(ReportDefinition.is_template == templates)
    return list(db.scalars(statement.order_by(ReportDefinition.name)).all())


@router.post("", response_model=CustomReportOut, status_code=201)
def create_definition(
    payload: CustomReportCreate,
    db: DbSession,
    context: AccessContext = Depends(require("reports.custom.design")),
) -> ReportDefinition:
    _validate(payload.definition)
    report = ReportDefinition(
        company_id=context.company_id,
        name=payload.name,
        report_type="structured",
        definition=payload.definition.model_dump(mode="json"),
        conversion_status="converted",
        is_template=payload.is_template,
        created_by_id=context.user.id,
    )
    db.add(report)
    db.flush()
    record_audit(
        db,
        company_id=context.company_id,
        actor_id=context.user.id,
        action="custom_report.created",
        entity_type="report_definition",
        entity_id=str(report.id),
        after={"name": report.name, "version": report.version, "template": report.is_template},
    )
    db.commit()
    return report


@router.get("/{definition_id}", response_model=CustomReportOut)
def get_definition(
    definition_id: uuid.UUID,
    db: DbSession,
    context: AccessContext = Depends(require("reports.custom.run")),
) -> ReportDefinition:
    return _definition(db, context.company_id, definition_id)


@router.put("/{definition_id}", response_model=CustomReportOut)
def update_definition(
    definition_id: uuid.UUID,
    payload: CustomReportUpdate,
    db: DbSession,
    context: AccessContext = Depends(require("reports.custom.design")),
) -> ReportDefinition:
    _validate(payload.definition)
    report = _definition(db, context.company_id, definition_id, lock=True)
    if report.version != payload.version:
        raise HTTPException(409, "Report changed since it was opened; reload before saving")
    before = {"name": report.name, "version": report.version}
    report.name = payload.name
    report.definition = payload.definition.model_dump(mode="json")
    report.is_template = payload.is_template
    report.report_type = "structured"
    report.conversion_status = "converted"
    report.version += 1
    record_audit(
        db,
        company_id=context.company_id,
        actor_id=context.user.id,
        action="custom_report.updated",
        entity_type="report_definition",
        entity_id=str(report.id),
        before=before,
        after={"name": report.name, "version": report.version, "template": report.is_template},
    )
    db.commit()
    return report


@router.post("/{definition_id}/clone", response_model=CustomReportOut, status_code=201)
def clone_definition(
    definition_id: uuid.UUID,
    db: DbSession,
    context: AccessContext = Depends(require("reports.custom.design")),
) -> ReportDefinition:
    source = _definition(db, context.company_id, definition_id)
    clone = ReportDefinition(
        company_id=context.company_id,
        name=f"{source.name} — copy",
        report_type="structured",
        definition=source.definition,
        conversion_status="converted",
        is_template=False,
        created_by_id=context.user.id,
    )
    db.add(clone)
    db.commit()
    return clone


@router.post("/designer/preview", response_model=None)
def preview_definition(
    payload: CustomReportPreview,
    db: DbSession,
    context: AccessContext = Depends(require("reports.custom.design")),
) -> dict[str, object]:
    report = build_custom_report(db, context.company_id, payload.definition, payload.parameters)
    return {
        "title": report.title,
        "digest": report.digest,
        "columns": report.columns,
        "rows": report.rows,
    }


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
            "Content-Disposition": f'attachment; filename="custom-report-{run.id}.{extension}"',
            "X-Report-Run-ID": str(run.id),
            "X-Report-Digest": report.digest,
        },
    )


def _execute(
    db: DbSession,
    context: AccessContext,
    definition: ReportDefinition,
    parameters: dict[str, object],
) -> tuple[ReportRun, ReportData]:
    if definition.conversion_status in {"manual", "partial"}:
        raise HTTPException(409, "Legacy report requires manual conversion before it can run")
    parsed = CustomReportDefinitionData.model_validate(definition.definition)
    run = ReportRun(
        company_id=context.company_id,
        report_definition_id=definition.id,
        report_type="custom",
        parameters=parameters,
        status=RunStatus.RUNNING,
        requested_by_id=context.user.id,
    )
    db.add(run)
    db.flush()
    try:
        report = build_custom_report(db, context.company_id, parsed, parameters)
        run.status = RunStatus.SUCCEEDED
        run.result_digest = report.digest
        record_audit(
            db,
            company_id=context.company_id,
            actor_id=context.user.id,
            action="custom_report.completed",
            entity_type="report_run",
            entity_id=str(run.id),
            metadata={"definition_id": str(definition.id), "digest": report.digest},
        )
        db.commit()
        return run, report
    except Exception as exc:
        db.rollback()
        failed = ReportRun(
            id=run.id,
            company_id=context.company_id,
            report_definition_id=definition.id,
            report_type="custom",
            parameters=parameters,
            status=RunStatus.FAILED,
            requested_by_id=context.user.id,
            error=str(exc)[:2000],
        )
        db.merge(failed)
        db.commit()
        raise


@router.post("/{definition_id}/run", response_model=None)
def run_definition(
    definition_id: uuid.UUID,
    payload: CustomReportRunRequest,
    db: DbSession,
    context: AccessContext = Depends(require("reports.custom.run")),
) -> Response | dict[str, object]:
    definition = _definition(db, context.company_id, definition_id)
    run, report = _execute(db, context, definition, payload.parameters)
    return _response(run, report, payload.format)


@router.get("/runs/history", response_model=list[ReportRunOut])
def list_custom_runs(
    db: DbSession,
    context: AccessContext = Depends(require("reports.custom.run")),
) -> list[ReportRun]:
    return list(
        db.scalars(
            select(ReportRun)
            .where(
                ReportRun.company_id == context.company_id,
                ReportRun.report_definition_id.is_not(None),
            )
            .order_by(ReportRun.created_at.desc())
            .limit(200)
        ).all()
    )


@router.post("/legacy/preview", response_model=LegacyConversionPreview)
def preview_legacy(
    payload: LegacyReportImport,
    _context: AccessContext = Depends(require("reports.custom.design")),
) -> LegacyConversionPreview:
    return convert_legacy_report(payload.spec, payload.template)


@router.post("/legacy/import", response_model=CustomReportOut, status_code=201)
def import_legacy(
    payload: LegacyReportImport,
    db: DbSession,
    context: AccessContext = Depends(require("reports.custom.design")),
) -> ReportDefinition:
    conversion = convert_legacy_report(payload.spec, payload.template)
    report = ReportDefinition(
        company_id=context.company_id,
        name=payload.name,
        report_type="legacy",
        definition=conversion.definition.model_dump(mode="json") if conversion.definition else {},
        legacy_spec=payload.spec,
        legacy_template=payload.template,
        conversion_status=conversion.status,
        is_template=payload.is_template,
        created_by_id=context.user.id,
    )
    db.add(report)
    db.flush()
    record_audit(
        db,
        company_id=context.company_id,
        actor_id=context.user.id,
        action="custom_report.legacy_imported",
        entity_type="report_definition",
        entity_id=str(report.id),
        metadata={"status": conversion.status, "warnings": conversion.warnings},
    )
    db.commit()
    return report
