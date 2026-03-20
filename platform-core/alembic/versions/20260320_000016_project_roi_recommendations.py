"""project roi recommendations

Revision ID: 20260320_000016
Revises: 20260319_000015
Create Date: 2026-03-20 12:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260320_000016"
down_revision: Union[str, None] = "20260319_000015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_roi_scenario_recommendations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("scenario_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("recommendation", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scenario_id"], ["project_roi_scenarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_project_roi_scenario_recommendations_project_id"), "project_roi_scenario_recommendations", ["project_id"], unique=False)
    op.create_index(op.f("ix_project_roi_scenario_recommendations_scenario_id"), "project_roi_scenario_recommendations", ["scenario_id"], unique=False)
    op.create_index(op.f("ix_project_roi_scenario_recommendations_tenant_id"), "project_roi_scenario_recommendations", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_project_roi_scenario_recommendations_tenant_id"), table_name="project_roi_scenario_recommendations")
    op.drop_index(op.f("ix_project_roi_scenario_recommendations_scenario_id"), table_name="project_roi_scenario_recommendations")
    op.drop_index(op.f("ix_project_roi_scenario_recommendations_project_id"), table_name="project_roi_scenario_recommendations")
    op.drop_table("project_roi_scenario_recommendations")
