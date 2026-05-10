from fastapi import Header, HTTPException, status

from app.config import get_settings


def require_internal_token(x_internal_trigger_token: str | None = Header(default=None)) -> None:
    expected = get_settings().internal_trigger_token
    if not x_internal_trigger_token or x_internal_trigger_token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal trigger token")


def require_telegram_secret(x_telegram_bot_api_secret_token: str | None = Header(default=None)) -> None:
    expected = get_settings().telegram_webhook_secret
    if not x_telegram_bot_api_secret_token or x_telegram_bot_api_secret_token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Telegram webhook secret")

