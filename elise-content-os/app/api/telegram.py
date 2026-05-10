import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import CallbackAction
from app.services.memory import MemoryService
from app.services.telegram import TelegramService
from app.utils.security import require_telegram_secret

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook", dependencies=[Depends(require_telegram_secret)])
async def telegram_webhook(request: Request, session: Session = Depends(get_session)) -> dict[str, Any]:
    update = await request.json()
    callback_query = update.get("callback_query")
    if not callback_query:
        return {"status": "ignored"}

    callback_id = callback_query.get("id")
    data = callback_query.get("data") or ""
    if ":" not in data:
        raise HTTPException(status_code=400, detail="Invalid callback data")

    action_raw, plan_id = data.split(":", 1)
    if action_raw not in {"published", "skipped", "regenerate"}:
        raise HTTPException(status_code=400, detail="Invalid callback action")
    action: CallbackAction = action_raw  # type: ignore[assignment]

    result = MemoryService(session).handle_callback(
        action=action,
        plan_id=plan_id,
        callback_event_id=callback_id,
        payload=update,
    )
    _best_effort_telegram_ack(callback_query, result.status)
    return result.model_dump()


def _best_effort_telegram_ack(callback_query: dict[str, Any], status: str) -> None:
    service = TelegramService()
    callback_id = callback_query.get("id")
    if callback_id:
        try:
            service.answer_callback(callback_id, f"Kaydedildi: {status}")
        except Exception as exc:
            logger.warning("Could not answer Telegram callback: %s", exc)

    message = callback_query.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    message_id = message.get("message_id")
    if chat_id and message_id:
        try:
            service.edit_callback_message(chat_id, message_id, f"Kaydedildi: {status}")
        except Exception as exc:
            logger.warning("Could not edit Telegram callback message: %s", exc)

