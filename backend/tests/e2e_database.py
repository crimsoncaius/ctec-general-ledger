"""Create and destroy the private database used by Playwright.

This is deliberately a command-line test utility, not an application endpoint.  Its database-name
guard is the final protection against resetting a developer or demonstration database.
"""

from __future__ import annotations

import argparse
import os

import psycopg
from alembic.config import Config
from psycopg import sql
from sqlalchemy import select
from sqlalchemy.engine import URL, make_url

from alembic import command

DEFAULT_TEST_DATABASE_URL = "postgresql+psycopg://ctec:ctec_local_only@localhost:15432/ctec_gl_e2e"


def checked_url(raw_url: str) -> URL:
    url = make_url(raw_url)
    database = url.database or ""
    if not database.startswith("ctec_gl_e2e"):
        raise RuntimeError(
            f"Refusing to manage database {database!r}; E2E databases must start with ctec_gl_e2e"
        )
    return url


def admin_dsn(url: URL) -> str:
    return os.getenv(
        "TEST_DATABASE_ADMIN_URL",
        url.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False),
    )


def drop_database(url: URL) -> None:
    database = url.database
    assert database is not None
    with psycopg.connect(admin_dsn(url), autocommit=True) as connection:
        connection.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = %s AND pid <> pg_backend_pid()",
            (database,),
        )
        connection.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database)))


def add_restricted_browser_user() -> None:
    from app.db import SessionLocal
    from app.models import Membership, Permission, Role, RolePermission, User
    from app.security import hash_password
    from app.seed_support import stable_id

    with SessionLocal() as db:
        company_id = stable_id("company:acme")
        role = Role(
            id=stable_id("ACME:role:restricted"),
            company_id=company_id,
            name="Restricted viewer",
            system=True,
        )
        user = User(
            id=stable_id("user:restricted"),
            email="restricted@example.com",
            display_name="Riley Restricted",
            password_hash=hash_password("CTec-E2E-Restricted-2026!"),
        )
        db.add_all([role, user])
        db.flush()
        db.add(Membership(company_id=company_id, user_id=user.id, role_id=role.id))
        for code in ("accounts.view", "fiscal.view", "journals.view", "journals.inquire"):
            assert db.scalar(select(Permission.code).where(Permission.code == code)) is not None
            db.add(
                RolePermission(
                    company_id=company_id,
                    role_id=role.id,
                    permission_code=code,
                )
            )
        db.commit()


def prepare_database(url: URL) -> None:
    drop_database(url)
    database = url.database
    assert database is not None
    with psycopg.connect(admin_dsn(url), autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))

    os.environ["DATABASE_URL"] = url.render_as_string(hide_password=False)
    os.environ["ENVIRONMENT"] = "test"
    os.environ.setdefault("JWT_SECRET", "e2e-only-secret-that-is-longer-than-thirty-two-characters")

    from app.config import get_settings

    get_settings.cache_clear()
    alembic = Config("backend/alembic.ini")
    command.upgrade(alembic, "head")

    from app.test_seed import seed

    seed()
    add_restricted_browser_user()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "drop"))
    parser.add_argument("--url", default=os.getenv("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL))
    args = parser.parse_args()
    url = checked_url(args.url)
    if args.action == "prepare":
        prepare_database(url)
    else:
        drop_database(url)


if __name__ == "__main__":
    main()
