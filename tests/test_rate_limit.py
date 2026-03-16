from datetime import datetime
from pathlib import Path

import pytest

from zip2telegraph_bot.db import Database
from zip2telegraph_bot.services.rate_limit import RateLimiter


@pytest.mark.asyncio
async def test_rate_limit_blocks_after_threshold(tmp_path: Path) -> None:
    db = Database(str(tmp_path / "test.db"))
    await db.connect()

    limiter = RateLimiter(
        db=db,
        chat_window_seconds=300,
        chat_max_calls=1,
        user_window_seconds=3600,
        user_max_calls=3,
    )

    now = datetime.fromisoformat("2026-03-16T12:00:00+09:00")
    first = await limiter.check(now, chat_id=1, user_id=2)
    assert first.allowed is True

    await limiter.consume(now, chat_id=1, user_id=2)

    second = await limiter.check(now, chat_id=1, user_id=2)
    assert second.allowed is False
    assert second.retry_after_seconds > 0

