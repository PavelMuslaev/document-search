"""Create documents table.

Revision ID: 001
Revises:
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rubrics", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_date", sa.DateTime(timezone=False), nullable=False),
    )
    op.create_index("ix_documents_created_date", "documents", ["created_date"])


def downgrade() -> None:
    op.drop_index("ix_documents_created_date", table_name="documents")
    op.drop_table("documents")
