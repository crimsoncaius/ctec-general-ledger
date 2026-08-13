from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Account, AccountType, FiscalYear
from tests.conftest import auth_headers


def _create_single_period_year(
    client: TestClient, headers: dict[str, str], label: str, start: date
) -> tuple[str, str]:
    response = client.post(
        "/api/v1/fiscal/years",
        headers=headers,
        json={
            "label": label,
            "start_date": start.isoformat(),
            "end_date": start.isoformat(),
            "periods": [
                {
                    "period_no": 1,
                    "label": f"{label}-P01",
                    "start_date": start.isoformat(),
                    "end_date": start.isoformat(),
                }
            ],
        },
    )
    assert response.status_code == 201, response.text
    year_id = response.json()["id"]
    periods = client.get("/api/v1/fiscal/periods", headers=headers).json()
    period_id = next(item["id"] for item in periods if item["label"] == f"{label}-P01")
    return year_id, period_id


def test_close_context_rejects_missing_periods_bad_opening_and_missing_retained_earnings(
    client: TestClient,
    admin_token: str,
    company_ids,
    acme_ledger,
) -> None:
    company_id = company_ids["ACME"]
    headers = auth_headers(admin_token, company_id)
    with SessionLocal() as db:
        empty_year = FiscalYear(
            company_id=company_id,
            label="NO-PERIODS-2065",
            start_date=date(2065, 1, 1),
            end_date=date(2065, 12, 31),
        )
        db.add(empty_year)
        db.commit()
        empty_year_id = empty_year.id

    no_periods = client.post(
        f"/api/v1/fiscal/years/{empty_year_id}/close-preview",
        headers=headers,
        json={"opening_period_id": str(acme_ledger["period_id"]), "reason": "No periods"},
    )
    assert no_periods.status_code == 409
    assert no_periods.json()["detail"] == "Fiscal year has no periods"

    fiscal_year = client.get("/api/v1/fiscal/years", headers=headers).json()[0]
    fiscal_year_id = fiscal_year["id"]
    bad_opening = client.post(
        f"/api/v1/fiscal/years/{fiscal_year_id}/close-preview",
        headers=headers,
        json={"opening_period_id": str(acme_ledger["period_id"]), "reason": "Bad opening"},
    )
    assert bad_opening.status_code == 422
    valid_opening_id = next(
        period["id"]
        for period in client.get("/api/v1/fiscal/periods", headers=headers).json()
        if period["start_date"] > fiscal_year["end_date"]
    )

    try:
        with SessionLocal() as db:
            retained = db.scalar(
                select(Account).where(
                    Account.company_id == company_id,
                    Account.account_type == AccountType.RETAINED_EARNINGS,
                )
            )
            assert retained is not None
            retained.active = False
            db.commit()
        missing_retained = client.post(
            f"/api/v1/fiscal/years/{fiscal_year_id}/close-preview",
            headers=headers,
            json={"opening_period_id": valid_opening_id, "reason": "No retained"},
        )
        assert missing_retained.status_code == 409
        assert (
            missing_retained.json()["detail"] == "One active retained-earnings account is required"
        )
    finally:
        with SessionLocal() as db:
            retained = db.scalar(
                select(Account).where(
                    Account.company_id == company_id,
                    Account.account_type == AccountType.RETAINED_EARNINGS,
                )
            )
            assert retained is not None
            retained.active = True
            db.commit()


def test_empty_year_close_and_compensation_failure_boundaries(
    client: TestClient,
    admin_token: str,
    company_ids,
) -> None:
    company_id = company_ids["ACME"]
    headers = auth_headers(admin_token, company_id)
    year_id, closing_period_id = _create_single_period_year(
        client, headers, "EMPTY-CLOSE-2070", date(2070, 1, 1)
    )
    _opening_year_id, opening_period_id = _create_single_period_year(
        client, headers, "EMPTY-OPEN-2071", date(2071, 1, 1)
    )

    result = client.post(
        f"/api/v1/fiscal/years/{year_id}/close",
        headers=headers,
        json={"opening_period_id": opening_period_id, "reason": "Close empty control year"},
    )
    assert result.status_code == 200, result.text
    assert result.json()["batch_id"] is None
    assert result.json()["closing_entry_id"] is None
    assert result.json()["opening_entry_id"] is None

    no_effects = client.post(
        f"/api/v1/fiscal/years/{year_id}/compensate-close",
        headers=headers,
        json={
            "fiscal_period_id": opening_period_id,
            "posting_date": "2071-01-01",
            "reason": "Nothing to compensate",
        },
    )
    assert no_effects.status_code == 409
    assert no_effects.json()["detail"] == "Close event has no ledger effects to compensate"

    missing = client.post(
        "/api/v1/fiscal/years/00000000-0000-0000-0000-000000000001/compensate-close",
        headers=headers,
        json={
            "fiscal_period_id": opening_period_id,
            "posting_date": "2071-01-01",
            "reason": "Missing close event",
        },
    )
    assert missing.status_code == 404

    invalid_period = client.post(
        f"/api/v1/fiscal/years/{year_id}/compensate-close",
        headers=headers,
        json={
            "fiscal_period_id": closing_period_id,
            "posting_date": "2070-01-01",
            "reason": "Closed period is invalid",
        },
    )
    assert invalid_period.status_code == 422


def test_preclosed_year_without_close_event_is_rejected(
    client: TestClient,
    admin_token: str,
    company_ids,
) -> None:
    headers = auth_headers(admin_token, company_ids["ACME"])
    year_id, _period_id = _create_single_period_year(
        client, headers, "PRECLOSED-2080", date(2080, 1, 1)
    )
    _opening_year_id, opening_period_id = _create_single_period_year(
        client, headers, "PRECLOSED-2081", date(2081, 1, 1)
    )
    with SessionLocal() as db:
        fiscal_year = db.get(FiscalYear, year_id)
        assert fiscal_year is not None
        fiscal_year.closed_at = datetime.now(UTC)
        db.commit()

    response = client.post(
        f"/api/v1/fiscal/years/{year_id}/close",
        headers=headers,
        json={"opening_period_id": opening_period_id, "reason": "Already closed"},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Fiscal year is already closed"
