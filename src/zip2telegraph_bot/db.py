from __future__ import annotations

import aiosqlite


SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  chat_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  file_name TEXT NOT NULL,
  status TEXT NOT NULL,
  page_url TEXT,
  error_code TEXT,
  error_message TEXT,
  created_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS rate_limit_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scope TEXT NOT NULL,
  scope_id INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rate_limit_scope_created
  ON rate_limit_events(scope, scope_id, created_at);
"""


class Database:
    def __init__(self, path: str) -> None:
        self._path = path

    async def connect(self) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.executescript(SCHEMA)
            await db.commit()

    async def create_task(self, task_id: str, chat_id: int, user_id: int, file_name: str, created_at: str) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                """
                INSERT INTO tasks(id, chat_id, user_id, file_name, status, created_at)
                VALUES(?, ?, ?, ?, 'queued', ?)
                """,
                (task_id, chat_id, user_id, file_name, created_at),
            )
            await db.commit()

    async def mark_task_running(self, task_id: str, started_at: str) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "UPDATE tasks SET status = 'running', started_at = ? WHERE id = ?",
                (started_at, task_id),
            )
            await db.commit()

    async def mark_task_succeeded(self, task_id: str, page_url: str, finished_at: str) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                """
                UPDATE tasks
                SET status = 'succeeded', page_url = ?, finished_at = ?
                WHERE id = ?
                """,
                (page_url, finished_at, task_id),
            )
            await db.commit()

    async def mark_task_failed(
        self,
        task_id: str,
        error_code: str,
        error_message: str,
        finished_at: str,
    ) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                """
                UPDATE tasks
                SET status = 'failed', error_code = ?, error_message = ?, finished_at = ?
                WHERE id = ?
                """,
                (error_code, error_message, finished_at, task_id),
            )
            await db.commit()

    async def add_rate_limit_event(self, scope: str, scope_id: int, created_at: str) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "INSERT INTO rate_limit_events(scope, scope_id, created_at) VALUES(?, ?, ?)",
                (scope, scope_id, created_at),
            )
            await db.commit()

    async def count_rate_limit_events(self, scope: str, scope_id: int, created_after: str) -> int:
        async with aiosqlite.connect(self._path) as db:
            async with db.execute(
                """
                SELECT COUNT(1)
                FROM rate_limit_events
                WHERE scope = ? AND scope_id = ? AND created_at >= ?
                """,
                (scope, scope_id, created_after),
            ) as cursor:
                row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def latest_rate_limit_event(self, scope: str, scope_id: int) -> str | None:
        async with aiosqlite.connect(self._path) as db:
            async with db.execute(
                """
                SELECT created_at
                FROM rate_limit_events
                WHERE scope = ? AND scope_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (scope, scope_id),
            ) as cursor:
                row = await cursor.fetchone()
        return None if row is None else str(row[0])

    async def prune_rate_limit_events(self, created_before: str) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "DELETE FROM rate_limit_events WHERE created_at < ?",
                (created_before,),
            )
            await db.commit()

