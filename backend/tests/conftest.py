from __future__ import annotations

import os
import uuid
from collections.abc import Generator

import psycopg
import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy.engine import make_url

from alembic import command

DEFAULT_TEST_DATABASE = f"ctec_gl_test_{os.getpid()}"
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    f"postgresql+psycopg://ctec:ctec_local_only@localhost:15432/{DEFAULT_TEST_DATABASE}",
)
test_database_url = make_url(TEST_DATABASE_URL)
TEST_DATABASE = test_database_url.database or ""
if not TEST_DATABASE.startswith(("ctec_gl_test_", "ctec_gl_e2e")):
    raise RuntimeError(
        "Refusing to run tests against a database that is not prefixed with "
        "ctec_gl_test_ or ctec_gl_e2e"
    )
ADMIN_DSN = os.getenv(
    "TEST_DATABASE_ADMIN_URL",
    test_database_url.set(drivername="postgresql", database="postgres").render_as_string(
        hide_password=False
    ),
)

with psycopg.connect(ADMIN_DSN, autocommit=True) as connection:
    connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(TEST_DATABASE)))

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["JWT_SECRET"] = "test-only-secret-that-is-longer-than-thirty-two-characters"

from app.db import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Account, Company, FiscalPeriod, FiscalYear, User  # noqa: E402
from app.test_seed import seed  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Generator[None, None, None]:
    config = Config("backend/alembic.ini")
    command.upgrade(config, "head")
    seed()
    yield
    engine.dispose()
    with psycopg.connect(ADMIN_DSN, autocommit=True) as connection:
        connection.execute(
            sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(TEST_DATABASE))
        )


@pytest.fixture
def client(migrated_database: None) -> TestClient:
    return TestClient(app)


def login(client: TestClient, email: str, password: str) -> str:
    response = client.post("/api/v1/auth/token", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture
def admin_token(client: TestClient) -> str:
    return login(client, "admin@example.com", "CTec-Demo-Admin-2026!")


@pytest.fixture
def preparer_token(client: TestClient) -> str:
    return login(client, "preparer@example.com", "CTec-Demo-Prepare-2026!")


@pytest.fixture
def approver_token(client: TestClient) -> str:
    return login(client, "approver@example.com", "CTec-Demo-Approve-2026!")


@pytest.fixture
def company_ids(migrated_database: None) -> dict[str, uuid.UUID]:
    with SessionLocal() as db:
        return {company.code: company.id for company in db.query(Company).all()}


@pytest.fixture
def acme_ledger(migrated_database: None) -> dict[str, object]:
    with SessionLocal() as db:
        company = db.query(Company).filter_by(code="ACME").one()
        period = (
            db.query(FiscalPeriod)
            .join(FiscalYear, FiscalYear.id == FiscalPeriod.fiscal_year_id)
            .filter(
                FiscalPeriod.company_id == company.id,
                FiscalPeriod.period_no == 1,
                FiscalYear.label == "FY2026",
            )
            .one()
        )
        accounts = {
            account.code: account.id
            for account in db.query(Account).filter_by(company_id=company.id).all()
        }
        users = {user.email: user.id for user in db.query(User).all()}
        return {
            "company_id": company.id,
            "period_id": period.id,
            "period_start": period.start_date.isoformat(),
            "accounts": accounts,
            "users": users,
        }


def auth_headers(token: str, company_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Company-ID": str(company_id)}


@pytest.fixture
def journal_payload(acme_ledger: dict[str, object]) -> dict[str, object]:
    accounts = acme_ledger["accounts"]
    assert isinstance(accounts, dict)
    return {
        "description": "Test cash sale",
        "entries": [
            {
                "entry_date": acme_ledger["period_start"],
                "posting_date": acme_ledger["period_start"],
                "fiscal_period_id": str(acme_ledger["period_id"]),
                "reference": "TEST-SALE",
                "description": "Cash sale",
                "lines": [
                    {
                        "account_id": str(accounts["1000"]),
                        "currency_code": "SGD",
                        "debit": "125.55",
                        "credit": "0",
                    },
                    {
                        "account_id": str(accounts["4000"]),
                        "currency_code": "SGD",
                        "debit": "0",
                        "credit": "125.55",
                    },
                ],
            }
        ],
    }
