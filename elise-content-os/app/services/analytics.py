from datetime import datetime

from sqlalchemy.orm import Session

from app.models import ManualAnalyticsSnapshot


class AnalyticsService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_snapshot(
        self,
        *,
        plan_id: str | None,
        content_format: str,
        platform_post_url: str | None = None,
        published_at: datetime | None = None,
        reach: int | None = None,
        likes: int | None = None,
        comments: int | None = None,
        saves: int | None = None,
        shares: int | None = None,
        replies: int | None = None,
        follower_count_snapshot: int | None = None,
    ) -> ManualAnalyticsSnapshot:
        snapshot = ManualAnalyticsSnapshot(
            plan_id=plan_id,
            platform_post_url=platform_post_url,
            published_at=published_at,
            content_format=content_format,
            reach=reach,
            likes=likes,
            comments=comments,
            saves=saves,
            shares=shares,
            replies=replies,
            follower_count_snapshot=follower_count_snapshot,
        )
        self.session.add(snapshot)
        self.session.commit()
        return snapshot
