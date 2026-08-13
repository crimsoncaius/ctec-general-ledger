import csv
import io
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select

from app.deps import AccessContext, DbSession, require
from app.models import MigrationRun, MigrationStagingRecord
from app.schemas import MigrationApplyRequest, MigrationRunOut
from app.services.legacy_dbf import apply_run, stage_archive

router = APIRouter(prefix="/migration", tags=["legacy migration"])


def _run(db: DbSession, company_id: uuid.UUID, run_id: uuid.UUID) -> MigrationRun:
    result = db.scalar(
        select(MigrationRun).where(MigrationRun.company_id == company_id, MigrationRun.id == run_id)
    )
    if result is None:
        raise HTTPException(404, "Migration run not found")
    return result


def _out(db: DbSession, run: MigrationRun, *, include_rows: bool = False) -> dict[str, object]:
    value = MigrationRunOut.model_validate(run).model_dump()
    if include_rows:
        value["staging_records"] = list(
            db.scalars(
                select(MigrationStagingRecord)
                .where(
                    MigrationStagingRecord.company_id == run.company_id,
                    MigrationStagingRecord.migration_run_id == run.id,
                    MigrationStagingRecord.severity != "ok",
                )
                .order_by(
                    MigrationStagingRecord.severity.desc(),
                    MigrationStagingRecord.source_table,
                    MigrationStagingRecord.source_record,
                )
                .limit(500)
            ).all()
        )
    return value


@router.post("/stage", response_model=MigrationRunOut, status_code=201)
async def stage_legacy_archive(
    db: DbSession,
    archive: UploadFile = File(...),
    context: AccessContext = Depends(require("migration.run")),
) -> dict[str, object]:
    data = await archive.read()
    run = stage_archive(
        db,
        company_id=context.company_id,
        user_id=context.user.id,
        source_name=archive.filename or "legacy-dbfs.zip",
        archive=data,
    )
    return _out(db, run, include_rows=True)


@router.get("/runs", response_model=list[MigrationRunOut])
def list_runs(
    db: DbSession,
    context: AccessContext = Depends(require("migration.run")),
) -> list[MigrationRun]:
    return list(
        db.scalars(
            select(MigrationRun)
            .where(MigrationRun.company_id == context.company_id)
            .order_by(MigrationRun.created_at.desc())
        ).all()
    )


@router.get("/runs/{run_id}", response_model=MigrationRunOut)
def get_run(
    run_id: uuid.UUID,
    db: DbSession,
    context: AccessContext = Depends(require("migration.run")),
) -> dict[str, object]:
    return _out(db, _run(db, context.company_id, run_id), include_rows=True)


@router.get("/runs/{run_id}/exceptions.csv")
def exception_report(
    run_id: uuid.UUID,
    db: DbSession,
    context: AccessContext = Depends(require("migration.run")),
) -> Response:
    run = _run(db, context.company_id, run_id)
    rows = db.scalars(
        select(MigrationStagingRecord)
        .where(
            MigrationStagingRecord.company_id == context.company_id,
            MigrationStagingRecord.migration_run_id == run.id,
            MigrationStagingRecord.severity != "ok",
        )
        .order_by(MigrationStagingRecord.source_table, MigrationStagingRecord.source_record)
    ).all()
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(
        ["source_table", "source_record", "natural_key", "severity", "code", "field", "message"]
    )
    for row in rows:
        for issue in row.issues:
            writer.writerow(
                [
                    row.source_table,
                    row.source_record,
                    row.natural_key or "",
                    row.severity,
                    issue.get("code", ""),
                    issue.get("field", ""),
                    issue.get("message", ""),
                ]
            )
    return Response(
        content="\ufeff" + stream.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="migration-{run.id}-exceptions.csv"'
        },
    )


@router.post("/runs/{run_id}/apply", response_model=MigrationRunOut)
def apply_staged_run(
    run_id: uuid.UUID,
    payload: MigrationApplyRequest,
    db: DbSession,
    context: AccessContext = Depends(require("migration.run")),
) -> MigrationRun:
    run = _run(db, context.company_id, run_id)
    if run.source_digest != payload.source_digest:
        raise HTTPException(409, "Confirmation digest does not match the staged source")
    return apply_run(db, run, context.user.id)
