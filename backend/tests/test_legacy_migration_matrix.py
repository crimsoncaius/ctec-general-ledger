# ruff: noqa: E501
from __future__ import annotations

import io
import uuid
import zipfile

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import (
    Budget,
    Company,
    Currency,
    JournalBatch,
    MigrationRun,
    MigrationStagingRecord,
    ReportDefinition,
    RunStatus,
    User,
)
from app.services import legacy_dbf
from tests.conftest import auth_headers
from tests.test_legacy_migration import (
    ACCOUNT_FIELDS,
    MAIN_FIELDS,
    dbf_bytes,
    migration_company,
)

REPORT_FIELDS = [("NAME", "C", 30, 0), ("SPEC", "C", 120, 0), ("REP", "C", 80, 0)]


def _tables(**overrides: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    values: dict[str, list[dict[str, object]]] = {"GLACCNT": [], "GLMAIN": []}
    values.update(overrides)
    return values


def _stage_direct(monkeypatch: pytest.MonkeyPatch, company_id: str, tables, digest: str):
    monkeypatch.setattr(legacy_dbf, "extract_archive", lambda _: (digest, [], tables))
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "admin@example.com"))
        assert user is not None
        return legacy_dbf.stage_archive(
            db,
            company_id=uuid.UUID(company_id),
            user_id=user.id,
            source_name="synthetic-matrix.zip",
            archive=b"synthetic",
        )


