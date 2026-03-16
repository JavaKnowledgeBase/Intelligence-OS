"""session and ingestion enhancements

Revision ID: 20260316_000002
Revises: 20260316_000001
Create Date: 2026-03-16 04:05:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260316_000002"
down_revision: Union[str, None] = "20260316_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("source_name", sa.String(length=120), nullable=True))
    op.create_index(op.f("ix_listings_source_name"), "listings", ["source_name"], unique=False)

    op.add_column("market_insights", sa.Column("source_name", sa.String(length=120), nullable=True))
    op.create_index(op.f("ix_market_insights_source_name"), "market_insights", ["source_name"], unique=False)

    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("source_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("records_processed", sa.Integer(), nullable=False),
        sa.Column("records_created", sa.Integer(), nullable=False),
        sa.Column("records_updated", sa.Integer(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ingestion_runs_source_name"), "ingestion_runs", ["source_name"], unique=False)
    op.create_index(op.f("ix_ingestion_runs_status"), "ingestion_runs", ["status"], unique=False)
    op.create_index(op.f("ix_ingestion_runs_tenant_id"), "ingestion_runs", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ingestion_runs_tenant_id"), table_name="ingestion_runs")
    op.drop_index(op.f("ix_ingestion_runs_status"), table_name="ingestion_runs")
    op.drop_index(op.f("ix_ingestion_runs_source_name"), table_name="ingestion_runs")
    op.drop_table("ingestion_runs")

    op.drop_index(op.f("ix_market_insights_source_name"), table_name="market_insights")
    op.drop_column("market_insights", "source_name")

    op.drop_index(op.f("ix_listings_source_name"), table_name="listings")
    op.drop_column("listings", "source_name")
