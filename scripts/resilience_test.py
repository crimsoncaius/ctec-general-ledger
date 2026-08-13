"""Exercise worker/API/DB recovery only inside the named Stage 6 Compose project."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx
import psycopg
from stage6_guard import psycopg_url, require_isolated_url, write_json

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "docker-compose.stage6.yml"
PROJECT = "ctec-stage6"
API_URL = "http://127.0.0.1:28000"
DATABASE_URL = (
    "postgresql+psycopg://ctec_stage6:stage6_local_only@127.0.0.1:25432/ctec_gl_stage6"
)


def compose(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    docker = shutil.which("docker")
    if docker is None:
        raise RuntimeError("Docker is required for the isolated resilience drill")
    return subprocess.run(
        [docker, "compose", "-p", PROJECT, "-f", str(COMPOSE_FILE), *arguments],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def authenticate(api_url: str) -> tuple[str, str]:
    with httpx.Client(base_url=api_url, timeout=10) as client:
        response = client.post(
            "/api/v1/auth/token",
            json={
                "email": os.getenv("STAGE6_ADMIN_EMAIL", "admin@example.com"),
                "password": os.getenv("STAGE6_ADMIN_PASSWORD", "CTec-Demo-Admin-2026!"),
            },
        )
        response.raise_for_status()
        token = response.json()["access_token"]
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        me.raise_for_status()
        company_code = os.getenv("STAGE6_COMPANY_CODE", "ACME")
        company = next(
            item for item in me.json()["companies"] if item["code"] == company_code
        )
        return token, company["id"]


def ledger_snapshot(database_url: str, company_id: str) -> dict[str, object]:
    with psycopg.connect(psycopg_url(database_url)) as connection:
        row = connection.execute(
            """
            SELECT count(DISTINCT e.id), count(l.id), count(DISTINCT pe.id),
                   coalesce(sum(l.debit_base), 0), coalesce(sum(l.credit_base), 0)
            FROM journal_entries e
            JOIN journal_lines l ON l.company_id = e.company_id AND l.entry_id = e.id
            LEFT JOIN posting_events pe ON pe.company_id = e.company_id AND pe.entry_id = e.id
            WHERE e.company_id = %s AND e.status = 'posted'
            """,
            (company_id,),
        ).fetchone()
    return {
        "posted_entries": row[0],
        "posted_lines": row[1],
        "posting_events": row[2],
        "debit": str(row[3]),
        "credit": str(row[4]),
    }


def wait_for_jobs(
    client: httpx.Client, job_ids: set[str], timeout: float = 90
) -> list[dict[str, Any]]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get("/api/v1/administration/operations")
        response.raise_for_status()
        jobs = [item for item in response.json() if item["id"] in job_ids]
        if len(jobs) == len(job_ids) and all(
            item["status"] in {"succeeded", "failed"} for item in jobs
        ):
            return jobs
        time.sleep(1)
    raise RuntimeError(f"Timed out waiting for operation jobs: {sorted(job_ids)}")


def main() -> int:
    api_url = require_isolated_url(
        os.getenv("STAGE6_API_URL", API_URL), label="STAGE6_API_URL"
    )
    database_url = os.getenv("STAGE6_DATABASE_URL", DATABASE_URL)
    psycopg_url(database_url)
    if COMPOSE_FILE.name != "docker-compose.stage6.yml" or PROJECT != "ctec-stage6":
        raise RuntimeError("Resilience drill project identity was altered")
    compose("ps", "--status", "running")

    token, company_id = authenticate(api_url)
    headers = {"Authorization": f"Bearer {token}", "X-Company-ID": company_id}
    before = ledger_snapshot(database_url, company_id)
    evidence: dict[str, Any] = {"project": PROJECT, "ledger_before": before}
    db_stopped = False
    try:
        compose("stop", "worker")
        with httpx.Client(base_url=api_url, headers=headers, timeout=15) as client:
            queued = client.post(
                "/api/v1/administration/operations",
                json={"kind": "integrity", "parameters": {}},
            )
            queued.raise_for_status()
            queued_id = queued.json()["id"]
            evidence["queued_while_worker_stopped"] = (
                queued.json()["status"] == "queued"
            )
        compose("start", "worker")
        with httpx.Client(base_url=api_url, headers=headers, timeout=15) as client:
            evidence["worker_restart_jobs"] = wait_for_jobs(client, {queued_id})

        compose("up", "-d", "--scale", "worker=3", "worker")
        with httpx.Client(base_url=api_url, headers=headers, timeout=15) as client:
            job_ids: set[str] = set()
            for _ in range(12):
                response = client.post(
                    "/api/v1/administration/operations",
                    json={"kind": "integrity", "parameters": {}},
                )
                response.raise_for_status()
                job_ids.add(response.json()["id"])
            jobs = wait_for_jobs(client, job_ids)
            evidence["concurrent_workers"] = {
                "requested": 12,
                "unique_ids": len(job_ids),
                "terminal_rows": len(jobs),
                "all_succeeded": all(item["status"] == "succeeded" for item in jobs),
            }
        compose("up", "-d", "--scale", "worker=1", "worker")

        compose("restart", "api")
        deadline = time.monotonic() + 60
        while True:
            try:
                authenticate(api_url)
                evidence["api_restart_recovered"] = True
                break
            except (httpx.HTTPError, ConnectionError):
                if time.monotonic() >= deadline:
                    raise RuntimeError("API did not recover after restart")
                time.sleep(1)

        compose("stop", "db")
        db_stopped = True
        try:
            authenticate(api_url)
            evidence["db_outage_rejected_request"] = False
        except (httpx.HTTPError, ConnectionError):
            evidence["db_outage_rejected_request"] = True
        compose("start", "db")
        db_stopped = False
        deadline = time.monotonic() + 90
        while True:
            try:
                token, company_id = authenticate(api_url)
                evidence["db_recovery_succeeded"] = True
                break
            except (httpx.HTTPError, ConnectionError):
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        "API did not recover after the Stage 6 DB restart"
                    )
                time.sleep(1)
    finally:
        if db_stopped:
            compose("start", "db", check=False)
        compose("up", "-d", "--scale", "worker=1", "worker", check=False)
        logs = compose(
            "logs", "--no-color", "--tail", "500", "api", "worker", "db", check=False
        )
        log_path = ROOT / "artifacts" / "resilience" / "compose.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(logs.stdout + logs.stderr, encoding="utf-8")

    after = ledger_snapshot(database_url, company_id)
    evidence["ledger_after"] = after
    evidence["ledger_unchanged"] = before == after
    evidence["passed"] = all(
        (
            evidence.get("queued_while_worker_stopped") is True,
            evidence.get("api_restart_recovered") is True,
            evidence.get("db_outage_rejected_request") is True,
            evidence.get("db_recovery_succeeded") is True,
            evidence["concurrent_workers"]["unique_ids"] == 12,
            evidence["concurrent_workers"]["terminal_rows"] == 12,
            evidence["concurrent_workers"]["all_succeeded"] is True,
            evidence["ledger_unchanged"] is True,
            before["debit"] == before["credit"],
        )
    )
    output = ROOT / "artifacts" / "resilience" / "summary.json"
    write_json(output, evidence)
    print(f"Stage 6 resilience passed={evidence['passed']}; evidence: {output}")
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
