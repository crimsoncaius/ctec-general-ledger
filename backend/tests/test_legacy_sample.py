from collections import Counter
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import (
    Account,
    Budget,
    Company,
    JournalBatch,
    JournalEntry,
    JournalLine,
    JournalStatus,
    MigrationRun,
    MigrationStagingRecord,
    ReportDefinition,
    User,
)
from app.seed import _add_calendar, _archive, _settings
from app.services.legacy_dbf import apply_run, stage_archive

SAMPLE_DIR = Path(__file__).resolve().parents[3] / "GL_Data"


def test_actual_legacy_sample_stages_reconciles_and_applies() -> None:
    settings = _settings(SAMPLE_DIR)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "admin@example.com"))
        assert user is not None
        company = Company(
            code="ALCAN-SAMPLE",
            name=str(settings["company_name"]),
            base_currency_code="SGD",
            rounding_places=int(settings["rounding_places"]),
            use_bankers_rounding=False,
        )
        db.add(company)
        db.flush()
        _add_calendar(db, company, settings)
        db.commit()

        staged = stage_archive(
            db,
            company_id=company.id,
            user_id=user.id,
            source_name="actual-legacy-sample.zip",
            archive=_archive(SAMPLE_DIR),
        )
        assert staged.counts["tables"] == {
            "GLACCNT": 141,
            "GLACCNX": 141,
            "GLGP": 0,
            "GLMAIN": 5,
            "GLREP": 10,
            "GLTRANS": 0,
        }
        assert staged.counts["errors"] == 0
        assert staged.reconciliation == {
            "opening_balance_net": "0.00",
            "recorded_current_net": "0.00",
            "ledger_debits": "605.88",
            "ledger_credits": "605.88",
            "ledger_balanced": True,
            "account_periods_match": True,
            "apply_ready": True,
        }
        issue_codes = {
            issue["code"]
            for row in db.scalars(
                select(MigrationStagingRecord).where(
                    MigrationStagingRecord.migration_run_id == staged.id
                )
            )
            for issue in row.issues
        }
        assert {
            "currency_normalized",
            "derived_group_key",
            "base_currency_rate_normalized",
            "legacy_report_warning",
        }.issubset(issue_codes)

        applied = apply_run(db, staged, user.id)
        assert applied.counts["applied_accounts"] == 141
        assert applied.counts["applied_posted_batches"] == 2
        assert applied.counts["applied_draft_batches"] == 0
        assert applied.counts["applied_reports"] == 10

        assert (
            db.scalar(select(func.count(Account.id)).where(Account.company_id == company.id)) == 141
        )
        assert (
            db.scalar(
                select(func.count(JournalBatch.id)).where(JournalBatch.company_id == company.id)
            )
            == 2
        )
        assert db.scalar(select(func.count(Budget.id)).where(Budget.company_id == company.id)) == 0
        assert (
            db.scalar(
                select(func.count(MigrationRun.id)).where(MigrationRun.company_id == company.id)
            )
            == 2
        )

        reports = list(
            db.scalars(
                select(ReportDefinition).where(ReportDefinition.company_id == company.id)
            ).all()
        )
        assert Counter(report.conversion_status for report in reports) == {
            "partial": 7,
            "manual": 3,
        }
        assert all(report.legacy_spec for report in reports)

        foreign_opening = db.execute(
            select(JournalLine)
            .join(Account, Account.id == JournalLine.account_id)
            .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
            .where(
                JournalLine.company_id == company.id,
                Account.code == "B-B03",
                JournalEntry.reference == "LEGACY-OPEN",
            )
        ).scalar_one()
        assert foreign_opening.currency_code == "USD"
        assert foreign_opening.debit_original == Decimal("6000.000000")
        assert foreign_opening.debit_base == Decimal("11764.700000")

        posted_entry = db.scalar(
            select(JournalEntry).where(
                JournalEntry.company_id == company.id,
                JournalEntry.reference == "AP->GL",
                JournalEntry.status == JournalStatus.POSTED,
            )
        )
        assert posted_entry is not None
        posted_lines = list(
            db.scalars(select(JournalLine).where(JournalLine.entry_id == posted_entry.id)).all()
        )
        assert sum((line.debit_base for line in posted_lines), Decimal("0")) == Decimal("605.88")
        assert sum((line.credit_base for line in posted_lines), Decimal("0")) == Decimal("605.88")
