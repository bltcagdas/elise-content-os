"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-10 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "scene_prompts",
        sa.Column("scene_id", sa.String(length=16), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("group", sa.String(length=64), nullable=False),
        sa.Column("shot", sa.String(length=64), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("kohya_caption", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("scene_id"),
    )
    op.create_index("ix_scene_prompts_group", "scene_prompts", ["group"])

    op.create_table(
        "content_plans",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("parent_plan_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("trigger_time", sa.String(length=32), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("scene_id", sa.String(length=16), nullable=False),
        sa.Column("scene_group", sa.String(length=64), nullable=False),
        sa.Column("excluded_scene_ids", json_type, nullable=False),
        sa.Column("image_brief", sa.Text(), nullable=False),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("caption_formula", sa.String(length=64), nullable=False),
        sa.Column("hashtags", json_type, nullable=False),
        sa.Column("publishing_note", sa.Text(), nullable=False),
        sa.Column("monthly_checklist_fulfilled", sa.String(length=32), nullable=True),
        sa.Column("watch_used", sa.String(length=255), nullable=True),
        sa.Column("shoes_used", sa.String(length=255), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["parent_plan_id"], ["content_plans.id"]),
        sa.ForeignKeyConstraint(["scene_id"], ["scene_prompts.scene_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_content_plans_scene_id", "content_plans", ["scene_id"])
    op.create_index("ix_content_plans_status", "content_plans", ["status"])
    op.create_index("ix_content_plans_trigger_time", "content_plans", ["trigger_time"])

    op.create_table(
        "publish_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("plan_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("callback_event_id", sa.String(length=128), nullable=True),
        sa.Column("payload", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["content_plans.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("callback_event_id", name="uq_publish_events_callback_event_id"),
    )
    op.create_index("ix_publish_events_plan_id", "publish_events", ["plan_id"])

    op.create_table(
        "daily_counters",
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("story_count", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("local_date"),
    )

    op.create_table(
        "monthly_checklist_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("month", sa.String(length=16), nullable=False),
        sa.Column("item_id", sa.String(length=32), nullable=False),
        sa.Column("item", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("completed_count", sa.Integer(), nullable=False),
        sa.Column("target_count", sa.Integer(), nullable=False),
        sa.Column("completed_date", sa.Date(), nullable=True),
        sa.Column("raw", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("month", "item_id", name="uq_monthly_checklist_month_item"),
    )
    op.create_index("ix_monthly_checklist_items_month", "monthly_checklist_items", ["month"])
    op.create_index("ix_monthly_checklist_items_status", "monthly_checklist_items", ["status"])

    op.create_table(
        "weekly_reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("metrics", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_weekly_reviews_week_start", "weekly_reviews", ["week_start"])


def downgrade() -> None:
    op.drop_index("ix_weekly_reviews_week_start", table_name="weekly_reviews")
    op.drop_table("weekly_reviews")
    op.drop_index("ix_monthly_checklist_items_status", table_name="monthly_checklist_items")
    op.drop_index("ix_monthly_checklist_items_month", table_name="monthly_checklist_items")
    op.drop_table("monthly_checklist_items")
    op.drop_table("daily_counters")
    op.drop_index("ix_publish_events_plan_id", table_name="publish_events")
    op.drop_table("publish_events")
    op.drop_index("ix_content_plans_trigger_time", table_name="content_plans")
    op.drop_index("ix_content_plans_status", table_name="content_plans")
    op.drop_index("ix_content_plans_scene_id", table_name="content_plans")
    op.drop_table("content_plans")
    op.drop_index("ix_scene_prompts_group", table_name="scene_prompts")
    op.drop_table("scene_prompts")
