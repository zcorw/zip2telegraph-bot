from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aiogram import Bot
from aiogram.types import Document


@dataclass(slots=True)
class JobRequest:
    task_id: str
    bot: Bot
    chat_id: int
    user_id: int
    reply_to_message_id: int
    document: Document


@dataclass(slots=True)
class PreparedImage:
    original_name: str
    path: Path
    size_bytes: int


@dataclass(slots=True)
class PreparedJob:
    title: str
    images: list[PreparedImage]

