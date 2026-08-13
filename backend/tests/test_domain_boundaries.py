from __future__ import annotations

import copy
import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.models import FiscalPeriod, FiscalYear, JournalBatch, PeriodStatus, Role
from tests.conftest import auth_headers, login


def _periods(start: date, count: int) -> list[dict[str, object]]:
    return [
        {
            "period_no": index + 1,
            "label": f"P{index + 1:02d}",
            "start_date": (start + timedelta(days=index)).isoformat(),
            "end_date": (start + timedelta(days=index)).isoformat(),
        }
        for index in range(count)
    ]


def test_fiscal_calendar_accepts_one_and_eighteen_period_boundaries_and_rejects_bad_ranges(
    client: TestClient,
    admin_token: str,
    company_ids,
) -> None:
    headers = auth_headers(admin_token, company_ids["ACME"])
    for year, count in ((2040, 1), (2041, 18)):
        start = date(year, 1, 1)
        created = client.post(
            "/api/v1/fiscal/years",
            headers=headers,
            json={
                "label": f"BOUNDARY-{year}",
                "start_date": start.isoformat(),
                "end_date": (start + timedelta(days=count - 1)).isoformat(),
                "periods": _periods(start, count),
            },
        )
        assert created.status_code == 201, created.text
        assert created.json()["period_count"] == count

    invalid_payloads = [
        {
            "label": "NON-CONTIGUOUS-NUMBERS",
            "start_date": "2042-01-01",
            "end_date": "2042-01-03",
            "periods": [
                {
                    "period_no": 1,
                    "label": "P01",
                    "start_date": "2042-01-01",
                    "end_date": "2042-01-01",
                },
                {
                    "period_no": 3,
                    "label": "P03",
                    "start_date": "2042-01-02",
                    "end_date": "2042-01-03",
                },
            ],
        },
        {
            "label": "OVERLAPPING-PERIODS",
            "start_date": "2043-01-01",
            "end_date": "2043-01-31",
            "periods": [
                {
                    "period_no": 1,
                    "label": "P01",
                    "start_date": "2043-01-01",
                    "end_date": "2043-01-20",
                },
                {
                    "period_no": 2,
                    "label": "P02",
                    "start_date": "2043-01-20",
                    "end_date": "2043-01-31",
                },
            ],
        },
    ]
    for payload in invalid_payloads:
        assert client.post("/api/v1/fiscal/years", headers=headers, json=payload).status_code == 422


def test_title_accounts_and_cross_company_foreign_identifiers_are_rejected(
    client: TestClient,
    admin_token: str,
    company_ids,
    journal_payload,
) -> None:
    acme_headers = auth_headers(admin_token, company_ids["ACME"])
    title = client.post(
        "/api/v1/accounts",
        headers=acme_headers,
        json={
            "code": "TITLE-BOUNDARY",
            "name": "Invalid postable title",
            "account_type": "title",
            "currency_code": "SGD",
            "postable": True,
        },
    )
    assert title.status_code == 422

    north_accounts = client.get(
        "/api/v1/accounts", headers=auth_headers(admin_token, company_ids["NORTH"])
    ).json()
    foreign_account = copy.deepcopy(journal_payload)
    foreign_account["entries"][0]["lines"][0]["account_id"] = north_accounts[0]["id"]

    with SessionLocal() as db:
        before = db.query(JournalBatch).filter_by(company_id=company_ids["ACME"]).count()
    rejected = client.post("/api/v1/journals", headers=acme_headers, json=foreign_account)
    assert rejected.status_code == 422
    with SessionLocal() as db:
        assert db.query(JournalBatch).filter_by(company_id=company_ids["ACME"]).count() == before

    north_period = client.get(
        "/api/v1/fiscal/periods", headers=auth_headers(admin_token, company_ids["NORTH"])
    ).json()[0]
    foreign_period = copy.deepcopy(journal_payload)
    foreign_period["entries"][0]["fiscal_period_id"] = north_period["id"]
    rejected_period = client.post("/api/v1/journals", headers=acme_headers, json=foreign_period)
    assert rejected_period.status_code == 422

    budget = client.put(
        "/api/v1/budgets",
        headers=acme_headers,
        json={
            "fiscal_period_id": str(journal_payload["entries"][0]["fiscal_period_id"]),
            "account_id": north_accounts[0]["id"],
            "scenario": "Cross-tenant attempt",
            "currency_code": "SGD",
            "amount": "10.00",
        },
    )
    assert budget.status_code == 422


