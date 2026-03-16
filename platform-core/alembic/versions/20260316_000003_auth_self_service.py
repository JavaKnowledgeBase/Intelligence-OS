"""auth self service support

Revision ID: 20260316_000003
Revises: 20260316_000002
Create Date: 2026-03-16 06:05:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260316_000003"
down_revision: Union[str, None] = "20260316_000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "access_requests",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("requested_role", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_access_requests_email"), "access_requests", ["email"], unique=False)
    op.create_index(op.f("ix_access_requests_status"), "access_requests", ["status"], unique=False)

    op.create_table(
        "password_reset_requests",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("reset_token", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_password_reset_requests_email"), "password_reset_requests", ["email"], unique=False)
    op.create_index(op.f("ix_password_reset_requests_reset_token"), "password_reset_requests", ["reset_token"], unique=True)
    op.create_index(op.f("ix_password_reset_requests_user_id"), "password_reset_requests", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_password_reset_requests_user_id"), table_name="password_reset_requests")
    op.drop_index(op.f("ix_password_reset_requests_reset_token"), table_name="password_reset_requests")
    op.drop_index(op.f("ix_password_reset_requests_email"), table_name="password_reset_requests")
    op.drop_table("password_reset_requests")

    op.drop_index(op.f("ix_access_requests_status"), table_name="access_requests")
    op.drop_index(op.f("ix_access_requests_email"), table_name="access_requests")
    op.drop_table("access_requests")
