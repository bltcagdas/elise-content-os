from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


JsonColumn = JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class ScenePrompt(Base):
    __tablename__ = "scene_prompts"

    scene_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    group: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    shot: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    kohya_caption: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    plans: Mapped[list["ContentPlan"]] = relationship(back_populates="scene")


class ContentPlan(Base):
    __tablename__ = "content_plans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    parent_plan_id: Mapped[Optional[str]] = mapped_column(ForeignKey("content_plans.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    trigger_time: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    content_type: Mapped[str] = mapped_column(String(32), default="story", nullable=False)
    scene_id: Mapped[str] = mapped_column(ForeignKey("scene_prompts.scene_id"), nullable=False, index=True)
    scene_group: Mapped[str] = mapped_column(String(64), nullable=False)
    excluded_scene_ids: Mapped[list[str]] = mapped_column(JsonColumn, default=list, nullable=False)
    image_brief: Mapped[str] = mapped_column(Text, nullable=False)
    caption: Mapped[str] = mapped_column(Text, nullable=False)
    caption_formula: Mapped[str] = mapped_column(String(64), nullable=False)
    hashtags: Mapped[list[str]] = mapped_column(JsonColumn, default=list, nullable=False)
    publishing_note: Mapped[str] = mapped_column(Text, nullable=False)
    monthly_checklist_fulfilled: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    watch_used: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    shoes_used: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    scene: Mapped[ScenePrompt] = relationship(back_populates="plans")
    parent: Mapped[Optional["ContentPlan"]] = relationship(remote_side=[id])
    events: Mapped[list["PublishEvent"]] = relationship(back_populates="plan")


class PublishEvent(Base):
    __tablename__ = "publish_events"
    __table_args__ = (UniqueConstraint("callback_event_id", name="uq_publish_events_callback_event_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("content_plans.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    callback_event_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    plan: Mapped[ContentPlan] = relationship(back_populates="events")


class DailyCounter(Base):
    __tablename__ = "daily_counters"

    local_date: Mapped[date] = mapped_column(Date, primary_key=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    story_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class MonthlyChecklistItem(Base):
    __tablename__ = "monthly_checklist_items"
    __table_args__ = (UniqueConstraint("month", "item_id", name="uq_monthly_checklist_month_item"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    month: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(String(32), nullable=False)
    item: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    completed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    target_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    completed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    raw: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class WeeklyReview(Base):
    __tablename__ = "weekly_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ManualAnalyticsSnapshot(Base):
    __tablename__ = "manual_analytics_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[Optional[str]] = mapped_column(ForeignKey("content_plans.id"), nullable=True, index=True)
    platform_post_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    content_format: Mapped[str] = mapped_column(String(32), nullable=False)
    reach: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    likes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    comments: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    saves: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shares: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    replies: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    follower_count_snapshot: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
