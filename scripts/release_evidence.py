"""Create or validate a release evidence manifest without inventing approvals."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "artifacts/release/evidence-manifest.json"
EVIDENCE = {
    "coverage": "artifacts/coverage/backend.xml",
    "frontend_coverage": "artifacts/coverage/frontend/coverage-summary.json",
    "security": "artifacts/security/summary.json",
    "performance": "artifacts/performance/load-release.json",
    "resilience": "artifacts/resilience/summary.json",
    "migration_controls": "artifacts/legacy-fixtures/manifest.json",
    "migration_reconciliation": "artifacts/release/migration-reconciliation.json",
    "restore_rehearsal": "artifacts/release/restore-verification.json",
    "uat": "artifacts/release/uat-results.json",
}
APPROVALS = ("accounting", "qa", "security", "operations", "release_owner")


def file_evidence(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    if not path.is_file():
        return {"path": relative, "status": "missing", "sha256": None}
    return {
        "path": relative,
        "status": "present-unreviewed",
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
    }


def git_value(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def git_status() -> str:
    porcelain = git_value("status", "--porcelain")
    if porcelain == "unavailable":
        return "unavailable"
    return "clean" if not porcelain else "dirty"


def build_manifest() -> dict[str, Any]:
    pyproject = (ROOT / "backend/pyproject.toml").read_text(encoding="utf-8")
    version_line = next(
        line for line in pyproject.splitlines() if line.startswith("version = ")
    )
    revisions = sorted(
        path.stem
        for path in (ROOT / "backend/alembic/versions").glob("*.py")
        if not path.name.startswith("__")
    )
    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "release_candidate": {
            "application_version": version_line.split('"')[1],
            "git_commit": git_value("rev-parse", "HEAD"),
            "git_status": git_status(),
            "alembic_latest_file": revisions[-1] if revisions else None,
        },
        "evidence": {name: file_evidence(path) for name, path in EVIDENCE.items()},
        "approvals": {
            role: {
                "status": "pending",
                "approver": None,
                "timestamp": None,
                "reference": None,
            }
            for role in APPROVALS
        },
        "release_decision": {
            "status": "pending",
            "reason": "Evidence review and human approvals are required.",
        },
        "claims": {
            "long_running_performance_completed": False,
            "external_security_review_completed": False,
            "human_uat_approved": False,
        },
    }


def validate(manifest: dict[str, Any]) -> list[str]:
    failures = [
        f"missing evidence: {name}"
        for name, value in manifest.get("evidence", {}).items()
        if value.get("status") == "missing"
    ]
    failures.extend(
        f"pending approval: {role}"
        for role, value in manifest.get("approvals", {}).items()
        if value.get("status") != "approved"
    )
    if manifest.get("release_decision", {}).get("status") != "approved":
        failures.append("release decision is not approved")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--validate", type=Path)
    args = parser.parse_args()
    if args.validate:
        failures = validate(json.loads(args.validate.read_text(encoding="utf-8")))
        print(
            json.dumps(
                {"status": "pass" if not failures else "blocked", "failures": failures},
                indent=2,
            )
        )
        raise SystemExit(0 if not failures else 1)
    if args.output.exists() and not args.force:
        raise SystemExit(
            f"Refusing to overwrite {args.output}; pass --force for an intentional refresh"
        )
    manifest = build_manifest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "draft-created",
                "output": str(args.output),
                "missing": len(validate(manifest)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
