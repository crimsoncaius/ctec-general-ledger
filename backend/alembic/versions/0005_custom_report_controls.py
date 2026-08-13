"""Add custom-report lifecycle controls and database invariants.

Revision ID: 0005_custom_reports
Revises: 0004_preferences
"""

import sqlalchemy as sa

from alembic import op

revision = "0005_custom_reports"
down_revision = "0004_preferences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "report_definitions",
        sa.Column("is_template", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "report_definitions",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_check_constraint(
        "ck_report_definitions_report_definition_type",
        "report_definitions",
        "report_type IN ('structured', 'legacy')",
    )
    op.create_check_constraint(
        "ck_report_definitions_report_definition_conversion_status",
        "report_definitions",
        "conversion_status IS NULL OR conversion_status IN "
        "('compatible', 'partial', 'manual', 'converted')",
    )
    op.create_check_constraint(
        "ck_report_definitions_report_definition_version_positive",
        "report_definitions",
        "version >= 1",
    )
    op.alter_column("report_definitions", "is_template", server_default=None)
    op.alter_column("report_definitions", "version", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "ck_report_definitions_report_definition_version_positive",
        "report_definitions",
        type_="check",
    )
    op.drop_constraint(
        "ck_report_definitions_report_definition_conversion_status",
        "report_definitions",
        type_="check",
    )
    op.drop_constraint(
        "ck_report_definitions_report_definition_type",
        "report_definitions",
        type_="check",
    )
    op.drop_column("report_definitions", "version")
    op.drop_column("report_definitions", "is_template")
