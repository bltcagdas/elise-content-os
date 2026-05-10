from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.internal import router as internal_router
from app.api.telegram import router as telegram_router
from app.config import get_settings
from app.db import get_session
from app.logging_config import configure_logging

configure_logging()

app = FastAPI(title="Elise Verne Content OS", version="0.1.0")
app.include_router(internal_router)
app.include_router(telegram_router)


@app.get("/healthz")
def healthz(session: Session = Depends(get_session)):
    settings = get_settings()
    try:
        session.execute(text("select 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc
    return {"status": "ok", "timezone": settings.tz, "model": settings.openai_model}
