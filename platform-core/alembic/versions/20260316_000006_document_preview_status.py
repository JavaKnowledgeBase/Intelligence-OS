"""document preview and status fields

Revision ID: 20260316_000006
Revises: 20260316_000005
Create Date: 2026-03-16 09:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260316_000006"
down_revision: Union[str, None] = "20260316_000005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("project_documents", sa.Column("processing_status", sa.String(length=40), server_default="ready", nullable=False))
    op.add_column("project_documents", sa.Column("preview_available", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("project_documents", sa.Column("extracted_text_excerpt", sa.Text(), server_default="", nullable=False))


def downgrade() -> None:
    op.drop_column("project_documents", "extracted_text_excerpt")
    op.drop_column("project_documents", "preview_available")
    op.drop_column("project_documents", "processing_status")
