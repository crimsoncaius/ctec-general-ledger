"""Shared safety checks for destructive Stage 6 tooling."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

LIVE_PORTS = {5173, 8000}
SAFE_DATABASE_PREFIXES = (
    "ctec_gl_stage6",
    "ctec_gl_perf",
    "ctec_gl_e2e",
    "ctec_gl_test_",
)
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1", "host.docker.internal"}


def require_isolated_url(raw_url: str, *, label: str) -> str:
    parsed = urlparse(raw_url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in LOOPBACK_HOSTS:
        raise RuntimeError(f"{label} must be an explicit loopback URL, got {raw_url!r}")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if port in LIVE_PORTS:
        raise RuntimeError(f"{label} must not target demonstration port {port}")
    return raw_url.rstrip("/")


def require_isolated_database(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    database = parsed.path.lstrip("/").split("?", 1)[0]
    if not database.startswith(SAFE_DATABASE_PREFIXES):
        allowed = ", ".join(SAFE_DATABASE_PREFIXES)
        raise RuntimeError(
            f"Refusing database {database!r}; Stage 6 database names must start with {allowed}"
        )
    return raw_url


def psycopg_url(raw_url: str) -> str:
    require_isolated_database(raw_url)
    return raw_url.replace("postgresql+psycopg://", "postgresql://", 1)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")
