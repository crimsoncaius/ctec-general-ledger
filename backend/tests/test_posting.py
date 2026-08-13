from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.exc import DBAPIError

from app.db import SessionLocal
from app.main import app
from app.models import Account, JournalBatch, JournalEntry, PeriodBalance, PostingEvent
from tests.conftest import auth_headers


def test_balanced_batch_workflow_posts_and_is_immutable(
    client: TestClient,
    admin_token: str,
    approver_token: str,
    company_ids,
    journal_payload,
) -> None:
    company_id = company_ids["ACME"]
    created = client.post(
        "/api/v1/journals",
        headers=auth_headers(admin_token, company_id),
        json=journal_payload,
    )
    assert created.status_code == 201, created.text
    batch_id = created.json()["id"]

    validated = client.post(
        f"/api/v1/journals/{batch_id}/validate",
        headers=auth_headers(admin_token, company_id),
    )
    assert validated.status_code == 200
    approved = client.post(
        f"/api/v1/journals/{batch_id}/approve",
        headers=auth_headers(approver_token, company_id),
    )
    assert approved.status_code == 200
    posted = client.post(
        f"/api/v1/journals/{batch_id}/post",
        headers=auth_headers(approver_token, company_id),
    )
    assert posted.status_code == 200, posted.text
    assert posted.json()["status"] == "posted"
    entry_id = posted.json()["entries"][0]["id"]

    with SessionLocal() as db:
        batch = db.get(JournalBatch, batch_id)
        assert batch is not None
        entry = batch.entries[0]
        events = db.scalars(select(PostingEvent).where(PostingEvent.entry_id == entry.id)).all()
        balances = db.scalars(
            select(PeriodBalance).where(PeriodBalance.company_id == company_id)
        ).all()
        assert len(events) == 1
        assert sum((row.debit_base for row in balances), Decimal("0")) >= Decimal("125.55")
        assert sum((row.credit_base for row in balances), Decimal("0")) >= Decimal("125.55")
        with pytest.raises(DBAPIError):
            db.execute(
                update(JournalEntry)
                .where(JournalEntry.id == entry.id)
                .values(description="Forbidden rewrite")
            )
            db.commit()
        db.rollback()

    reversal = client.post(
        f"/api/v1/journals/entries/{entry_id}/reverse",
        headers=auth_headers(approver_token, company_id),
        json={
            "posting_date": journal_payload["entries"][0]["posting_date"],
            "fiscal_period_id": journal_payload["entries"][0]["fiscal_period_id"],
            "reason": "Customer sale cancelled",
        },
    )
    assert reversal.status_code == 201, reversal.text
    assert reversal.json()["status"] == "posted"
    assert reversal.json()["entries"][0]["reversal_of_id"] == entry_id

    duplicate = client.post(
        f"/api/v1/journals/entries/{entry_id}/reverse",
        headers=auth_headers(approver_token, company_id),
        json={
            "posting_date": journal_payload["entries"][0]["posting_date"],
            "fiscal_period_id": journal_payload["entries"][0]["fiscal_period_id"],
            "reason": "Duplicate should fail",
        },
    )
    assert duplicate.status_code == 409

    integrity = client.post(
        "/api/v1/ledger/integrity", headers=auth_headers(approver_token, company_id)
    )
    assert integrity.status_code == 200
    assert integrity.json()["ok"] is True


def test_invalid_account_at_post_rolls_back_all_mutations(
    client: TestClient,
    admin_token: str,
    approver_token: str,
    company_ids,
    journal_payload,
) -> None:
    company_id = company_ids["ACME"]
    created = client.post(
        "/api/v1/journals",
        headers=auth_headers(admin_token, company_id),
        json=journal_payload,
    )
    batch_id = created.json()["id"]
    client.post(
        f"/api/v1/journals/{batch_id}/validate",
        headers=auth_headers(admin_token, company_id),
    )
    client.post(
        f"/api/v1/journals/{batch_id}/approve",
        headers=auth_headers(approver_token, company_id),
    )

    with SessionLocal() as db:
        revenue = db.scalar(
            select(Account).where(Account.company_id == company_id, Account.code == "4000")
        )
        assert revenue is not None
        revenue.active = False
        before_balances = db.query(PeriodBalance).filter_by(company_id=company_id).count()
        db.commit()

    response = client.post(
        f"/api/v1/journals/{batch_id}/post",
        headers=auth_headers(approver_token, company_id),
    )
    assert response.status_code == 422

    with SessionLocal() as db:
        batch = db.get(JournalBatch, batch_id)
        assert batch is not None
        assert batch.status.value == "approved"
        assert (
            db.query(PostingEvent)
            .join(JournalEntry)
            .filter(JournalEntry.batch_id == batch.id)
            .count()
            == 0
        )
        assert db.query(PeriodBalance).filter_by(company_id=company_id).count() == before_balances
        revenue = db.scalar(
            select(Account).where(Account.company_id == company_id, Account.code == "4000")
        )
        assert revenue is not None
        revenue.active = True
        db.commit()


def test_unbalanced_payload_is_rejected_without_batch(
    client: TestClient,
    admin_token: str,
    company_ids,
    journal_payload,
) -> None:
    company_id = company_ids["ACME"]
    journal_payload["entries"][0]["lines"][1]["credit"] = "124.00"
    with SessionLocal() as db:
        before = db.query(JournalBatch).filter_by(company_id=company_id).count()
    response = client.post(
        "/api/v1/journals",
        headers=auth_headers(admin_token, company_id),
        json=journal_payload,
    )
    assert response.status_code == 422
    with SessionLocal() as db:
        assert db.query(JournalBatch).filter_by(company_id=company_id).count() == before


def test_concurrent_post_requests_create_exactly_one_posting_event(
    client: TestClient,
    admin_token: str,
    company_ids,
    journal_payload,
) -> None:
    company_id = company_ids["ACME"]
    headers = auth_headers(admin_token, company_id)
    created = client.post("/api/v1/journals", headers=headers, json=journal_payload)
    assert created.status_code == 201, created.text
    batch_id = created.json()["id"]
    assert client.post(f"/api/v1/journals/{batch_id}/validate", headers=headers).status_code == 200
    assert client.post(f"/api/v1/journals/{batch_id}/approve", headers=headers).status_code == 200

    def post_once() -> int:
        with TestClient(app) as concurrent_client:
            return concurrent_client.post(
                f"/api/v1/journals/{batch_id}/post", headers=headers
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = sorted(executor.map(lambda _index: post_once(), range(2)))
    assert statuses == [200, 409]

    with SessionLocal() as db:
        batch = db.get(JournalBatch, batch_id)
        assert batch is not None and batch.status.value == "posted"
        entry_ids = [entry.id for entry in batch.entries]
        events = db.scalars(select(PostingEvent).where(PostingEvent.entry_id.in_(entry_ids))).all()
        assert len(events) == len(entry_ids) == 1