@pytest.mark.parametrize(
    ("line_patch", "expected_detail"),
    [
        ({"debit": "0", "credit": "0"}, "Exactly one of debit or credit must be positive"),
        ({"debit": "-1", "credit": "0"}, None),
        ({"debit": "1.0000001", "credit": "0"}, None),
        ({"debit": "1", "credit": "1"}, "Exactly one of debit or credit must be positive"),
    ],
)
def test_journal_numeric_boundaries_are_rejected_before_persistence(
    client: TestClient,
    admin_token: str,
    company_ids,
    journal_payload,
    line_patch: dict[str, str],
    expected_detail: str | None,
) -> None:
    payload = copy.deepcopy(journal_payload)
    payload["entries"][0]["lines"][0].update(line_patch)
    with SessionLocal() as db:
        before = db.query(JournalBatch).filter_by(company_id=company_ids["ACME"]).count()

    response = client.post(
        "/api/v1/journals",
        headers=auth_headers(admin_token, company_ids["ACME"]),
        json=payload,
    )
    assert response.status_code == 422
    if expected_detail is not None:
        assert expected_detail in response.text
    with SessionLocal() as db:
        assert db.query(JournalBatch).filter_by(company_id=company_ids["ACME"]).count() == before


def test_posting_date_and_closed_period_guards_do_not_leave_batches(
    client: TestClient,
    admin_token: str,
    company_ids,
    acme_ledger,
    journal_payload,
) -> None:
    headers = auth_headers(admin_token, company_ids["ACME"])
    wrong_date = copy.deepcopy(journal_payload)
    wrong_date["entries"][0]["posting_date"] = "1999-01-01"
    assert client.post("/api/v1/journals", headers=headers, json=wrong_date).status_code == 422

    period_id = acme_ledger["period_id"]
    try:
        with SessionLocal() as db:
            period = db.get(FiscalPeriod, period_id)
            assert period is not None
            period.status = PeriodStatus.CLOSED
            db.commit()
        closed = client.post("/api/v1/journals", headers=headers, json=journal_payload)
        assert closed.status_code == 409
        assert closed.json()["detail"] == "Fiscal period is not open"
    finally:
        with SessionLocal() as db:
            period = db.get(FiscalPeriod, period_id)
            assert period is not None
            period.status = PeriodStatus.OPEN
            db.commit()


def test_maker_checker_and_duplicate_transition_rules(
    client: TestClient,
    admin_token: str,
    company_ids,
    journal_payload,
) -> None:
    headers = auth_headers(admin_token, company_ids["ACME"])
    suffix = uuid.uuid4().hex[:10]
    role = client.post(
        "/api/v1/administration/roles",
        headers=headers,
        json={
            "name": f"Maker checker {suffix}",
            "permissions": [
                "journals.create",
                "journals.validate",
                "journals.approve",
                "journals.view",
            ],
        },
    )
    assert role.status_code == 201, role.text
    email = f"maker-{suffix}@example.com"
    user = client.post(
        "/api/v1/administration/users",
        headers=headers,
        json={
            "email": email,
            "display_name": "Maker Checker Boundary",
            "password": "Maker-Checker-2026!",
            "role_id": role.json()["id"],
        },
    )
    assert user.status_code == 201, user.text
    maker_token = login(client, email, "Maker-Checker-2026!")
    maker_headers = auth_headers(maker_token, company_ids["ACME"])

    created = client.post("/api/v1/journals", headers=maker_headers, json=journal_payload)
    assert created.status_code == 201, created.text
    batch_id = created.json()["id"]
    validated = client.post(f"/api/v1/journals/{batch_id}/validate", headers=maker_headers)
    assert validated.status_code == 200

    self_approval = client.post(f"/api/v1/journals/{batch_id}/approve", headers=maker_headers)
    assert self_approval.status_code == 409
    assert "another user" in self_approval.json()["detail"]

    duplicate_validation = client.post(
        f"/api/v1/journals/{batch_id}/validate", headers=maker_headers
    )
    assert duplicate_validation.status_code == 409


