import uuid

from sqlalchemy import select

from app.db import SessionLocal
from app.models import OperationJob, RunStatus
from app.services.integrity import run_integrity_checks
from app.services.reporting import build_report


def run_operation(job_id: uuid.UUID) -> None:
    """Execute one durable operation job and persist its terminal result."""
    with SessionLocal() as db:
        job = db.get(OperationJob, job_id)
        if job is None or job.status in {RunStatus.SUCCEEDED, RunStatus.FAILED}:
            return
        if job.status == RunStatus.QUEUED:
            job.status = RunStatus.RUNNING
            job.progress = 10
            db.commit()
        try:
            if job.kind == "integrity":
                checks = run_integrity_checks(db, job.company_id)
                job.result = {"ok": all(bool(item["ok"]) for item in checks), "checks": checks}
            elif job.kind == "trial_balance":
                report = build_report(db, job.company_id, "trial_balance", job.parameters)
                job.result = {"digest": report.digest, "rows": len(report.rows)}
            else:
                raise ValueError("Unsupported operation")
            job.progress = 100
            job.status = RunStatus.SUCCEEDED
        except Exception as exc:
            job.status = RunStatus.FAILED
            job.error = str(exc)[:2000]
        db.commit()


def process_next_operation() -> bool:
    """Atomically claim one queued job; multiple workers may poll safely."""
    with SessionLocal() as db:
        job = db.scalar(
            select(OperationJob)
            .where(OperationJob.status == RunStatus.QUEUED)
            .order_by(OperationJob.created_at, OperationJob.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job is None:
            return False
        job.status = RunStatus.RUNNING
        job.progress = 10
        job_id = job.id
        db.commit()
    run_operation(job_id)
    return True
