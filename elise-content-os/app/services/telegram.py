import html
import logging
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.models import ContentPlan

logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def send_content_notification(self, plan: ContentPlan) -> dict[str, Any]:
        token, chat_id = self.settings.require_telegram()
        payload = {
            "chat_id": chat_id,
            "text": self._message_text(plan),
            "parse_mode": "HTML",
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {"text": "Paylaştım", "callback_data": f"published:{plan.id}"},
                        {"text": "Paylaşmadım", "callback_data": f"skipped:{plan.id}"},
                    ],
                    [{"text": "Farklı fikir üret", "callback_data": f"regenerate:{plan.id}"}],
                ]
            },
        }
        return self._post(token, "sendMessage", payload)

    def send_admin_alert(self, title: str, body: str) -> dict[str, Any]:
        token, chat_id = self.settings.require_telegram()
        payload = {
            "chat_id": chat_id,
            "text": f"<b>{html.escape(title)}</b>\n\n{html.escape(body)}",
            "parse_mode": "HTML",
        }
        return self._post(token, "sendMessage", payload)

    def answer_callback(self, callback_query_id: str, text: str) -> dict[str, Any]:
        token, _ = self.settings.require_telegram()
        return self._post(token, "answerCallbackQuery", {"callback_query_id": callback_query_id, "text": text})

    def edit_callback_message(self, chat_id: int | str, message_id: int, text: str) -> dict[str, Any]:
        token, _ = self.settings.require_telegram()
        return self._post(
            token,
            "editMessageText",
            {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": html.escape(text),
                "parse_mode": "HTML",
            },
        )

    def _post(self, token: str, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"https://api.telegram.org/bot{token}/{method}"
        with httpx.Client(timeout=20.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            if not data.get("ok"):
                raise RuntimeError(f"Telegram API error for {method}: {data}")
            return data

    def _message_text(self, plan: ContentPlan) -> str:
        brief = self._truncate(plan.image_brief, 2400)
        hashtags = " ".join(plan.hashtags or [])
        return (
            f"<b>{html.escape(plan.trigger_time.upper())} ICERIGI HAZIR</b>\n\n"
            f"<b>Sahne:</b> {html.escape(plan.scene_id)} - {html.escape(plan.scene_group)}\n"
            f"<b>Plan:</b> {html.escape(plan.id)}\n\n"
            f"<b>GORSEL BRIEF</b>\n{html.escape(brief)}\n\n"
            f"<b>CAPTION</b>\n{html.escape(plan.caption)}\n\n"
            f"<b>HASHTAGS</b>\n{html.escape(hashtags)}\n\n"
            f"<b>NOT</b>\n{html.escape(plan.publishing_note)}"
            f"\n\n<b>VISUAL QC CHECKLIST</b>\n{html.escape(self._visual_qc_checklist())}"
        )

    def _truncate(self, value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        return value[: limit - 20].rstrip() + "\n[truncated]"

    def _visual_qc_checklist(self) -> str:
        return "\n".join(
            [
                "- face consistency",
                "- realistic skin texture",
                "- left-eye freckle detail",
                "- right-corner micro-smirk",
                "- no over-smoothed AI skin",
                "- correct watch/shoes",
                "- correct scene distance freckle rule",
            ]
        )
