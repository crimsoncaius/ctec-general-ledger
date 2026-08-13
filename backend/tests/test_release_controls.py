# ruff: noqa: E501, I001
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from app.services.legacy_dbf import extract_archive

import scripts.release_evidence as release_evidence
import scripts.test as portable_test
from scripts.generate_legacy_fixtures import PROFILE_FILE, build_profile, generate
from scripts.release_evidence import APPROVALS, EVIDENCE, build_manifest, validate
from scripts.release_rehearsal import (
    ACKNOWLEDGEMENT,
    checksum,
    database_target,
    require_distinct,
    require_isolated_target,
    self_check,
)


def test_synthetic_fixture_profiles_are_deterministic_and_controlled(tmp_path: Path) -> None:
    profiles = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))["profiles"]
    assert set(profiles) == {"small", "medium", "corrupt", "boundary"}
    first = generate(tmp_path, write=True)
    second = generate(tmp_path, write=False)
    assert first == second
    for name, controls in first["fixtures"].items():
        archive = tmp_path / f"{name}.zip"
        assert archive.is_file()
        assert controls["archive_sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()
        assert (
            json.loads((tmp_path / f"{name}.controls.json").read_text())["source_kind"]
            == "synthetic"
        )
        _, _, tables = extract_archive(archive.read_bytes())
        assert len(tables["GLACCNT"]) == controls["counts"]["accounts"]
        assert len(tables["GLMAIN"]) == controls["counts"]["posted_lines"]
    assert (
        first["fixtures"]["small"]["totals"]["ledger_debits"]
        == first["fixtures"]["small"]["totals"]["ledger_credits"]
    )
    assert first["fixtures"]["medium"]["counts"]["posted_lines"] == 500
    assert first["fixtures"]["boundary"]["periods"] == 18
    assert first["fixtures"]["corrupt"]["expected_status"] == "blocked"


def test_generated_archive_and_controls_change_together() -> None:
    profile = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))["profiles"]["small"]
    first_archive, first_controls = build_profile("small", profile)
    second_archive, second_controls = build_profile("small", profile)
    assert first_archive == second_archive
    assert first_controls == second_controls
    changed_archive, changed_controls = build_profile("small", {**profile, "posted_groups": 2})
    assert changed_archive != first_archive
    assert changed_controls["archive_sha256"] != first_controls["archive_sha256"]


def test_release_rehearsal_rejects_live_or_same_targets(tmp_path: Path) -> None:
    live = database_target("postgresql+psycopg://ctec:secret@localhost:15432/ctec_gl")
    isolated = database_target(
        "postgresql+psycopg://ctec:secret@localhost:15432/ctec_gl_restore_20260810"
    )
    require_isolated_target(isolated)
    with pytest.raises(ValueError, match="Refusing target database"):
        require_isolated_target(live)
    with pytest.raises(ValueError, match="different databases"):
        require_distinct(isolated, isolated)
    require_distinct(live, isolated)
    assert "secret" not in isolated.redacted()
    assert self_check()["live_name_rejected"] is True
    assert self_check()["acknowledgement"] == ACKNOWLEDGEMENT
    payload = tmp_path / "backup.dump"
    payload.write_bytes(b"synthetic backup bytes")
    assert checksum(payload) == hashlib.sha256(payload.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    "url", ["sqlite:///ctec_gl_restore_x", "postgresql://localhost", "not a url"]
)
def test_release_rehearsal_requires_named_postgresql_database(url: str) -> None:
    with pytest.raises(ValueError):
        database_target(url)


def test_evidence_manifest_is_truthful_and_blocked_until_external_gates() -> None:
    manifest = build_manifest()
    assert set(manifest["approvals"]) == set(APPROVALS)
    assert all(value["status"] == "pending" for value in manifest["approvals"].values())
    assert manifest["claims"] == {
        "long_running_performance_completed": False,
        "external_security_review_completed": False,
        "human_uat_approved": False,
    }
    failures = validate(manifest)
    assert "release decision is not approved" in failures
    assert all(any(role in item for item in failures) for role in APPROVALS)


def test_evidence_manifest_uses_stage6_output_contracts_and_reports_missing_git(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert EVIDENCE["performance"] == "artifacts/performance/load-release.json"
    assert EVIDENCE["resilience"] == "artifacts/resilience/summary.json"
    monkeypatch.setattr(release_evidence, "git_value", lambda *args: "unavailable")
    manifest = release_evidence.build_manifest()
    assert manifest["release_candidate"]["git_commit"] == "unavailable"
    assert manifest["release_candidate"]["git_status"] == "unavailable"


def test_portable_backend_coverage_paths_match_evidence_contract() -> None:
    command = portable_test.COMMANDS["backend"]
    assert "--cov-report=html:artifacts/coverage/backend-html" in command
    assert "--cov-report=xml:artifacts/coverage/backend.xml" in command
    assert EVIDENCE["coverage"] == "artifacts/coverage/backend.xml"


def test_completed_evidence_manifest_can_be_validated_without_weakening_gate() -> None:
    manifest = {
        "evidence": {"one": {"status": "present-reviewed"}},
        "approvals": {role: {"status": "approved"} for role in APPROVALS},
        "release_decision": {"status": "approved"},
    }
    assert validate(manifest) == []
