"""The bot's notion of "today"."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo


def today(timezone: ZoneInfo, now: datetime | None = None) -> date:
    """The current date in the bot's time zone. `now` (timezone-aware) is for tests."""
    return (now or datetime.now(UTC)).astimezone(timezone).date()
