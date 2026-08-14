from __future__ import annotations

import io
import os
import secrets
import zipfile
from datetime import date, timedelta
from pathlib import Path
from typing import TypedDict

from dbfread import DBF  # type: ignore[import-untyped]
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import (
    Account,
    Company,
    Currency,
    FiscalPeriod,
    FiscalYear,
    JournalBatch,
    Membership,
    Permission,
    ReportDefinition,
    Role,
    RolePermission,
    User,
)
from app.security import hash_password
from app.seed_support import CAPABILITIES, stable_id
from app.services.legacy_dbf import apply_run, stage_archive

REQUIRED_FILES = ("GLACCNT.DAT", "GLMAIN.DAT", "GLCOMP.SET")
PREPARER_CAPABILITIES = (
    "accounts.view",
    "fiscal.view",
    "journals.create",
    "journals.update",
    "journals.view",
    "journals.validate",
    "journals.inquire",
    "reports.run",
)
APPROVER_CAPABILITIES = (
    "accounts.view",
    "fiscal.view",
    "journals.view",
    "journals.approve",
    "journals.post",
    "journals.reverse",
    "journals.inquire",
    "reports.run",
    "integrity.run",
)


class LegacySettings(TypedDict):
    company_name: str
    periods: int
    start_month: int
    start_year: int
    rounding_places: int


def _legacy_data_directory(explicit: str | Path | None = None) -> Path:
    candidates = []
    if explicit is not None:
        candidates.append(Path(explicit))
    configured = os.getenv("LEGACY_DEMO_DATA_DIR")
    if configured:
        candidates.append(Path(configured))
    candidates.append(Path("/app/legacy-demo"))
    module_parents = Path(__file__).resolve().parents
    if len(module_parents) > 3:
        candidates.append(module_parents[3] / "GL_Data")
    candidates.extend([Path.cwd() / "GL_Data", Path.cwd().parent / "GL_Data"])
    for candidate in candidates:
        resolved = candidate.resolve()
        if all((resolved / name).is_file() for name in REQUIRED_FILES):
            return resolved
    searched = ", ".join(str(candidate) for candidate in candidates)
    raise RuntimeError(f"Legacy demo data was not found; searched: {searched}")


def _settings(source: Path) -> LegacySettings:
    rows = list(
        DBF(
            str(source / "GLCOMP.SET"),
            load=True,
            ignore_missing_memofile=True,
            char_decode_errors="replace",
        )
    )

    def value(record_no: int) -> str:
        return str(rows[record_no - 1]["VALUE"] or "").strip()

    return {
        "company_name": value(3) or "ALCAN GENERAL TRADING PTE LTD",
        "periods": int(value(13) or "12"),
        "start_month": int(value(14) or "2"),
        "start_year": int(value(15) or "2003"),
        "rounding_places": int(value(29) or "2"),
    }


def _archive(source: Path) -> bytes:
    names = {
        *REQUIRED_FILES,
        "GLACCNX.DAT",
        "GLGP.DAT",
        "GLTRANS.DAT",
        "GLREP.DAT",
        *(path.name for path in source.glob("*.FMT")),
    }
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(names, key=str.upper):
            path = source / name
            if path.is_file():
                archive.writestr(name, path.read_bytes())
    return stream.getvalue()


def _next_month(value: date) -> date:
    return date(value.year + (value.month == 12), 1 if value.month == 12 else value.month + 1, 1)


def _add_calendar(db: Session, company: Company, settings: LegacySettings) -> None:
    periods = int(settings["periods"])
    if periods != 12:
        raise RuntimeError(
            f"The packaged ALCAN sample must contain 12 fiscal periods, got {periods}"
        )
    start = date(int(settings["start_year"]), int(settings["start_month"]), 1)
    period_starts = [start]
    for _ in range(periods):
        period_starts.append(_next_month(period_starts[-1]))
    fiscal_year = FiscalYear(
        id=stable_id("ALCAN:fy:FY2003"),
        company_id=company.id,
        label="FY2003",
        start_date=start,
        end_date=period_starts[-1] - timedelta(days=1),
    )
    db.add(fiscal_year)
    db.flush()
    for period_no in range(1, periods + 1):
        db.add(
            FiscalPeriod(
                id=stable_id(f"ALCAN:FY2003:period:{period_no}"),
                company_id=company.id,
                fiscal_year_id=fiscal_year.id,
                period_no=period_no,
                label=f"P{period_no:02d}",
                start_date=period_starts[period_no - 1],
                end_date=period_starts[period_no] - timedelta(days=1),
            )
        )


