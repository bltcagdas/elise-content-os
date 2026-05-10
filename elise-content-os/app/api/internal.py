from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import TriggerTime
from app.services.orchestrator import TriggerOrchestrator
from app.services.weekly import WeeklyReviewService
from app.utils.security import require_internal_token

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/triggers/{trigger_time}", dependencies=[Depends(require_internal_token)])
def run_trigger(
    trigger_time: str,
    dry_run: bool = False,
    session: Session = Depends(get_session),
):
    if trigger_time not in {"morning", "afternoon", "evening"}:
        raise HTTPException(status_code=400, detail="Invalid trigger_time")
    result = TriggerOrchestrator(session).run_trigger(trigger_time=trigger_time, dry_run=dry_run)  # type: ignore[arg-type]
    return result.model_dump()


@router.post("/reviews/weekly", dependencies=[Depends(require_internal_token)])
def weekly_review(session: Session = Depends(get_session)):
    review = WeeklyReviewService(session).create_review()
    return {"status": "created", "review_id": review.id, "week_start": review.week_start.isoformat()}

