from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import ContentPlan, WeeklyReview
from app.utils.time import local_today


class WeeklyReviewService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_review(self) -> WeeklyReview:
        today = local_today()
        week_start = today - timedelta(days=today.weekday())
        rows = (
            self.session.query(ContentPlan)
            .filter(ContentPlan.created_at >= week_start)
            .order_by(ContentPlan.created_at.asc())
            .all()
        )
        metrics = {
            "planned": len(rows),
            "published": sum(1 for row in rows if row.status == "published"),
            "skipped": sum(1 for row in rows if row.status == "skipped"),
            "regenerate_requested": sum(1 for row in rows if row.status == "regenerate_requested"),
            "scenes": [row.scene_id for row in rows],
        }
        summary = (
            f"Weekly review for {week_start.isoformat()}: "
            f"{metrics['published']} published, {metrics['skipped']} skipped, "
            f"{metrics['regenerate_requested']} regenerate requests."
        )
        review = WeeklyReview(week_start=week_start, summary=summary, metrics=metrics)
        self.session.add(review)
        self.session.commit()
        return review
