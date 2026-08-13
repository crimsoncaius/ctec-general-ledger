"""Guarded asynchronous Stage 6 load test with financial-integrity evidence."""

from __future__ import annotations

import argparse
import asyncio
import math
import os
import random
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx
import psycopg
from stage6_guard import psycopg_url, require_isolated_url, write_json

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_API_URL = "http://127.0.0.1:28000"
DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://ctec_stage6:stage6_local_only@127.0.0.1:25432/ctec_gl_stage6"
)


@dataclass
class Sample:
    category: str
    elapsed_ms: float
    status: int
    ok: bool
    correlation_id: str | None
    error: str | None = None


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return math.inf
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)]


def ledger_snapshot(database_url: str, company_id: str) -> dict[str, object]:
    with psycopg.connect(psycopg_url(database_url)) as connection:
        row = connection.execute(
            """
            SELECT
              (SELECT count(*) FROM journal_entries WHERE company_id = %s),
              (SELECT count(*) FROM journal_lines WHERE company_id = %s),
              (SELECT count(*) FROM posting_events WHERE company_id = %s),
              (SELECT coalesce(sum(l.debit_base), 0)
                 FROM journal_lines l JOIN journal_entries e
                   ON e.company_id = l.company_id AND e.id = l.entry_id
                WHERE e.company_id = %s AND e.status = 'posted'),
              (SELECT coalesce(sum(l.credit_base), 0)
                 FROM journal_lines l JOIN journal_entries e
                   ON e.company_id = l.company_id AND e.id = l.entry_id
                WHERE e.company_id = %s AND e.status = 'posted')
            """,
            (company_id,) * 5,
        ).fetchone()
    return {
        "journal_entries": row[0],
        "journal_lines": row[1],
        "posting_events": row[2],
        "posted_debit": str(row[3]),
        "posted_credit": str(row[4]),
    }


async def measured(
    client: httpx.AsyncClient,
    samples: list[Sample],
    category: str,
    method: str,
    path: str,
    **kwargs: Any,
) -> httpx.Response | None:
    started = time.perf_counter()
    try:
        response = await client.request(method, path, **kwargs)
        elapsed = (time.perf_counter() - started) * 1000
        samples.append(
            Sample(
                category,
                elapsed,
                response.status_code,
                response.is_success,
                response.headers.get("x-correlation-id"),
                None if response.is_success else response.text[:300],
            )
        )
        return response
    except httpx.HTTPError as exc:
        samples.append(
            Sample(
                category,
                (time.perf_counter() - started) * 1000,
                0,
                False,
                None,
                type(exc).__name__,
            )
        )
        return None


async def authenticate(
    api_url: str, email: str, password: str, company_code: str
) -> tuple[str, str]:
    async with httpx.AsyncClient(base_url=api_url, timeout=20) as client:
        login = await client.post(
            "/api/v1/auth/token", json={"email": email, "password": password}
        )
        login.raise_for_status()
        token = login.json()["access_token"]
        me = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        me.raise_for_status()
        company = next(
            item for item in me.json()["companies"] if item["code"] == company_code
        )
        return token, company["id"]


async def virtual_user(
    *,
    user_id: int,
    api_url: str,
    token: str,
    company_id: str,
    period_id: str,
    deadline: float,
    think_seconds: float,
    samples: list[Sample],
) -> None:
    headers = {"Authorization": f"Bearer {token}", "X-Company-ID": company_id}
    timeout = httpx.Timeout(15, connect=5)
    async with httpx.AsyncClient(
        base_url=api_url, headers=headers, timeout=timeout
    ) as client:
        iteration = 0
        read_paths = ["/api/v1/accounts", "/api/v1/journals", "/api/v1/fiscal/periods"]
        while time.monotonic() < deadline:
            selector = iteration % 20
            if selector == 5:
                await measured(
                    client,
                    samples,
                    "write",
                    "PUT",
                    f"/api/v1/administration/preferences/stage6-user-{user_id}",
                    json={"value": {"iteration": iteration}},
                )
            elif selector == 9:
                await measured(
                    client,
                    samples,
                    "report",
                    "POST",
                    "/api/v1/reports/run",
                    json={
                        "report_type": "trial_balance",
                        "parameters": {"period_id": period_id, "include_zero": True},
                        "format": "json",
                    },
                )
            elif selector == 15:
                await measured(
                    client,
                    samples,
                    "export",
                    "POST",
                    "/api/v1/reports/run",
                    json={
                        "report_type": "trial_balance",
                        "parameters": {"period_id": period_id, "include_zero": True},
                        "format": "csv",
                    },
                )
            else:
                await measured(
                    client,
                    samples,
                    "read",
                    "GET",
                    random.choice(read_paths),
                )
            iteration += 1
            await asyncio.sleep(think_seconds)


async def run_phase(
    *,
    users: int,
    duration: float,
    api_url: str,
    token: str,
    company_id: str,
    period_id: str,
    think_seconds: float,
    samples: list[Sample],
) -> None:
    deadline = time.monotonic() + duration
    async with asyncio.TaskGroup() as group:
        for user_id in range(users):
            group.create_task(
                virtual_user(
                    user_id=user_id,
                    api_url=api_url,
                    token=token,
                    company_id=company_id,
                    period_id=period_id,
                    deadline=deadline,
                    think_seconds=think_seconds,
                    samples=samples,
                )
            )


