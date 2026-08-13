"""Constrain close-related journal links to the same company.

Revision ID: 0003_close_fks
Revises: 0002_trigger_enum
"""

from alembic import op

revision = "0003_close_fks"
down_revision = "0002_trigger_enum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("closing_events", "closing_entry_id", nullable=True)
    op.create_foreign_key(
        "fk_closing_events_opening_entry_company",
        "closing_events",
        "journal_entries",
        ["company_id", "opening_entry_id"],
        ["company_id", "id"],
    )
    op.create_foreign_key(
        "fk_closing_events_reversed_entry_company",
        "closing_events",
        "journal_entries",
        ["company_id", "reversed_by_entry_id"],
        ["company_id", "id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_closing_events_reversed_entry_company", "closing_events", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_closing_events_opening_entry_company", "closing_events", type_="foreignkey"
    )
    op.alter_column("closing_events", "closing_entry_id", nullable=False)
