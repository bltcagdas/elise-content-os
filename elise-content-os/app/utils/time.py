from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app.config import get_settings


def app_timezone() -> ZoneInfo:
    return ZoneInfo(get_settings().tz)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def local_now() -> datetime:
    return utc_now().astimezone(app_timezone())


def local_today() -> date:
    return local_now().date()


def is_sunday(day: date | None = None) -> bool:
    current = day or local_today()
    return current.weekday() == 6

