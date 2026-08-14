"""Portable entry point for the local test gates."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NPM = shutil.which("npm") or "npm"

COMMANDS = {
    "backend": [
        sys.executable,
        "-m",
        "pytest",
        "backend",
        "--cov=app",
        "--cov-branch",
        "--cov-report=term-missing",
        "--cov-report=html:artifacts/coverage/backend-html",
        "--cov-report=xml:artifacts/coverage/backend.xml",
    ],
    "frontend": [NPM, "--prefix", "frontend", "run", "test:coverage"],
    "e2e-seed": [
        NPM,
        "--prefix",
        "frontend",
        "run",
        "test:e2e",
        "--",
        "e2e/seed.spec.ts",
    ],
    "stage6-security-inventory": [
        sys.executable,
        "scripts/security_gate.py",
        "--inventory",
    ],
    "stage6-security": [sys.executable, "scripts/security_gate.py", "--include-zap"],
    "stage6-data": [sys.executable, "scripts/prepare_stage6_data.py"],
    "stage6-load-smoke": [sys.executable, "scripts/load_test.py", "--profile", "smoke"],
    "stage6-load-release": [
        sys.executable,
        "scripts/load_test.py",
        "--profile",
        "release",
    ],
    "stage6-web-vitals": [NPM, "--prefix", "frontend", "run", "test:web-vitals"],
    "stage6-resilience": [sys.executable, "scripts/resilience_test.py"],
    "stage7-fixtures": [
        sys.executable,
        "scripts/generate_legacy_fixtures.py",
        "--check",
    ],
    "stage7-migration": [
        sys.executable,
        "-m",
        "pytest",
        "backend/tests/test_legacy_migration.py",
        "backend/tests/test_legacy_archive_safety.py",
        "backend/tests/test_legacy_migration_matrix.py",
        "backend/tests/test_legacy_sample.py",
        "--cov=app.services.legacy_dbf",
        "--cov-branch",
        "--cov-report=term-missing",
        "--cov-fail-under=90",
    ],
    "stage8-controls": [
        sys.executable,
        "-m",
        "pytest",
        "backend/tests/test_release_controls.py",
    ],
    "stage8-rehearsal-self-check": [
        sys.executable,
        "scripts/release_rehearsal.py",
        "self-check",
    ],
    "stage8-evidence-draft": [
        sys.executable,
        "scripts/release_evidence.py",
        "--output",
        "artifacts/release/evidence-manifest.json",
        "--force",
    ],
}

DEFAULT_STAGES = ("backend", "frontend", "e2e-seed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=(*COMMANDS, "all"))
    args = parser.parse_args()
    stages = DEFAULT_STAGES if args.stage == "all" else (args.stage,)
    for stage in stages:
        print(f"== {stage} ==", flush=True)
        subprocess.run(COMMANDS[stage], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
