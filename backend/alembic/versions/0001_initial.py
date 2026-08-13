"""Initial normalized ledger schema and immutable-posting controls."""

from sqlalchemy import MetaData

from alembic import op
from app import models  # noqa: F401
from app.db import Base

INITIAL_TABLES = [
    "currencies",
    "companies",
    "users",
    "permissions",
    "roles",
    "role_permissions",
    "memberships",
    "fiscal_years",
    "fiscal_periods",
    "accounts",
    "exchange_rates",
    "number_sequences",
    "journal_batches",
    "journal_entries",
    "journal_lines",
    "posting_events",
    "period_balances",
    "budgets",
    "closing_events",
    "audit_events",
    "saved_views",
    "report_definitions",
    "report_runs",
    "operation_jobs",
    "migration_runs",
    "migration_staging_records",
]

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    historical = MetaData()
    initial_tables = [Base.metadata.tables[name].to_metadata(historical) for name in INITIAL_TABLES]
    report_definitions = historical.tables["report_definitions"]
    # Revision 0001 is a historical snapshot. Later ORM fields must not leak into a clean install.
    for column_name in ("is_template", "version"):
        report_definitions._columns.remove(report_definitions.c[column_name])
    later_constraints = {
        "ck_report_definitions_report_definition_type",
        "ck_report_definitions_report_definition_conversion_status",
        "ck_report_definitions_report_definition_version_positive",
    }
    for constraint in list(report_definitions.constraints):
        if constraint.name in later_constraints:
            report_definitions.constraints.remove(constraint)
    phase7_constraints = {
        "migration_runs_digest_length_check",
        "migration_staging_source_record_check",
        "migration_staging_severity_check",
        "migration_staging_source_table_check",
    }
    for table_name in ("migration_runs", "migration_staging_records"):
        table = historical.tables[table_name]
        for constraint in list(table.constraints):
            if constraint.name in phase7_constraints:
                table.constraints.remove(constraint)
    historical.create_all(bind=bind, tables=initial_tables)
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION prevent_posted_journal_mutation()
            RETURNS trigger AS $$
            BEGIN
              IF OLD.status = 'POSTED' THEN
                RAISE EXCEPTION 'posted journal entries are immutable; create a reversal';
              END IF;
              RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
            END;
            $$ LANGUAGE plpgsql;

            CREATE TRIGGER journal_entries_immutable
            BEFORE UPDATE OR DELETE ON journal_entries
            FOR EACH ROW EXECUTE FUNCTION prevent_posted_journal_mutation();

            CREATE OR REPLACE FUNCTION prevent_posted_line_mutation()
            RETURNS trigger AS $$
            DECLARE entry_status journalstatus;
            BEGIN
              SELECT status INTO entry_status
              FROM journal_entries
              WHERE id = OLD.entry_id AND company_id = OLD.company_id;
              IF entry_status = 'POSTED' THEN
                RAISE EXCEPTION 'posted journal lines are immutable; create a reversal';
              END IF;
              RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
            END;
            $$ LANGUAGE plpgsql;

            CREATE TRIGGER journal_lines_immutable
            BEFORE UPDATE OR DELETE ON journal_lines
            FOR EACH ROW EXECUTE FUNCTION prevent_posted_line_mutation();
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(
        bind=bind, tables=[Base.metadata.tables[name] for name in reversed(INITIAL_TABLES)]
    )
    if bind.dialect.name == "postgresql":
        op.execute("DROP FUNCTION IF EXISTS prevent_posted_line_mutation() CASCADE")
        op.execute("DROP FUNCTION IF EXISTS prevent_posted_journal_mutation() CASCADE")
