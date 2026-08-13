"""Constrain legacy migration lineage and validation state."""

from alembic import op

revision = "0006_legacy_migration"
down_revision = "0005_custom_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "migration_runs_digest_length_check",
        "migration_runs",
        "char_length(source_digest) = 64",
    )
    op.create_check_constraint(
        "migration_staging_source_record_check",
        "migration_staging_records",
        "source_record > 0",
    )
    op.create_check_constraint(
        "migration_staging_severity_check",
        "migration_staging_records",
        "severity in ('ok', 'warning', 'error')",
    )
    op.create_check_constraint(
        "migration_staging_source_table_check",
        "migration_staging_records",
        "source_table in ('GLACCNT', 'GLACCNX', 'GLMAIN', 'GLTRANS', 'GLGP', 'GLREP')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "migration_staging_source_table_check", "migration_staging_records", type_="check"
    )
    op.drop_constraint(
        "migration_staging_severity_check", "migration_staging_records", type_="check"
    )
    op.drop_constraint(
        "migration_staging_source_record_check", "migration_staging_records", type_="check"
    )
    op.drop_constraint("migration_runs_digest_length_check", "migration_runs", type_="check")
