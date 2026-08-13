"""Guarded backup, isolated restore, upgrade and verification release rehearsal."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

ALLOWED_TARGET_PREFIXES = ("ctec_gl_restore_", "ctec_gl_rehearsal_")
ACKNOWLEDGEMENT = "RESTORE TO ISOLATED TARGET"
ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class DatabaseTarget:
    url: URL

    @property
    def database(self) -> str:
        return self.url.database or ""

    def tool_environment(self) -> dict[str, str]:
        env = os.environ.copy()
        if self.url.password:
            env["PGPASSWORD"] = self.url.password
        return env

    def tool_args(self) -> list[str]:
        args: list[str] = []
        if self.url.host:
            args.extend(("--host", self.url.host))
        if self.url.port:
            args.extend(("--port", str(self.url.port)))
        if self.url.username:
            args.extend(("--username", self.url.username))
        args.extend(("--dbname", self.database))
        return args

    def redacted(self) -> str:
        return self.url.render_as_string(hide_password=True)


def database_target(raw_url: str) -> DatabaseTarget:
    try:
        url = make_url(raw_url)
    except ArgumentError as exc:
        raise ValueError("A valid PostgreSQL URL is required") from exc
    if not url.database or not url.drivername.startswith("postgresql"):
        raise ValueError("A PostgreSQL URL with a database name is required")
    return DatabaseTarget(url)


def require_isolated_target(target: DatabaseTarget) -> None:
    if not target.database.startswith(ALLOWED_TARGET_PREFIXES):
        allowed = " or ".join(f"{prefix}*" for prefix in ALLOWED_TARGET_PREFIXES)
        raise ValueError(f"Refusing target database {target.database!r}; use {allowed}")


def require_distinct(source: DatabaseTarget, target: DatabaseTarget) -> None:
    source_identity = (source.url.host, source.url.port, source.database)
    target_identity = (target.url.host, target.url.port, target.database)
    if source_identity == target_identity:
        raise ValueError("Source and restore target must be different databases")


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_tool(name: str) -> str:
    found = shutil.which(name)
    if found is None:
        raise RuntimeError(f"Required PostgreSQL tool is unavailable: {name}")
    return found


def run(command: list[str], target: DatabaseTarget) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        env=target.tool_environment(),
        text=True,
        capture_output=True,
    )


def ensure_empty_target(target: DatabaseTarget) -> None:
    query = "SELECT count(*) FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema')"
    result = run(
        [
            require_tool("psql"),
            *target.tool_args(),
            "--tuples-only",
            "--no-align",
            "--command",
            query,
        ],
        target,
    )
    if int(result.stdout.strip() or "0") != 0:
        raise RuntimeError(
            "Restore target is not empty; provision a new isolated database"
        )


def backup(source: DatabaseTarget, output: Path) -> dict[str, object]:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing backup: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".partial")
    if temporary.exists():
        raise FileExistsError(f"Remove stale partial backup first: {temporary}")
    run(
        [
            require_tool("pg_dump"),
            *source.tool_args(),
            "--format",
            "custom",
            "--file",
            str(temporary),
        ],
        source,
    )
    temporary.replace(output)
    digest = checksum(output)
    checksum_file = output.with_suffix(output.suffix + ".sha256")
    checksum_file.write_text(f"{digest}  {output.name}\n", encoding="ascii")
    return {"backup": str(output), "sha256": digest, "source": source.redacted()}


def restore(
    backup_path: Path,
    expected_sha256: str,
    source: DatabaseTarget,
    target: DatabaseTarget,
) -> dict[str, object]:
    require_isolated_target(target)
    require_distinct(source, target)
    actual = checksum(backup_path)
    if actual.lower() != expected_sha256.lower():
        raise RuntimeError(
            f"Backup checksum mismatch: expected {expected_sha256}, got {actual}"
        )
    ensure_empty_target(target)
    run(
        [
            require_tool("pg_restore"),
            *target.tool_args(),
            "--exit-on-error",
            "--no-owner",
            "--no-privileges",
            str(backup_path),
        ],
        target,
    )
    return {"restored": str(backup_path), "sha256": actual, "target": target.redacted()}


def upgrade(target: DatabaseTarget) -> dict[str, object]:
    require_isolated_target(target)
    env = target.tool_environment()
    env["DATABASE_URL"] = target.url.render_as_string(hide_password=False)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(ROOT / "backend/alembic.ini"),
            "upgrade",
            "head",
        ],
        cwd=ROOT,
        env=env,
        check=True,
    )
    return {"upgraded": target.redacted(), "revision": "head", "downgrade_used": False}


def verify(target: DatabaseTarget) -> dict[str, object]:
    require_isolated_target(target)
    queries = {
        "alembic_revision": "SELECT version_num FROM alembic_version",
        "companies": "SELECT count(*) FROM companies",
        "accounts": "SELECT count(*) FROM accounts",
        "journal_batches": "SELECT count(*) FROM journal_batches",
        "journal_lines": "SELECT count(*) FROM journal_lines",
        "migration_runs": "SELECT count(*) FROM migration_runs",
        "report_runs": "SELECT count(*) FROM report_runs",
    }
    values: dict[str, str] = {}
    psql = require_tool("psql")
    for name, query in queries.items():
        result = run(
            [
                psql,
                *target.tool_args(),
                "--tuples-only",
                "--no-align",
                "--command",
                query,
            ],
            target,
        )
        values[name] = result.stdout.strip()
    return {
        "target": target.redacted(),
        "checks": values,
        "read_only_verification": True,
    }


def self_check() -> dict[str, object]:
    sample = database_target(
        "postgresql+psycopg://user:secret@127.0.0.1:5432/ctec_gl_restore_example"
    )
    require_isolated_target(sample)
    try:
        require_isolated_target(
            database_target("postgresql://user:secret@127.0.0.1:5432/ctec_gl")
        )
    except ValueError:
        rejected_live_name = True
    else:
        rejected_live_name = False
    return {
        "status": "ok" if rejected_live_name else "failed",
        "live_name_rejected": rejected_live_name,
        "example": sample.redacted(),
        "acknowledgement": ACKNOWLEDGEMENT,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("self-check")
    backup_parser = subparsers.add_parser("backup")
    backup_parser.add_argument("--source-url", required=True)
    backup_parser.add_argument("--output", required=True, type=Path)
    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("--source-url", required=True)
    restore_parser.add_argument("--target-url", required=True)
    restore_parser.add_argument("--backup", required=True, type=Path)
    restore_parser.add_argument("--sha256", required=True)
    restore_parser.add_argument("--acknowledge", required=True)
    upgrade_parser = subparsers.add_parser("upgrade")
    upgrade_parser.add_argument("--target-url", required=True)
    upgrade_parser.add_argument("--acknowledge", required=True)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--target-url", required=True)
    args = parser.parse_args()
    if args.command == "self-check":
        result = self_check()
    elif args.command == "backup":
        result = backup(database_target(args.source_url), args.output)
    elif args.command == "restore":
        if args.acknowledge != ACKNOWLEDGEMENT:
            raise SystemExit(f"Required acknowledgement: {ACKNOWLEDGEMENT}")
        result = restore(
            args.backup,
            args.sha256,
            database_target(args.source_url),
            database_target(args.target_url),
        )
    elif args.command == "upgrade":
        if args.acknowledge != ACKNOWLEDGEMENT:
            raise SystemExit(f"Required acknowledgement: {ACKNOWLEDGEMENT}")
        result = upgrade(database_target(args.target_url))
    else:
        result = verify(database_target(args.target_url))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
