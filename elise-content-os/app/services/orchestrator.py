import logging
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.schemas import TriggerResult, TriggerTime
from app.services.planner import PlannerService, PlannerSkip
from app.services.telegram import TelegramService

logger = logging.getLogger(__name__)


class TriggerOrchestrator:
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

    def run_trigger(self, trigger_time: TriggerTime, *, dry_run: bool = False) -> TriggerResult:
        trigger_id = f"trigger_{uuid4().hex[:12]}"
        try:
            plan = self.planner_service.create_plan(trigger_time, dry_run=dry_run)
            self.session.commit()
        except PlannerSkip as exc:
            self.session.rollback()
            logger.info(
                "trigger_skipped",
                extra={"trigger_id": trigger_id, "status": "skipped", "error_type": "skip_rule"},
            )
            return TriggerResult(status="skipped", reason=exc.reason)
        except Exception as exc:
            self.session.rollback()
            error_type = self._error_type(exc)
            logger.exception(
                "trigger_failed",
                extra={"trigger_id": trigger_id, "status": "failed", "error_type": error_type},
            )
            self._best_effort_admin_alert(
                "Content OS trigger failed",
                f"trigger_id={trigger_id}\ntrigger_time={trigger_time}\nerror_type={error_type}\nerror={exc}",
            )
            raise

        sent = False
        if not dry_run:
            try:
                self.telegram_service.send_content_notification(plan)
                sent = True
            except Exception as exc:
                logger.exception(
                    "telegram_send_failed",
                    extra={
                        "trigger_id": trigger_id,
                        "plan_id": plan.id,
                        "scene_id": plan.scene_id,
                        "status": "failed",
                        "error_type": "telegram_failure",
                    },
                )
        logger.info(
            "trigger_completed",
            extra={
                "trigger_id": trigger_id,
                "plan_id": plan.id,
                "scene_id": plan.scene_id,
                "status": "planned",
            },
        )
        return TriggerResult(
            status="planned",
            plan_id=plan.id,
            scene_id=plan.scene_id,
            sent_to_telegram=sent,
        )

    def _best_effort_admin_alert(self, title: str, body: str) -> None:
        try:
            self.telegram_service.send_admin_alert(title, body)
        except Exception:
            logger.warning("admin_alert_failed", extra={"error_type": "telegram_failure", "status": "failed"})

    def _error_type(self, exc: Exception) -> str:
        module = exc.__class__.__module__.lower()
        name = exc.__class__.__name__.lower()
        if "openai" in module or "captiongeneration" in name:
            return "openai_failure"
        if "sqlalchemy" in module or "psycopg" in module:
            return "db_failure"
        return exc.__class__.__name__
