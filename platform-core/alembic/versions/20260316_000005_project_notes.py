"""project note support

Revision ID: 20260316_000005
Revises: 20260316_000004
Create Date: 2026-03-16 08:45:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260316_000005"
down_revision: Union[str, None] = "20260316_000004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_notes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("author_name", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_project_notes_project_id"), "project_notes", ["project_id"], unique=False)
    op.create_index(op.f("ix_project_notes_tenant_id"), "project_notes", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_project_notes_tenant_id"), table_name="project_notes")
    op.drop_index(op.f("ix_project_notes_project_id"), table_name="project_notes")
    op.drop_table("project_notes")
