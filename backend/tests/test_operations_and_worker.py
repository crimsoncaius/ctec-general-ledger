from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

import app.worker as worker
from app.db import SessionLocal
from app.models import OperationJob, RunStatus
from app.services.operations import process_next_operation, run_operation


def _job(company_id: uuid.UUID, user_id: uuid.UUID, kind: str, **parameters: object) -> uuid.UUID:
    with SessionLocal() as db:
        job = OperationJob(
            company_id=company_id,
            requested_by_id=user_id,
            kind=kind,
            parameters=parameters,
        )
        db.add(job)
        db.commit()
        return job.id


def test_operations_handle_missing_terminal_success_and_failure_jobs(acme_ledger) -> None:
    company_id = acme_ledger["company_id"]
    user_id = acme_ledger["users"]["admin@example.com"]

    run_operation(uuid.uuid4())
    for terminal in (RunStatus.SUCCEEDED, RunStatus.FAILED):
        job_id = _job(company_id, user_id, "integrity")
        with SessionLocal() as db:
            job = db.get(OperationJob, job_id)
            assert job is not None
            job.status = terminal
            job.progress = 77
            db.commit()
        run_operation(job_id)
        with SessionLocal() as db:
            job = db.get(OperationJob, job_id)
            assert job is not None
            assert job.status == terminal and job.progress == 77

    trial_id = _job(
        company_id,
        user_id,
        "trial_balance",
        period_id=str(acme_ledger["period_id"]),
        include_zero=True,
    )
    run_operation(trial_id)
    with SessionLocal() as db:
        trial = db.get(OperationJob, trial_id)
        assert trial is not None
        assert trial.status == RunStatus.SUCCEEDED
        assert trial.progress == 100
        assert trial.result is not None and trial.result["rows"] > 0
        assert len(str(trial.result["digest"])) == 64

    unsupported_id = _job(company_id, user_id, "unsupported")
    run_operation(unsupported_id)
    with SessionLocal() as db:
        unsupported = db.get(OperationJob, unsupported_id)
        assert unsupported is not None
        assert unsupported.status == RunStatus.FAILED
        assert unsupported.error == "Unsupported operation"


def test_process_next_operation_claims_once_and_reports_an_empty_queue(acme_ledger) -> None:
    company_id = acme_ledger["company_id"]
    user_id = acme_ledger["users"]["admin@example.com"]
    job_id = _job(company_id, user_id, "integrity")

    assert process_next_operation() is True
    with SessionLocal() as db:
        job = db.get(OperationJob, job_id)
        assert job is not None
        assert job.status == RunStatus.SUCCEEDED
        assert job.progress == 100
        assert job.result is not None and job.result["ok"] is True
        assert (
            db.scalar(select(OperationJob.id).where(OperationJob.status == RunStatus.QUEUED))
            is None
        )
    assert process_next_operation() is False


def test_worker_stop_idle_poll_and_polling_failure_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    worker.running = True
    worker._stop(15, object())
    assert worker.running is False

    registered: list[int] = []
    sleeps: list[int] = []
    monkeypatch.setattr(worker.signal, "signal", lambda number, _handler: registered.append(number))
    monkeypatch.setattr(worker.time, "sleep", sleeps.append)

    worker.running = True

    def idle_once() -> bool:
        worker.running = False
        return False

    monkeypatch.setattr(worker, "process_next_operation", idle_once)
    worker.main()
    assert registered == [worker.signal.SIGTERM, worker.signal.SIGINT]
    assert sleeps == [1]

    worker.running = True

    def fail_once() -> bool:
        worker.running = False
        raise RuntimeError("poll failed")

    monkeypatch.setattr(worker, "process_next_operation", fail_once)
    worker.main()
    assert sleeps == [1, 2]
