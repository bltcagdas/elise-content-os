"""manual analytics snapshots

Revision ID: 0002_manual_analytics
Revises: 0001_initial
Create Date: 2026-05-10 00:00:01.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_manual_analytics"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "manual_analytics_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("plan_id", sa.String(length=64), nullable=True),
        sa.Column("platform_post_url", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_format", sa.String(length=32), nullable=False),
        sa.Column("reach", sa.Integer(), nullable=True),
        sa.Column("likes", sa.Integer(), nullable=True),
        sa.Column("comments", sa.Integer(), nullable=True),
        sa.Column("saves", sa.Integer(), nullable=True),
        sa.Column("shares", sa.Integer(), nullable=True),
        sa.Column("replies", sa.Integer(), nullable=True),
        sa.Column("follower_count_snapshot", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["content_plans.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_manual_analytics_snapshots_plan_id", "manual_analytics_snapshots", ["plan_id"])


def downgrade() -> None:
    op.drop_index("ix_manual_analytics_snapshots_plan_id", table_name="manual_analytics_snapshots")
    op.drop_table("manual_analytics_snapshots")
