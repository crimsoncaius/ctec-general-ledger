from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.models import (
    Account,
    ClosingEvent,
    Company,
    FiscalPeriod,
    FiscalYear,
    JournalEntry,
    PeriodStatus,
)
from tests.conftest import auth_headers


def test_budget_history_and_non_destructive_reconciled_close(
    client: TestClient,
    admin_token: str,
    company_ids,
) -> None:
    company_id = company_ids["NORTH"]
    headers = auth_headers(admin_token, company_id)
    with SessionLocal() as db:
        company = db.scalar(select(Company).where(Company.id == company_id))
        fiscal_year = db.scalar(
            select(FiscalYear).where(
                FiscalYear.company_id == company_id, FiscalYear.label == "FY2026"
            )
        )
        period = db.scalar(
            select(FiscalPeriod).where(
                FiscalPeriod.company_id == company_id,
                FiscalPeriod.fiscal_year_id == fiscal_year.id,
                FiscalPeriod.period_no == 1,
            )
        )
        accounts = {
            account.code: account.id
            for account in db.scalars(select(Account).where(Account.company_id == company_id)).all()
        }
        assert company is not None and fiscal_year is not None and period is not None

    budget = client.put(
        "/api/v1/budgets",
        headers=headers,
        json={
            "fiscal_period_id": str(period.id),
            "account_id": str(accounts["4000"]),
            "scenario": "Approved FY2026",
            "currency_code": "USD",
            "amount": "120000.00",
        },
    )
    assert budget.status_code == 200, budget.text
    assert Decimal(budget.json()["amount"]) == Decimal("120000.000000")

    periods = client.get("/api/v1/fiscal/periods", headers=headers).json()
    opening_period = next(
        item for item in periods if item["start_date"] > fiscal_year.end_date.isoformat()
    )

    journal = {
        "description": "Northstar close-cycle revenue",
        "entries": [
            {
                "entry_date": period.start_date.isoformat(),
                "posting_date": period.start_date.isoformat(),
                "fiscal_period_id": str(period.id),
                "reference": "CLOSE-TEST",
                "description": "Revenue before year end",
                "lines": [
                    {
                        "account_id": str(accounts["1000"]),
                        "currency_code": "USD",
                        "debit": "2500.00",
                        "credit": "0",
                    },
                    {
                        "account_id": str(accounts["4000"]),
                        "currency_code": "USD",
                        "debit": "0",
                        "credit": "2500.00",
                    },
                ],
            }
        ],
    }
    created = client.post("/api/v1/journals", headers=headers, json=journal)
    batch_id = created.json()["id"]
    assert client.post(f"/api/v1/journals/{batch_id}/validate", headers=headers).status_code == 200
    assert client.post(f"/api/v1/journals/{batch_id}/approve", headers=headers).status_code == 200
    assert client.post(f"/api/v1/journals/{batch_id}/post", headers=headers).status_code == 200

    close_payload = {
        "opening_period_id": opening_period["id"],
        "reason": "Board-approved year end",
    }
    preview = client.post(
        f"/api/v1/fiscal/years/{fiscal_year.id}/close-preview",
        headers=headers,
        json=close_payload,
    )
    assert preview.status_code == 200, preview.text
    assert Decimal(preview.json()["profit_loss"]) == Decimal("-2500.000000")
    assert preview.json()["balanced"] is True

    result = client.post(
        f"/api/v1/fiscal/years/{fiscal_year.id}/close", headers=headers, json=close_payload
    )
    assert result.status_code == 200, result.text
    assert result.json()["closing_entry_id"]
    assert result.json()["opening_entry_id"]

    with SessionLocal() as db:
        close_event = db.scalar(
            select(ClosingEvent).where(
                ClosingEvent.company_id == company_id,
                ClosingEvent.fiscal_year_id == fiscal_year.id,
            )
        )
        assert close_event is not None
        assert close_event.reconciliation["balanced"] is True
        old_periods = db.scalars(
            select(FiscalPeriod).where(FiscalPeriod.fiscal_year_id == fiscal_year.id)
        ).all()
        assert all(item.status == PeriodStatus.CLOSED for item in old_periods)
        original = db.scalar(select(JournalEntry).where(JournalEntry.reference == "CLOSE-TEST"))
        assert original is not None and original.status.value == "posted"

    integrity = client.post("/api/v1/ledger/integrity", headers=headers)
    assert integrity.status_code == 200
    assert integrity.json()["ok"] is True
    assert (
        client.post(
            f"/api/v1/fiscal/years/{fiscal_year.id}/close", headers=headers, json=close_payload
        ).status_code
        == 409
    )

    compensation = client.post(
        f"/api/v1/fiscal/years/{fiscal_year.id}/compensate-close",
        headers=headers,
        json={
            "fiscal_period_id": opening_period["id"],
            "posting_date": opening_period["start_date"],
            "reason": "Approved compensating correction",
        },
    )
    assert compensation.status_code == 200, compensation.text
    assert compensation.json()["status"] == "posted"
    with SessionLocal() as db:
        close_event = db.scalar(
            select(ClosingEvent).where(ClosingEvent.fiscal_year_id == fiscal_year.id)
        )
        assert close_event is not None and close_event.reversed_by_entry_id is not None
        old_periods = db.scalars(
            select(FiscalPeriod).where(FiscalPeriod.fiscal_year_id == fiscal_year.id)
        ).all()
        assert all(item.status == PeriodStatus.CLOSED for item in old_periods)
    repeated_compensation = client.post(
        f"/api/v1/fiscal/years/{fiscal_year.id}/compensate-close",
        headers=headers,
        json={
            "fiscal_period_id": opening_period["id"],
            "posting_date": opening_period["start_date"],
            "reason": "Duplicate compensation must fail",
        },
    )
    assert repeated_compensation.status_code == 409
    assert client.post("/api/v1/ledger/integrity", headers=headers).json()["ok"] is True
