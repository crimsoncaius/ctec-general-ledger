"""Add company-scoped user display preferences.

Revision ID: 0004_preferences
Revises: 0003_close_fks
"""

from alembic import op
from app.db import Base

revision = "0004_preferences"
down_revision = "0003_close_fks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.tables["user_preferences"].create(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    op.drop_table("user_preferences")