def test_staging_validation_matrix_records_every_legacy_family(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    company_id = migration_company("admin@example.com", "MIGMATRIX")
    accounts = [
        {
            "A_ACC_CODE": "",
            "ACC_TYPE": "Z",
            "CURR": "ZZ",
            "OPEN_BAL": "bad",
            "CURR_BAL": "5",
            "BAL_1": "bad",
        },
        {
            "A_ACC_CODE": "R1",
            "ACC_TYPE": "R",
            "CURR": "SGD",
            "OPEN_BAL": "0",
            "CURR_BAL": "0",
            "BAL_1": "0",
        },
        {
            "A_ACC_CODE": "R2",
            "ACC_TYPE": "R",
            "CURR": "SGD",
            "OPEN_BAL": "0",
            "CURR_BAL": "0",
            "BAL_1": "0",
        },
        {
            "A_ACC_CODE": "1000",
            "ACC_TYPE": "B",
            "CURR": "SGD",
            "OPEN_BAL": "10",
            "CURR_BAL": "11",
            "BAL_1": "0",
        },
    ]
    row = {
        "M_ACC_CODE": "R2",
        "M_PERIOD": "1",
        "M_DATE": "2026-01-20",
        "M_DEBIT": "0",
        "M_CREDIT": "4",
        "M_CURR": "SGD",
        "M_EXRATE": "1",
        "KEY": "MIXED",
        "RECNO": "2",
    }
    posted = [
        {
            "M_ACC_CODE": "9999",
            "M_PERIOD": "bad",
            "M_DATE": None,
            "M_DEBIT": "-1",
            "M_CREDIT": "0",
            "M_CURR": "ZZZ",
            "M_EXRATE": "-1",
            "KEY": "",
            "RECNO": "1",
        },
        {
            "M_ACC_CODE": "R1",
            "M_PERIOD": "1",
            "M_DATE": "2026-01-02",
            "M_DEBIT": "5",
            "M_CREDIT": "0",
            "M_CURR": "SGD",
            "M_EXRATE": "1",
            "KEY": "MIXED",
            "RECNO": "2",
        },
        row,
        dict(row),
    ]
    draft = [
        {
            "T_ACC_CODE": "9999",
            "T_PERIOD": "bad",
            "T_DATE": None,
            "T_DEBIT": "-1",
            "T_CREDIT": "0",
            "T_CURR": "USD",
            "T_EXRATE": "2",
            "KEY": "",
            "GNAME": "BAD",
        },
        {
            "T_ACC_CODE": "R1",
            "T_PERIOD": "1",
            "T_DATE": "2026-01-02",
            "T_DEBIT": "5",
            "T_CREDIT": "0",
            "T_CURR": "SGD",
            "T_EXRATE": "1",
            "KEY": "DG",
            "GNAME": "BAD",
        },
        {
            "T_ACC_CODE": "R2",
            "T_PERIOD": "1",
            "T_DATE": "2026-01-03",
            "T_DEBIT": "0",
            "T_CREDIT": "4",
            "T_CURR": "SGD",
            "T_EXRATE": "1",
            "KEY": "DG",
            "GNAME": "BAD",
        },
    ]
    run = _stage_direct(
        monkeypatch,
        company_id,
        _tables(
            GLACCNT=accounts,
            GLMAIN=posted,
            GLACCNX=[{"A_ACC_CODE": "NOBASE"}],
            GLGP=[{"KEY": "NO-DETAIL"}, {"KEY": "DG"}],
            GLTRANS=draft,
            GLREP=[{"NAME": "Unsafe synthetic", "SPEC": "not recognized", "REP": "{\\rtf1 &Z}"}],
        ),
        "1" * 64,
    )
    assert run.reconciliation["apply_ready"] is False
    assert run.reconciliation["ledger_balanced"] is False
    assert run.reconciliation["blocking_reason"] == "Global posted ledger is unbalanced"
    with SessionLocal() as db:
        rows = db.scalars(
            select(MigrationStagingRecord).where(MigrationStagingRecord.migration_run_id == run.id)
        ).all()
        codes = {issue["code"] for item in rows for issue in item.issues}
    assert {
        "missing_account_code",
        "invalid_account_type",
        "unknown_currency",
        "malformed_number",
        "account_current_mismatch",
        "duplicate_retained_earnings",
        "orphan_transaction",
        "invalid_period",
        "malformed_date",
        "invalid_line_sides",
        "invalid_exchange_rate",
        "missing_group_key",
        "duplicate_record_number",
        "duplicate_transaction",
        "mixed_group_period",
        "unbalanced_group",
        "orphan_currency_mirror",
        "orphan_group_header",
        "orphan_group_detail",
        "orphan_draft_transaction",
        "invalid_draft_period",
        "malformed_draft_date",
        "invalid_draft_line_sides",
        "foreign_draft_manual",
        "mixed_draft_period",
        "unbalanced_draft_group",
        "legacy_report_warning",
        "period_reconciliation_mismatch",
    }.issubset(codes)


def test_stage_guards_missing_company_calendar_and_opening_net(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tables = _tables(GLACCNT=[], GLMAIN=[])
    monkeypatch.setattr(legacy_dbf, "extract_archive", lambda _: ("2" * 64, [], tables))
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "admin@example.com"))
        assert user is not None
        with pytest.raises(HTTPException, match="Company not found"):
            legacy_dbf.stage_archive(
                db, company_id=uuid.uuid4(), user_id=user.id, source_name="none.zip", archive=b"x"
            )
        company = Company(code="MIGNOCAL", name="Synthetic no calendar", base_currency_code="SGD")
        db.add(company)
        db.commit()
        with pytest.raises(HTTPException, match="Configure the target fiscal calendar"):
            legacy_dbf.stage_archive(
                db, company_id=company.id, user_id=user.id, source_name="none.zip", archive=b"x"
            )

    company_id = migration_company("admin@example.com", "MIGOPENNET")
    run = _stage_direct(
        monkeypatch,
        company_id,
        _tables(
            GLACCNT=[
                {
                    "A_ACC_CODE": "1000",
                    "ACC_TYPE": "B",
                    "CURR": "SGD",
                    "OPEN_BAL": "1",
                    "CURR_BAL": "1",
                    "BAL_1": "0",
                }
            ],
            GLMAIN=[],
        ),
        "3" * 64,
    )
    assert run.reconciliation["ledger_balanced"] is True
    assert run.reconciliation["blocking_reason"] == "Global opening balances are unbalanced"


