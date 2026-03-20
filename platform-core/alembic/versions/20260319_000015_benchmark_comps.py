"""benchmark comps

Revision ID: 20260319_000015
Revises: 20260319_000014
Create Date: 2026-03-19 23:59:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260319_000015"
down_revision: Union[str, None] = "20260319_000014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "benchmark_comps",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("asset_class", sa.String(length=80), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("source_name", sa.String(length=120), nullable=False),
        sa.Column("closed_on", sa.Date(), nullable=True),
        sa.Column("sale_price", sa.Float(), nullable=False),
        sa.Column("net_operating_income", sa.Float(), nullable=True),
        sa.Column("cap_rate", sa.Float(), nullable=True),
        sa.Column("projected_irr", sa.Float(), nullable=True),
        sa.Column("equity_multiple", sa.Float(), nullable=True),
        sa.Column("average_dscr", sa.Float(), nullable=True),
        sa.Column("occupancy_rate", sa.Float(), nullable=True),
        sa.Column("leverage_ratio", sa.Float(), nullable=True),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_benchmark_comps_tenant_id"), "benchmark_comps", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_benchmark_comps_asset_class"), "benchmark_comps", ["asset_class"], unique=False)
    op.create_index(op.f("ix_benchmark_comps_location"), "benchmark_comps", ["location"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_benchmark_comps_location"), table_name="benchmark_comps")
    op.drop_index(op.f("ix_benchmark_comps_asset_class"), table_name="benchmark_comps")
    op.drop_index(op.f("ix_benchmark_comps_tenant_id"), table_name="benchmark_comps")
    op.drop_table("benchmark_comps")
