from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from zip2telegraph_bot.db import Database


@dataclass(slots=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int


class RateLimiter:
    def __init__(
        self,
        db: Database,
        chat_window_seconds: int,
        chat_max_calls: int,
        user_window_seconds: int,
        user_max_calls: int,
    ) -> None:
        self._db = db
        self._chat_window_seconds = chat_window_seconds
        self._chat_max_calls = chat_max_calls
        self._user_window_seconds = user_window_seconds
        self._user_max_calls = user_max_calls

    async def check(self, now: datetime, chat_id: int, user_id: int) -> RateLimitDecision:
        chat_decision = await self._check_scope(
            now=now,
            scope="chat",
            scope_id=chat_id,
            window_seconds=self._chat_window_seconds,
            max_calls=self._chat_max_calls,
        )
        if not chat_decision.allowed:
            return chat_decision

        return await self._check_scope(
            now=now,
            scope="user",
            scope_id=user_id,
            window_seconds=self._user_window_seconds,
            max_calls=self._user_max_calls,
        )

    async def consume(self, now: datetime, chat_id: int, user_id: int) -> None:
        timestamp = now.isoformat()
        await self._db.add_rate_limit_event("chat", chat_id, timestamp)
        await self._db.add_rate_limit_event("user", user_id, timestamp)
        prune_before = (now - timedelta(seconds=max(self._chat_window_seconds, self._user_window_seconds) * 2)).isoformat()
        await self._db.prune_rate_limit_events(prune_before)

    async def _check_scope(
        self,
        now: datetime,
        scope: str,
        scope_id: int,
        window_seconds: int,
        max_calls: int,
    ) -> RateLimitDecision:
        created_after = (now - timedelta(seconds=window_seconds)).isoformat()
        count = await self._db.count_rate_limit_events(scope, scope_id, created_after)
        if count < max_calls:
            return RateLimitDecision(allowed=True, retry_after_seconds=0)

        latest = await self._db.latest_rate_limit_event(scope, scope_id)
        if latest is None:
            return RateLimitDecision(allowed=False, retry_after_seconds=window_seconds)

        latest_dt = datetime.fromisoformat(latest)
        retry_after = int((latest_dt + timedelta(seconds=window_seconds) - now).total_seconds())
        return RateLimitDecision(allowed=False, retry_after_seconds=max(retry_after, 1))

