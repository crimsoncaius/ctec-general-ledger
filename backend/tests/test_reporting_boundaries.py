from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.services.reporting import ReportData, build_report, export_report
from tests.conftest import auth_headers


def test_every_standard_report_branch_and_filter_is_executable(
    client: TestClient,
    admin_token: str,
    company_ids,
    acme_ledger,
    journal_payload,
) -> None:
    headers = auth_headers(admin_token, company_ids["ACME"])
    period_id = str(acme_ledger["period_id"])
    batch = client.post("/api/v1/journals", headers=headers, json=journal_payload)
    assert batch.status_code == 201, batch.text
    for action in ("validate", "approve", "post"):
        transitioned = client.post(
            f"/api/v1/journals/{batch.json()['id']}/{action}", headers=headers
        )
        assert transitioned.status_code == 200, transitioned.text
    requests = [
        ("chart_of_accounts", {"code_from": "9999", "code_to": "9999"}),
        (
            "trial_balance",
            {"period_id": period_id, "include_zero": False, "include_titles": False},
        ),
        (
            "general_ledger",
            {
                "from_period_id": period_id,
                "to_period_id": period_id,
                "code_from": "1000",
                "code_to": "4000",
            },
        ),
        ("pre_post", {}),
        ("close_history", {}),
        ("integrity", {}),
    ]
    for report_type, parameters in requests:
        response = client.post(
            "/api/v1/reports/run",
            headers=headers,
            json={"report_type": report_type, "parameters": parameters, "format": "json"},
        )
        assert response.status_code == 200, response.text
        assert len(response.json()["digest"]) == 64

    ledger_rows = client.post(
        "/api/v1/reports/run",
        headers=headers,
        json={
            "report_type": "general_ledger",
            "parameters": {"from_period_id": period_id},
            "format": "json",
        },
    ).json()["rows"]
    assert ledger_rows
    ledger = ledger_rows[0]
    assert ledger["account"] >= "1000"


def test_report_identifier_and_export_failures_are_explicit(
    client: TestClient,
    admin_token: str,
    company_ids,
) -> None:
    headers = auth_headers(admin_token, company_ids["ACME"])
    north_period = client.get(
        "/api/v1/fiscal/periods", headers=auth_headers(admin_token, company_ids["NORTH"])
    ).json()[0]
    cases = [
        ("trial_balance", {"period_id": "not-a-uuid"}, 422, "Invalid period identifier"),
        ("trial_balance", {"period_id": north_period["id"]}, 404, "Fiscal period not found"),
        ("transaction_groups", {"batch_id": "bad-batch"}, 422, "Invalid batch identifier"),
        ("unsupported", {}, 422, "Unsupported report type"),
    ]
    for report_type, parameters, status_code, detail in cases:
        response = client.post(
            "/api/v1/reports/run",
            headers=headers,
            json={"report_type": report_type, "parameters": parameters, "format": "json"},
        )
        assert response.status_code == status_code
        assert response.json()["detail"] == detail

    empty = ReportData("Empty", ["value"], [])
    for output_format, signature in (("csv", b"\xef\xbb\xbf"), ("xlsx", b"PK"), ("pdf", b"%PDF")):
        content, media_type, extension = export_report(empty, output_format)
        assert content.startswith(signature)
        assert output_format in media_type or output_format == "xlsx"
        assert extension == output_format
    with pytest.raises(HTTPException, match="Unsupported export format"):
        export_report(empty, "xml")

    with SessionLocal() as db, pytest.raises(HTTPException, match="Unsupported report type"):
        build_report(db, uuid.uuid4(), "not-supported", {})
