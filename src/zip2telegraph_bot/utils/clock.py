from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


def now_in_timezone(timezone: ZoneInfo) -> datetime:
    return datetime.now(tz=timezone)

