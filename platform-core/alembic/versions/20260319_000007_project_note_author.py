"""project note author ownership

Revision ID: 20260319_000007
Revises: 20260316_000006
Create Date: 2026-03-19 10:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260319_000007"
down_revision: Union[str, None] = "20260316_000006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("project_notes", sa.Column("author_id", sa.String(length=64), nullable=True))
    op.execute(
        """
        UPDATE project_notes
        SET author_id = users.id
        FROM users
        WHERE project_notes.author_id IS NULL
          AND users.tenant_id = project_notes.tenant_id
          AND users.full_name = project_notes.author_name
        """
    )
    op.execute(
        """
        UPDATE project_notes
        SET author_id = projects.owner_id
        FROM projects
        WHERE project_notes.author_id IS NULL
          AND projects.id = project_notes.project_id
        """
    )
    op.alter_column("project_notes", "author_id", existing_type=sa.String(length=64), nullable=False)
    op.create_index(op.f("ix_project_notes_author_id"), "project_notes", ["author_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_project_notes_author_id"), table_name="project_notes")
    op.drop_column("project_notes", "author_id")
