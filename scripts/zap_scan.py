"""Run an authenticated ZAP OpenAPI scan against the isolated Stage 6 API."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import httpx
from stage6_guard import require_isolated_database, require_isolated_url

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "security" / "zap"
ZAP_IMAGE = "zaproxy/zap-stable:2.16.1"


def container_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    return urlunparse(parsed._replace(netloc=f"host.docker.internal:{parsed.port}"))


def main() -> int:
    api_url = require_isolated_url(
        os.getenv("STAGE6_API_URL", "http://127.0.0.1:28000"), label="STAGE6_API_URL"
    )
    require_isolated_database(
        os.getenv(
            "STAGE6_DATABASE_URL",
            "postgresql+psycopg://ctec_stage6:stage6_local_only@127.0.0.1:25432/ctec_gl_stage6",
        )
    )
    docker = shutil.which("docker")
    if docker is None:
        raise RuntimeError("Docker is required for the pinned ZAP scanner")
    inspect = subprocess.run(
        [docker, "image", "inspect", ZAP_IMAGE],
        capture_output=True,
        text=True,
        check=False,
    )
    if inspect.returncode != 0:
        raise RuntimeError(
            f"Missing {ZAP_IMAGE}; pull the pinned image before the release scan"
        )

    email = os.getenv("STAGE6_ADMIN_EMAIL", "admin@example.com")
    password = os.getenv("STAGE6_ADMIN_PASSWORD", "CTec-Demo-Admin-2026!")
    company_code = os.getenv("STAGE6_COMPANY_CODE", "ACME")
    with httpx.Client(base_url=api_url, timeout=15) as client:
        login = client.post(
            "/api/v1/auth/token", json={"email": email, "password": password}
        )
        login.raise_for_status()
        token = login.json()["access_token"]
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        me.raise_for_status()
        company = next(
            item for item in me.json()["companies"] if item["code"] == company_code
        )

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    target = container_url(api_url)
    runner = """#!/bin/sh
set -eu
zap-api-scan.py -t \"$ZAP_TARGET/openapi.json\" -f openapi \\
  -r /zap/wrk/zap.html -J /zap/wrk/zap.json -w /zap/wrk/zap.md \\
  -z \"-config replacer.full_list(0).description=stage6-auth \\
-config replacer.full_list(0).enabled=true \\
-config replacer.full_list(0).matchtype=REQ_HEADER \\
-config replacer.full_list(0).matchstr=Authorization \\
-config replacer.full_list(0).replacement=$ZAP_AUTHORIZATION \\
-config replacer.full_list(1).description=stage6-company \\
-config replacer.full_list(1).enabled=true \\
-config replacer.full_list(1).matchtype=REQ_HEADER \\
-config replacer.full_list(1).matchstr=X-Company-ID \\
-config replacer.full_list(1).replacement=$ZAP_COMPANY_ID\"
"""
    with tempfile.TemporaryDirectory(prefix="ctec-zap-") as temporary:
        script = Path(temporary) / "run.sh"
        script.write_text(runner, encoding="utf-8", newline="\n")
        environment = {
            **os.environ,
            "ZAP_TARGET": target,
            "ZAP_AUTHORIZATION": f"Bearer {token}",
            "ZAP_COMPANY_ID": str(company["id"]),
        }
        command = [
            docker,
            "run",
            "--rm",
            "--add-host",
            "host.docker.internal:host-gateway",
            "-e",
            "ZAP_TARGET",
            "-e",
            "ZAP_AUTHORIZATION",
            "-e",
            "ZAP_COMPANY_ID",
            "-v",
            f"{ARTIFACTS.resolve()}:/zap/wrk:rw",
            "-v",
            f"{script.resolve()}:/zap/run-stage6.sh:ro",
            ZAP_IMAGE,
            "sh",
            "/zap/run-stage6.sh",
        ]
        result = subprocess.run(command, env=environment, check=False)
    if result.returncode != 0:
        print(f"ZAP failed with exit code {result.returncode}; see {ARTIFACTS}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