def test_bulk_transition_reports_partial_failure_without_rolling_back_success(
    client: TestClient,
    admin_token: str,
    company_ids,
    journal_payload,
) -> None:
    headers = auth_headers(admin_token, company_ids["ACME"])
    created = client.post("/api/v1/journals", headers=headers, json=journal_payload)
    assert created.status_code == 201
    batch_id = created.json()["id"]
    missing_id = str(uuid.uuid4())

    result = client.post(
        "/api/v1/journals/bulk",
        headers=headers,
        json={"batch_ids": [batch_id, missing_id], "action": "validate"},
    )
    assert result.status_code == 200, result.text
    assert result.json()["succeeded"] == [batch_id]
    assert result.json()["failed"] == [
        {"batch_id": missing_id, "status": 404, "detail": "Journal batch not found"}
    ]
    saved = client.get(f"/api/v1/journals/{batch_id}", headers=headers)
    assert saved.json()["status"] == "validated"


def test_cross_company_role_and_report_run_identifiers_are_not_visible(
    client: TestClient,
    admin_token: str,
    company_ids,
    acme_ledger,
) -> None:
    acme_headers = auth_headers(admin_token, company_ids["ACME"])
    north_headers = auth_headers(admin_token, company_ids["NORTH"])
    north_role = client.get("/api/v1/administration/roles", headers=north_headers).json()[0]
    assert (
        client.get(
            f"/api/v1/administration/roles/{north_role['id']}/permissions",
            headers=acme_headers,
        ).status_code
        == 404
    )

    report = client.post(
        "/api/v1/reports/run",
        headers=north_headers,
        json={"report_type": "chart_of_accounts", "parameters": {}, "format": "json"},
    )
    assert report.status_code == 200, report.text
    assert (
        client.post(
            f"/api/v1/reports/runs/{report.json()['run_id']}/reproduce",
            headers=acme_headers,
        ).status_code
        == 404
    )

    with SessionLocal() as db:
        fiscal_year = db.scalar(
            select(FiscalYear).where(
                FiscalYear.company_id == company_ids["NORTH"], FiscalYear.label == "FY2027"
            )
        )
        assert fiscal_year is not None
    close = client.post(
        f"/api/v1/fiscal/years/{fiscal_year.id}/close-preview",
        headers=acme_headers,
        json={
            "opening_period_id": str(acme_ledger["period_id"]),
            "reason": "Cross-tenant close attempt",
        },
    )
    assert close.status_code == 404


def test_cross_company_membership_cannot_use_a_foreign_role(
    client: TestClient,
    admin_token: str,
    company_ids,
) -> None:
    north_headers = auth_headers(admin_token, company_ids["NORTH"])
    acme_headers = auth_headers(admin_token, company_ids["ACME"])
    with SessionLocal() as db:
        north_role = db.scalar(
            select(Role).where(Role.company_id == company_ids["NORTH"], Role.name == "Approver")
        )
        assert north_role is not None
    response = client.post(
        "/api/v1/administration/users",
        headers=acme_headers,
        json={
            "email": f"foreign-role-{uuid.uuid4().hex[:10]}@example.com",
            "display_name": "Foreign Role Attempt",
            "password": "Foreign-Role-2026!",
            "role_id": str(north_role.id),
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Role must belong to this company"
    assert client.get("/api/v1/administration/users", headers=north_headers).status_code == 200
