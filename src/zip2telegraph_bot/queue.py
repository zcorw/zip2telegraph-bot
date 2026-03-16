from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from zip2telegraph_bot.models import JobRequest


logger = logging.getLogger(__name__)


class ChatJobManager:
    def __init__(self, processor: Callable[[JobRequest], Awaitable[None]]) -> None:
        self._processor = processor
        self._queues: dict[int, asyncio.Queue[JobRequest]] = {}
        self._workers: dict[int, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()

    async def enqueue(self, job: JobRequest) -> int:
        async with self._lock:
            queue = self._queues.get(job.chat_id)
            if queue is None:
                queue = asyncio.Queue()
                self._queues[job.chat_id] = queue
            await queue.put(job)
            if job.chat_id not in self._workers:
                self._workers[job.chat_id] = asyncio.create_task(self._run_chat_worker(job.chat_id))
            return queue.qsize()

    async def shutdown(self) -> None:
        workers = list(self._workers.values())
        for worker in workers:
            worker.cancel()
        if workers:
            await asyncio.gather(*workers, return_exceptions=True)

    async def _run_chat_worker(self, chat_id: int) -> None:
        queue = self._queues[chat_id]
        try:
            while True:
                job = await queue.get()
                try:
                    await self._processor(job)
                except Exception:
                    logger.exception("chat worker failed", extra={"chat_id": chat_id, "task_id": job.task_id})
                finally:
                    queue.task_done()
                async with self._lock:
                    if queue.empty():
                        self._queues.pop(chat_id, None)
                        self._workers.pop(chat_id, None)
                        return
        except asyncio.CancelledError:
            raise
