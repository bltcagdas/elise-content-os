from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models import MonthlyChecklistItem, ScenePrompt, utc_now
from app.services.knowledge import KnowledgeLoader


class SeedService:
    def __init__(self, session: Session, loader: KnowledgeLoader | None = None) -> None:
        self.session = session
        self.loader = loader or KnowledgeLoader()

    def seed_all(self) -> dict[str, int]:
        scene_count = self.seed_scenes()
        checklist_count = self.seed_monthly_checklist()
        self.session.commit()
        return {"scene_prompts": scene_count, "monthly_checklist_items": checklist_count}

    def seed_scenes(self) -> int:
        count = 0
        for record in self.loader.load_scene_records():
            if not record["prompt"] or not record["kohya_caption"]:
                continue
            existing = self.session.get(ScenePrompt, record["scene_id"])
            if existing:
                existing.filename = record["filename"]
                existing.group = record["group"]
                existing.shot = record["shot"]
                existing.prompt = record["prompt"]
                existing.kohya_caption = record["kohya_caption"]
                existing.source = record["source"]
                existing.updated_at = utc_now()
            else:
                self.session.add(ScenePrompt(**record))
            count += 1
        return count

    def seed_monthly_checklist(self) -> int:
        month, checklist = self.loader.load_monthly_checklist()
        count = 0
        for item in checklist:
            item_id = str(item["id"])
            existing = (
                self.session.query(MonthlyChecklistItem)
                .filter(
                    MonthlyChecklistItem.month == month,
                    MonthlyChecklistItem.item_id == item_id,
                )
                .one_or_none()
            )
            payload = self._normalize_item(month, item)
            if existing:
                existing.item = payload["item"]
                existing.status = payload["status"]
                existing.completed_count = payload["completed_count"]
                existing.target_count = payload["target_count"]
                existing.completed_date = payload["completed_date"]
                existing.raw = payload["raw"]
                existing.updated_at = utc_now()
            else:
                self.session.add(MonthlyChecklistItem(**payload))
            count += 1
        return count

    def _normalize_item(self, month: str, item: dict[str, Any]) -> dict[str, Any]:
        target_count = int(item.get("target_count") or 1)
        completed_count = int(item.get("completed_count") or (1 if item.get("status") == "completed" else 0))
        completed_date = self._parse_date(item.get("completed_date"))
        return {
            "month": month,
            "item_id": str(item["id"]),
            "item": str(item.get("item") or item["id"]),
            "status": str(item.get("status") or "pending"),
            "completed_count": completed_count,
            "target_count": target_count,
            "completed_date": completed_date,
            "raw": item,
        }

    def _parse_date(self, value: Any) -> date | None:
        if not value:
            return None
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value))