def _opening_fx_report_archive() -> bytes:
    accounts = [
        {
            "A_ACC_CODE": "1000",
            "DESC": "Synthetic cash",
            "ACC_TYPE": "B",
            "OPEN_BAL": 100,
            "CURR_BAL": 150,
            "BAL_1": 50,
            "BUG_1": 25,
            "CURR": "SGD",
        },
        {
            "A_ACC_CODE": "3000",
            "DESC": "Synthetic retained",
            "ACC_TYPE": "R",
            "OPEN_BAL": -100,
            "CURR_BAL": -100,
            "BAL_1": 0,
            "BUG_1": 0,
            "CURR": "SGD",
        },
        {
            "A_ACC_CODE": "4000",
            "DESC": "Synthetic income",
            "ACC_TYPE": "I",
            "OPEN_BAL": 0,
            "CURR_BAL": -50,
            "BAL_1": -50,
            "BUG_1": -25,
            "CURR": "SGD",
        },
    ]
    common = {
        "M_PERIOD": 1,
        "M_DATE": "2026-01-15",
        "M_TRANS_DE": "Synthetic FX sale",
        "M_REF": "FX-1",
        "M_GNAME": "FX",
        "M_EXRATE": 2,
        "KEY": "FX0001",
    }
    posted = [
        {
            **common,
            "M_ACC_CODE": "1000",
            "M_DEBIT": 50,
            "M_CREDIT": 0,
            "M_CURR": "USD",
            "M_DEBITX": 0,
            "M_CREDITX": 0,
            "RECNO": 1,
        },
        {
            **common,
            "M_ACC_CODE": "4000",
            "M_DEBIT": 0,
            "M_CREDIT": 50,
            "M_CURR": "USD",
            "M_DEBITX": 0,
            "M_CREDITX": 0,
            "RECNO": 2,
        },
    ]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("GLACCNT.DAT", dbf_bytes(ACCOUNT_FIELDS, accounts))
        archive.writestr("GLMAIN.DAT", dbf_bytes(MAIN_FIELDS, posted))
        archive.writestr(
            "GLREP.DAT",
            dbf_bytes(
                REPORT_FIELDS,
                [
                    {
                        "NAME": "Synthetic balance",
                        "SPEC": "A: [BP1] [BP2]\n1: [1000,4999]",
                        "REP": "Synthetic",
                    }
                ],
            ),
        )
    return buffer.getvalue()


def test_apply_imports_opening_budget_fx_and_convertible_report(
    client: TestClient,
    admin_token: str,
) -> None:
    company_id = migration_company("admin@example.com", "MIGAPPLYFULL")
    with SessionLocal() as db:
        assert db.get(Currency, "USD") is not None
    headers = auth_headers(admin_token, uuid.UUID(company_id))
    staged = client.post(
        "/api/v1/migration/stage",
        headers=headers,
        files={"archive": ("synthetic-full.zip", _opening_fx_report_archive(), "application/zip")},
    )
    assert staged.status_code == 201, staged.text
    body = staged.json()
    assert body["reconciliation"]["apply_ready"] is True
    applied = client.post(
        f"/api/v1/migration/runs/{body['id']}/apply",
        headers=headers,
        json={"source_digest": body["source_digest"], "confirmation": "APPLY"},
    )
    assert applied.status_code == 200, applied.text
    counts = applied.json()["counts"]
    assert counts["applied_accounts"] == 3
    assert counts["applied_posted_batches"] == 2
    assert counts["applied_reports"] == 1
    with SessionLocal() as db:
        company_uuid = uuid.UUID(company_id)
        assert (
            db.scalar(select(func.count(Budget.id)).where(Budget.company_id == company_uuid)) == 2
        )
        assert (
            db.scalar(
                select(func.count(ReportDefinition.id)).where(
                    ReportDefinition.company_id == company_uuid
                )
            )
            == 1
        )
        assert (
            db.scalar(
                select(func.count(JournalBatch.id)).where(JournalBatch.company_id == company_uuid)
            )
            == 2
        )


def test_apply_rejects_non_dry_or_unsuccessful_source() -> None:
    source = MigrationRun(
        company_id=uuid.uuid4(),
        source_path="synthetic",
        source_digest="4" * 64,
        status=RunStatus.SUCCEEDED,
        dry_run=False,
        requested_by_id=uuid.uuid4(),
        counts={},
        reconciliation={"apply_ready": True},
    )
    with SessionLocal() as db, pytest.raises(HTTPException, match="successful dry run"):
        legacy_dbf.apply_run(db, source, uuid.uuid4())
