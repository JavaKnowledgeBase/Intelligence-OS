"""add portfolio saved views

Revision ID: 20260320_000019
Revises: 20260320_000018
Create Date: 2026-03-20 19:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260320_000019"
down_revision = "20260320_000018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_saved_views",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("created_by_name", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("portfolio_view", sa.String(length=40), nullable=False),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_portfolio_saved_views_tenant_id"), "portfolio_saved_views", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_portfolio_saved_views_created_by"), "portfolio_saved_views", ["created_by"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_portfolio_saved_views_created_by"), table_name="portfolio_saved_views")
    op.drop_index(op.f("ix_portfolio_saved_views_tenant_id"), table_name="portfolio_saved_views")
    op.drop_table("portfolio_saved_views")
