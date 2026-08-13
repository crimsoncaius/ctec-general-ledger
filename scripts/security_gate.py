"""Fail-closed Stage 6 static, dependency, secret, and image security gate."""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from stage6_guard import write_json

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "security"


def run_step(name: str, command: list[str], *, cwd: Path = ROOT) -> dict[str, Any]:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        command, cwd=cwd, text=True, capture_output=True, check=False
    )
    (ARTIFACTS / f"{name}.stdout.log").write_text(result.stdout, encoding="utf-8")
    (ARTIFACTS / f"{name}.stderr.log").write_text(result.stderr, encoding="utf-8")
    return {
        "name": name,
        "status": "passed" if result.returncode == 0 else "failed",
        "exit_code": result.returncode,
        "command": [
            Path(value).name if index == 0 else value
            for index, value in enumerate(command)
        ],
        "stdout": str(ARTIFACTS / f"{name}.stdout.log"),
        "stderr": str(ARTIFACTS / f"{name}.stderr.log"),
    }


def missing(name: str, install: str) -> dict[str, Any]:
    return {"name": name, "status": "missing", "install": install}


def image_exists(image: str) -> bool:
    docker = shutil.which("docker")
    if docker is None:
        return False
    result = subprocess.run(
        [docker, "image", "inspect", image], capture_output=True, text=True, check=False
    )
    return result.returncode == 0


def gitleaks_step() -> dict[str, Any]:
    executable = shutil.which("gitleaks")
    if executable is None:
        return missing("gitleaks", "Install gitleaks 8.27.2 and place it on PATH")
    return run_step(
        "gitleaks",
        [
            executable,
            "detect",
            "--source",
            ".",
            "--no-git",
            "--redact",
            "--config",
            ".gitleaks.toml",
            "--report-format",
            "json",
            "--report-path",
            str(ARTIFACTS / "gitleaks.json"),
        ],
    )


def python_module_step(
    name: str, module: str, arguments: list[str], install: str
) -> dict[str, Any]:
    if importlib.util.find_spec(module) is None:
        return missing(name, install)
    return run_step(name, [sys.executable, "-m", module, *arguments])


def trivy_step(name: str, image: str) -> dict[str, Any]:
    executable = shutil.which("trivy")
    if executable is None:
        return missing(name, "Install Trivy 0.65.0 and place it on PATH")
    if not image_exists(image):
        return missing(name, f"Build the pinned local image first: {image}")
    return run_step(
        name,
        [
            executable,
            "image",
            "--scanners",
            "vuln,secret,misconfig",
            "--severity",
            "HIGH,CRITICAL",
            "--exit-code",
            "1",
            "--format",
            "json",
            "--output",
            str(ARTIFACTS / f"{name}.json"),
            image,
        ],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inventory",
        action="store_true",
        help="Report unavailable tools without passing the release gate",
    )
    parser.add_argument("--include-zap", action="store_true")
    parser.add_argument("--api-image", default="ctec-gl-api:stage6")
    parser.add_argument("--web-image", default="ctec-gl-web:stage6")
    args = parser.parse_args()

    npm = shutil.which("npm")
    results = [gitleaks_step()]
    results.append(
        python_module_step(
            "pip-audit",
            "pip_audit",
            [
                "--local",
                "--format",
                "json",
                "--output",
                str(ARTIFACTS / "pip-audit.json"),
            ],
            'Install the backend dev extra: pip install -e ".\\backend[dev]"',
        )
    )
    results.append(
        python_module_step(
            "bandit",
            "bandit",
            [
                "-r",
                "backend/app",
                "-lll",
                "-ii",
                "-f",
                "json",
                "-o",
                str(ARTIFACTS / "bandit.json"),
            ],
            'Install the backend dev extra: pip install -e ".\\backend[dev]"',
        )
    )
    if npm is None:
        results.append(missing("npm-audit", "Install Node.js 22 and npm"))
    else:
        results.append(
            run_step(
                "npm-audit",
                [npm, "audit", "--package-lock-only", "--audit-level=high", "--json"],
                cwd=ROOT / "frontend",
            )
        )
    results.extend(
        [
            trivy_step("trivy-api", args.api_image),
            trivy_step("trivy-web", args.web_image),
        ]
    )

    if args.include_zap:
        zap = run_step("zap-authenticated", [sys.executable, "scripts/zap_scan.py"])
        results.append(zap)

    passed = all(item["status"] == "passed" for item in results)
    summary = {
        "gate": "inventory-only" if args.inventory else "release",
        "passed": passed and not args.inventory,
        "results": results,
        "note": (
            "Inventory mode never constitutes a passed release gate."
            if args.inventory
            else "Missing tools and unbuilt scan images fail closed."
        ),
    }
    write_json(ARTIFACTS / "summary.json", summary)
    for item in results:
        print(f"{item['status'].upper():7} {item['name']}")
        if item["status"] == "missing":
            print(f"        {item['install']}")
    print(f"Evidence: {ARTIFACTS / 'summary.json'}")
    if args.inventory:
        return 0
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
