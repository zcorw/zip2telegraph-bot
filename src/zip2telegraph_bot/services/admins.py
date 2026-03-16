from __future__ import annotations

from aiogram import Bot


class AdminService:
    async def is_group_admin(self, bot: Bot, chat_id: int, user_id: int) -> bool:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in {"creator", "administrator"}

