import logging
from typing import Any

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import ContentPlan, DailyCounter, MonthlyChecklistItem, PublishEvent
from app.schemas import CallbackAction, TelegramCallbackResult
from app.services.planner import PlannerService
from app.services.telegram import TelegramService
from app.utils.time import local_today

logger = logging.getLogger(__name__)


class MemoryService:
    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        planner_service: PlannerService | None = None,
        telegram_service: TelegramService | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.planner_service = planner_service or PlannerService(session, self.settings)
        self.telegram_service = telegram_service or TelegramService(self.settings)

    def handle_callback(
        self,
        *,
        action: CallbackAction,
        plan_id: str,
        callback_event_id: str | None,
        payload: dict[str, Any],
        dry_run: bool = False,
        send_telegram: bool = True,
    ) -> TelegramCallbackResult:
        duplicate = self._existing_event(callback_event_id)
        if duplicate:
            return TelegramCallbackResult(status="duplicate", plan_id=plan_id, action=action)

        plan = self.session.get(ContentPlan, plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")

        if plan.status != "pending":
            return TelegramCallbackResult(status="already_processed", plan_id=plan.id, action=action)

        if action == "published":
            plan.status = "published"
            self._record_event(plan, action, callback_event_id, payload)
            self._increment_story_counter(plan)
            self._update_monthly_checklist(plan)
            self.session.commit()
            return TelegramCallbackResult(status="published", plan_id=plan.id, action=action)

        if action == "skipped":
            plan.status = "skipped"
            self._record_event(plan, action, callback_event_id, payload)
            self.session.commit()
            return TelegramCallbackResult(status="skipped", plan_id=plan.id, action=action)

        if action == "regenerate":
            excluded = sorted(set(plan.excluded_scene_ids or []) | {plan.scene_id})
            plan.excluded_scene_ids = excluded
            plan.status = "regenerate_requested"
            self._record_event(plan, action, callback_event_id, payload)
            new_plan = self.planner_service.create_plan(
                plan.trigger_time,
                excluded_scene_ids=excluded,
                parent_plan_id=plan.id,
                dry_run=dry_run,
            )
            self.session.commit()
            if send_telegram and not dry_run:
                try:
                    self.telegram_service.send_content_notification(new_plan)
                except Exception as exc:
                    logger.exception("Telegram notification for regenerated plan failed: %s", exc)
            return TelegramCallbackResult(
                status="regenerated",
                plan_id=plan.id,
                action=action,
                new_plan_id=new_plan.id,
            )

        raise ValueError(f"Unsupported callback action: {action}")

    def _existing_event(self, callback_event_id: str | None) -> PublishEvent | None:
        if not callback_event_id:
            return None
        return (
            self.session.query(PublishEvent)
            .filter(PublishEvent.callback_event_id == callback_event_id)
            .one_or_none()
        )

    def _record_event(
        self,
        plan: ContentPlan,
        action: str,
        callback_event_id: str | None,
        payload: dict[str, Any],
    ) -> None:
        self.session.add(
            PublishEvent(
                plan_id=plan.id,
                action=action,
                callback_event_id=callback_event_id,
                payload=payload,
            )
        )

    def _increment_story_counter(self, plan: ContentPlan) -> None:
        day = local_today()
        counter = self.session.get(DailyCounter, day)
        if not counter:
            counter = DailyCounter(local_date=day, timezone=self.settings.tz, story_count=0)
            self.session.add(counter)
        counter.story_count += 1

    def _update_monthly_checklist(self, plan: ContentPlan) -> None:
        item_id = plan.monthly_checklist_fulfilled
        if not item_id:
            return
        item = (
            self.session.query(MonthlyChecklistItem)
            .filter(MonthlyChecklistItem.item_id == item_id)
            .filter(MonthlyChecklistItem.status == "pending")
            .order_by(MonthlyChecklistItem.month.desc())
            .first()
        )
        if not item:
            return
        item.completed_count += 1
        if item.completed_count >= item.target_count:
            item.status = "completed"
            item.completed_date = local_today()
