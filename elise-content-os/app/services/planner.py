import hashlib
import logging
from datetime import timedelta
from typing import Iterable
from uuid import uuid4

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import ContentPlan, DailyCounter, MonthlyChecklistItem, ScenePrompt
from app.schemas import TriggerTime
from app.services.caption import CaptionService
from app.utils.time import is_sunday, local_today, utc_now

logger = logging.getLogger(__name__)


TRIGGER_GROUPS: dict[str, tuple[str, ...]] = {
    "morning": ("A_closeup", "D_detail"),
    "afternoon": ("B_waist_up", "C_full_body"),
    "evening": ("A_closeup", "B_waist_up"),
}

CHECKLIST_KEYWORDS: dict[str, tuple[str, ...]] = {
    "MCL-02": ("gym", "post-gym", "athletic", "workout"),
    "MCL-03": ("book", "reading", "couch", "desk"),
    "MCL-04": ("coffee", "cup", "aeropress", "fellow", "kitchen"),
    "MCL-05": ("golf", "gti", "car", "drive", "road"),
    "MCL-06": ("watch", "wrist", "tissot", "daniel", "seiko", "casio", "komono"),
    "MCL-07": ("desk", "macbook", "office", "work", "client"),
    "MCL-08": ("arabic", "lesson", "notebook", "study"),
}


class PlannerSkip(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class PlannerService:
    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        caption_service: CaptionService | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.caption_service = caption_service or CaptionService(self.settings)

    def create_plan(
        self,
        trigger_time: TriggerTime,
        *,
        excluded_scene_ids: Iterable[str] | None = None,
        parent_plan_id: str | None = None,
        dry_run: bool = False,
    ) -> ContentPlan:
        self._assert_can_run()
        explicit_exclusions = set(excluded_scene_ids or [])
        scene = self._select_scene(trigger_time, explicit_exclusions)
        monthly_focus = self._monthly_focus_for_scene(scene)
        recent_captions = self._recent_captions()
        caption = self.caption_service.generate(
            scene=scene,
            trigger_time=trigger_time,
            monthly_focus=monthly_focus,
            recent_captions=recent_captions,
            dry_run=dry_run,
        )
        plan = ContentPlan(
            id=self._new_plan_id(trigger_time),
            parent_plan_id=parent_plan_id,
            status="pending",
            trigger_time=trigger_time,
            content_type=caption.content_type or "story",
            scene_id=scene.scene_id,
            scene_group=scene.group,
            excluded_scene_ids=sorted(explicit_exclusions),
            image_brief=caption.image_brief,
            caption=caption.caption,
            caption_formula=caption.caption_formula,
            hashtags=caption.hashtags,
            publishing_note=caption.publishing_note,
            monthly_checklist_fulfilled=caption.monthly_checklist_fulfilled,
            watch_used=caption.watch_used,
            shoes_used=caption.shoes_used,
        )
        self.session.add(plan)
        self.session.flush()
        return plan

    def _assert_can_run(self) -> None:
        today = local_today()
        if is_sunday(today):
            raise PlannerSkip("Sunday is a silent day for Elise.")
        counter = self._daily_counter(today)
        if counter.story_count >= self.settings.story_daily_target:
            raise PlannerSkip(f"Daily story target reached ({counter.story_count}/{self.settings.story_daily_target}).")

    def _daily_counter(self, day) -> DailyCounter:
        counter = self.session.get(DailyCounter, day)
        if counter:
            return counter
        counter = DailyCounter(local_date=day, timezone=self.settings.tz, story_count=0)
        self.session.add(counter)
        self.session.flush()
        return counter

    def _select_scene(self, trigger_time: TriggerTime, explicit_exclusions: set[str]) -> ScenePrompt:
        recent_scene_ids = self._recent_scene_ids()
        hard_exclusions = set(explicit_exclusions)
        candidates = self._candidate_scenes(trigger_time, hard_exclusions | recent_scene_ids)
        if not candidates:
            logger.warning("No candidates after recent-scene filter; retrying without recent-scene exclusions.")
            candidates = self._candidate_scenes(trigger_time, hard_exclusions)
        if not candidates:
            raise RuntimeError("No scene candidates available after explicit exclusions.")

        focus = self._next_pending_focus()
        focused = self._rank_by_focus(candidates, focus)
        if focused:
            return focused[0]
        return self._deterministic_pick(candidates, trigger_time, hard_exclusions)

    def _candidate_scenes(self, trigger_time: TriggerTime, exclusions: set[str]) -> list[ScenePrompt]:
        groups = TRIGGER_GROUPS[trigger_time]
        return (
            self.session.query(ScenePrompt)
            .filter(ScenePrompt.group.in_(groups))
            .filter(~ScenePrompt.scene_id.in_(list(exclusions)) if exclusions else True)
            .order_by(ScenePrompt.scene_id.asc())
            .all()
        )

    def _recent_scene_ids(self) -> set[str]:
        cutoff = utc_now() - timedelta(days=14)
        rows = (
            self.session.query(ContentPlan.scene_id)
            .filter(ContentPlan.status == "published")
            .filter(ContentPlan.created_at >= cutoff)
            .order_by(desc(ContentPlan.created_at))
            .limit(14)
            .all()
        )
        return {row[0] for row in rows}

    def _next_pending_focus(self) -> str | None:
        item = (
            self.session.query(MonthlyChecklistItem)
            .filter(MonthlyChecklistItem.status == "pending")
            .order_by(MonthlyChecklistItem.item_id.asc())
            .first()
        )
        return item.item_id if item else None

    def _monthly_focus_for_scene(self, scene: ScenePrompt) -> str | None:
        focus = self._next_pending_focus()
        if not focus:
            return None
        score = self._focus_score(scene, focus)
        return focus if score > 0 else None

    def _rank_by_focus(self, candidates: list[ScenePrompt], focus: str | None) -> list[ScenePrompt]:
        if not focus:
            return []
        scored = [(self._focus_score(scene, focus), scene) for scene in candidates]
        return [scene for score, scene in sorted(scored, key=lambda item: (-item[0], item[1].scene_id)) if score > 0]

    def _focus_score(self, scene: ScenePrompt, focus: str) -> int:
        keywords = CHECKLIST_KEYWORDS.get(focus, ())
        haystack = f"{scene.prompt} {scene.kohya_caption} {scene.filename}".lower()
        return sum(1 for keyword in keywords if keyword in haystack)

    def _deterministic_pick(
        self,
        candidates: list[ScenePrompt],
        trigger_time: TriggerTime,
        hard_exclusions: set[str],
    ) -> ScenePrompt:
        seed = f"{local_today().isoformat()}:{trigger_time}:{','.join(sorted(hard_exclusions))}"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        index = int(digest[:8], 16) % len(candidates)
        return candidates[index]

    def _recent_captions(self) -> list[str]:
        rows = (
            self.session.query(ContentPlan.caption)
            .filter(ContentPlan.caption.isnot(None))
            .order_by(desc(ContentPlan.created_at))
            .limit(10)
            .all()
        )
        return [row[0] for row in rows]

    def _new_plan_id(self, trigger_time: TriggerTime) -> str:
        stamp = utc_now().strftime("%Y%m%d_%H%M%S")
        suffix = uuid4().hex[:8]
        return f"plan_{stamp}_{trigger_time}_{suffix}"
