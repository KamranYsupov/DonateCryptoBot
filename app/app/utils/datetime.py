from datetime import date, timedelta, datetime, UTC

from app.core.config import settings


def to_main_tz(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    return dt.astimezone(settings.timezone_info)


def get_start_of_week(day: date | None = None) -> date:
    day = day or to_main_tz(datetime.now()).date()
    return day - timedelta(days=day.weekday())


