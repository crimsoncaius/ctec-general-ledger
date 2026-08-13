"""Use the persisted lower-case enum values in immutable ledger triggers.

Revision ID: 0002_trigger_enum
Revises: 0001_initial
"""

from alembic import op

revision = "0002_trigger_enum"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_posted_journal_mutation()
        RETURNS trigger AS $$
        BEGIN
          IF OLD.status = 'posted' THEN
            RAISE EXCEPTION 'posted journal entries are immutable; create a reversal';
          END IF;
          RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END;
        $$ LANGUAGE plpgsql;

        CREATE OR REPLACE FUNCTION prevent_posted_line_mutation()
        RETURNS trigger AS $$
        DECLARE entry_status journalstatus;
        BEGIN
          SELECT status INTO entry_status
          FROM journal_entries
          WHERE id = OLD.entry_id AND company_id = OLD.company_id;
          IF entry_status = 'posted' THEN
            RAISE EXCEPTION 'posted journal lines are immutable; create a reversal';
          END IF;
          RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END;
        $$ LANGUAGE plpgsql;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_posted_journal_mutation()
        RETURNS trigger AS $$
        BEGIN
          IF OLD.status::text = 'posted' THEN
            RAISE EXCEPTION 'posted journal entries are immutable; create a reversal';
          END IF;
          RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