async def execute(args: argparse.Namespace) -> dict[str, object]:
    api_url = require_isolated_url(args.api_url, label="STAGE6_API_URL")
    token, company_id = await authenticate(
        api_url, args.email, args.password, args.company_code
    )
    headers = {"Authorization": f"Bearer {token}", "X-Company-ID": company_id}
    async with httpx.AsyncClient(
        base_url=api_url, headers=headers, timeout=20
    ) as client:
        periods = await client.get("/api/v1/fiscal/periods")
        periods.raise_for_status()
        period_id = periods.json()[0]["id"]

    before = ledger_snapshot(args.database_url, company_id)
    samples: list[Sample] = []
    await run_phase(
        users=args.users,
        duration=args.duration,
        api_url=api_url,
        token=token,
        company_id=company_id,
        period_id=period_id,
        think_seconds=args.think_seconds,
        samples=samples,
    )
    await run_phase(
        users=args.spike_users,
        duration=args.spike_duration,
        api_url=api_url,
        token=token,
        company_id=company_id,
        period_id=period_id,
        think_seconds=args.think_seconds,
        samples=samples,
    )
    async with httpx.AsyncClient(
        base_url=api_url, headers=headers, timeout=30
    ) as client:
        integrity = await client.post("/api/v1/ledger/integrity")
        integrity.raise_for_status()
        integrity_result = integrity.json()
    after = ledger_snapshot(args.database_url, company_id)

    grouped: dict[str, list[Sample]] = defaultdict(list)
    for sample in samples:
        grouped[sample.category].append(sample)
    limits = {"read": 750, "write": 1500, "report": 5000, "export": 10_000}
    metrics = {
        category: {
            "requests": len(items),
            "errors": sum(not item.ok for item in items),
            "p95_ms": round(percentile([item.elapsed_ms for item in items], 0.95), 2),
            "limit_ms": limits[category],
        }
        for category, items in grouped.items()
    }
    total = len(samples)
    errors = sum(not sample.ok for sample in samples)
    error_rate = errors / total if total else 1.0
    failures: list[str] = []
    for category, limit in limits.items():
        category_result = metrics.get(category)
        if category_result is None:
            failures.append(f"no {category} requests were measured")
        elif float(category_result["p95_ms"]) > limit:
            failures.append(f"{category} p95 exceeded {limit} ms")
    if error_rate >= 0.01:
        failures.append(f"HTTP error rate {error_rate:.3%} was not below 1%")
    if before != after:
        failures.append("immutable ledger snapshot changed during the load test")
    if not integrity_result["ok"]:
        failures.append("post-load integrity check failed")
    if args.profile == "release" and int(before["journal_lines"]) < 100_000:
        failures.append("release profile requires at least 100,000 journal lines")

    return {
        "profile": args.profile,
        "configuration": {
            "users": args.users,
            "duration_seconds": args.duration,
            "spike_users": args.spike_users,
            "spike_duration_seconds": args.spike_duration,
            "think_seconds": args.think_seconds,
            "company_code": args.company_code,
        },
        "passed": not failures,
        "error_rate": error_rate,
        "metrics": metrics,
        "ledger_before": before,
        "ledger_after": after,
        "integrity": integrity_result,
        "failures": failures,
        "failed_samples": [asdict(sample) for sample in samples if not sample.ok][:100],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("smoke", "release"), default="smoke")
    parser.add_argument(
        "--api-url", default=os.getenv("STAGE6_API_URL", DEFAULT_API_URL)
    )
    parser.add_argument(
        "--database-url", default=os.getenv("STAGE6_DATABASE_URL", DEFAULT_DATABASE_URL)
    )
    parser.add_argument(
        "--company-code", default=os.getenv("STAGE6_COMPANY_CODE", "ACME")
    )
    parser.add_argument(
        "--email", default=os.getenv("STAGE6_ADMIN_EMAIL", "admin@example.com")
    )
    parser.add_argument(
        "--password",
        default=os.getenv("STAGE6_ADMIN_PASSWORD", "CTec-Demo-Admin-2026!"),
    )
    parser.add_argument("--users", type=int)
    parser.add_argument("--duration", type=float)
    parser.add_argument("--spike-users", type=int)
    parser.add_argument("--spike-duration", type=float)
    parser.add_argument("--think-seconds", type=float, default=0.2)
    args = parser.parse_args()
    defaults = (
        {"users": 2, "duration": 8.0, "spike_users": 3, "spike_duration": 8.0}
        if args.profile == "smoke"
        else {
            "users": 15,
            "duration": 1800.0,
            "spike_users": 30,
            "spike_duration": 300.0,
        }
    )
    for name, value in defaults.items():
        if getattr(args, name) is None:
            setattr(args, name, value)
    if (
        min(args.users, args.spike_users) < 1
        or min(args.duration, args.spike_duration) <= 0
    ):
        parser.error("user counts and durations must be positive")
    return args


def main() -> int:
    args = parse_args()
    result = asyncio.run(execute(args))
    output = ROOT / "artifacts" / "performance" / f"load-{args.profile}.json"
    write_json(output, result)
    print(f"Stage 6 load test passed={result['passed']}; evidence: {output}")
    for failure in result["failures"]:
        print(f"FAIL: {failure}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
