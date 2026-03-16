"""project document workspace support

Revision ID: 20260316_000004
Revises: 20260316_000003
Create Date: 2026-03-16 08:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260316_000004"
down_revision: Union[str, None] = "20260316_000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_documents",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("stored_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_by", sa.String(length=255), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stored_name"),
    )
    op.create_index(op.f("ix_project_documents_project_id"), "project_documents", ["project_id"], unique=False)
    op.create_index(op.f("ix_project_documents_tenant_id"), "project_documents", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_project_documents_tenant_id"), table_name="project_documents")
    op.drop_index(op.f("ix_project_documents_project_id"), table_name="project_documents")
    op.drop_table("project_documents")