def _add_access_model(
    db: Session,
    company: Company,
    *,
    admin_email: str,
    admin_password: str,
    admin_display_name: str,
    disable_non_admin: bool,
) -> User:
    for code, description, legacy in CAPABILITIES:
        db.add(Permission(code=code, description=description, legacy_number=legacy))
    users = {
        "admin": User(
            id=stable_id("user:admin"),
            email=admin_email.lower(),
            display_name=admin_display_name,
            password_hash=hash_password(admin_password),
        ),
        "preparer": User(
            id=stable_id("user:preparer"),
            email="preparer@example.com",
            display_name="Priya Preparer",
            password_hash=hash_password(
                secrets.token_urlsafe(32) if disable_non_admin else "CTec-Demo-Prepare-2026!"
            ),
            active=not disable_non_admin,
        ),
        "approver": User(
            id=stable_id("user:approver"),
            email="approver@example.com",
            display_name="Alex Approver",
            password_hash=hash_password(
                secrets.token_urlsafe(32) if disable_non_admin else "CTec-Demo-Approve-2026!"
            ),
            active=not disable_non_admin,
        ),
    }
    db.add_all(users.values())
    db.flush()
    roles = {
        name: Role(
            id=stable_id(f"ALCAN:role:{name}"),
            company_id=company.id,
            name=name.title(),
            system=True,
        )
        for name in ("administrator", "preparer", "approver")
    }
    db.add_all(roles.values())
    db.flush()
    for user_name, role_name in (
        ("admin", "administrator"),
        ("preparer", "preparer"),
        ("approver", "approver"),
    ):
        db.add(
            Membership(
                company_id=company.id,
                user_id=users[user_name].id,
                role_id=roles[role_name].id,
            )
        )
    for code, _, _ in CAPABILITIES:
        db.add(
            RolePermission(
                company_id=company.id,
                role_id=roles["administrator"].id,
                permission_code=code,
            )
        )
    for role_name, capabilities in (
        ("preparer", PREPARER_CAPABILITIES),
        ("approver", APPROVER_CAPABILITIES),
    ):
        for code in capabilities:
            db.add(
                RolePermission(
                    company_id=company.id,
                    role_id=roles[role_name].id,
                    permission_code=code,
                )
            )
    return users["admin"]


def seed(
    *,
    admin_email: str = "admin@example.com",
    admin_password: str = "CTec-Demo-Admin-2026!",
    admin_display_name: str = "Demo Administrator",
    disable_non_admin: bool = False,
    legacy_data_dir: str | Path | None = None,
) -> None:
    source = _legacy_data_directory(legacy_data_dir)
    legacy_settings = _settings(source)
    archive = _archive(source)
    with SessionLocal() as db:
        if db.scalar(select(User.id).limit(1)) is not None:
            print("Seed skipped: data already exists")
            return
        db.add_all(
            [
                Currency(code="SGD", name="Singapore Dollar", minor_units=2),
                Currency(code="USD", name="US Dollar", minor_units=2),
            ]
        )
        db.flush()
        company = Company(
            id=stable_id("company:alcan"),
            code="ALCAN",
            name=str(legacy_settings["company_name"])[:120],
            base_currency_code="SGD",
            timezone="Asia/Singapore",
            rounding_places=int(legacy_settings["rounding_places"]),
            use_bankers_rounding=False,
        )
        db.add(company)
        admin = _add_access_model(
            db,
            company,
            admin_email=admin_email,
            admin_password=admin_password,
            admin_display_name=admin_display_name,
            disable_non_admin=disable_non_admin,
        )
        _add_calendar(db, company, legacy_settings)
        db.commit()

        staged = stage_archive(
            db,
            company_id=company.id,
            user_id=admin.id,
            source_name="legacy-sample.zip",
            archive=archive,
        )
        if not bool(staged.reconciliation.get("apply_ready")):
            raise RuntimeError(
                "Packaged legacy sample did not reconcile: "
                f"{staged.reconciliation}; counts={staged.counts}"
            )
        applied = apply_run(db, staged, admin.id)
        expected = {
            "applied_accounts": 141,
            "applied_posted_batches": 2,
            "applied_draft_batches": 0,
            "applied_reports": 10,
        }
        actual = {key: applied.counts.get(key) for key in expected}
        if actual != expected:
            raise RuntimeError(f"Legacy seed count mismatch: expected {expected}, got {actual}")
        if db.scalar(select(func.count(Account.id)).where(Account.company_id == company.id)) != 141:
            raise RuntimeError("Legacy seed account verification failed")
        if (
            db.scalar(
                select(func.count(JournalBatch.id)).where(JournalBatch.company_id == company.id)
            )
            != 2
        ):
            raise RuntimeError("Legacy seed journal verification failed")
        if (
            db.scalar(
                select(func.count(ReportDefinition.id)).where(
                    ReportDefinition.company_id == company.id
                )
            )
            != 10
        ):
            raise RuntimeError("Legacy seed report verification failed")
        print(
            "Seeded ALCAN from the read-only legacy sample: "
            "141 accounts, 2 posted batches, 10 legacy reports"
        )


if __name__ == "__main__":
    seed()
