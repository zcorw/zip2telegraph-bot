from __future__ import annotations

import asyncio
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ChatType
from aiogram.types import Message

from zip2telegraph_bot.config import Settings, load_settings
from zip2telegraph_bot.db import Database
from zip2telegraph_bot.errors import UserVisibleError, format_user_error
from zip2telegraph_bot.logging import configure_logging
from zip2telegraph_bot.models import JobRequest
from zip2telegraph_bot.queue import ChatJobManager
from zip2telegraph_bot.services.admins import AdminService
from zip2telegraph_bot.services.rate_limit import RateLimiter
from zip2telegraph_bot.services.telegraph import TelegraphClient
from zip2telegraph_bot.services.zip_processor import ZipProcessor
from zip2telegraph_bot.utils.clock import now_in_timezone
from zip2telegraph_bot.utils.formatting import format_retry_after


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AppContext:
    settings: Settings
    db: Database
    admin_service: AdminService
    rate_limiter: RateLimiter
    zip_processor: ZipProcessor
    telegraph_client: TelegraphClient
    job_manager: ChatJobManager


def run() -> None:
    asyncio.run(_run())


async def _run() -> None:
    settings = load_settings()
    configure_logging(settings.log_level)
    await cleanup_stale_tmp(settings.tmp_dir)

    db = Database(str(settings.database_path))
    await db.connect()

    telegraph_client = TelegraphClient(
        api_url=settings.telegraph_api_url,
        upload_url=settings.telegraph_upload_url,
        short_name=settings.telegraph_short_name,
        author_name=settings.telegraph_author_name,
        author_url=settings.telegraph_author_url,
        access_token=settings.telegraph_access_token,
    )

    context = AppContext(
        settings=settings,
        db=db,
        admin_service=AdminService(),
        rate_limiter=RateLimiter(
            db=db,
            chat_window_seconds=settings.chat_rate_limit_window_seconds,
            chat_max_calls=settings.chat_rate_limit_max_calls,
            user_window_seconds=settings.user_rate_limit_window_seconds,
            user_max_calls=settings.user_rate_limit_max_calls,
        ),
        zip_processor=ZipProcessor(
            image_max_size_bytes=settings.image_max_size_bytes,
            extracted_max_total_bytes=settings.extracted_max_total_bytes,
            zip_max_size_bytes=settings.transport_zip_limit_bytes,
        ),
        telegraph_client=telegraph_client,
        job_manager=None,  # type: ignore[arg-type]
    )
    context.job_manager = ChatJobManager(lambda job: process_job(context, job))

    bot = Bot(token=settings.bot_token, session=build_session(settings))
    dp = Dispatcher()
    dp.include_router(build_router(context))

    try:
        await dp.start_polling(bot)
    finally:
        await context.job_manager.shutdown()
        await telegraph_client.close()
        await bot.session.close()


def build_session(settings: Settings) -> AiohttpSession:
    if not settings.telegram_api_base:
        return AiohttpSession()
    return AiohttpSession(
        api=TelegramAPIServer.from_base(
            settings.telegram_api_base,
            is_local=settings.telegram_local_mode,
        )
    )


def build_router(context: AppContext) -> Router:
    router = Router()

    @router.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}), F.document)
    async def handle_document(message: Message) -> None:
        if not message.from_user or not message.document:
            return

        if not message.document.file_name or not message.document.file_name.lower().endswith(".zip"):
            return

        is_admin = await context.admin_service.is_group_admin(
            bot=message.bot,
            chat_id=message.chat.id,
            user_id=message.from_user.id,
        )
        if not is_admin:
            await message.reply("处理失败: 只有群管理员可以上传 ZIP\n错误码: ERR_NOT_ADMIN")
            return

        document_size = message.document.file_size or 0
        if document_size > context.settings.transport_zip_limit_bytes:
            limit_mb = context.settings.transport_zip_limit_bytes // (1024 * 1024)
            await message.reply(
                f"处理失败: 当前 Telegram 下载链路限制为 {limit_mb}MB，请调整 ZIP 大小或切换本地 Bot API\n错误码: ERR_ZIP_TOO_LARGE"
            )
            return

        now = now_in_timezone(context.settings.timezone)
        decision = await context.rate_limiter.check(now, message.chat.id, message.from_user.id)
        if not decision.allowed:
            await message.reply(
                f"处理失败: 调用过于频繁，请稍后再试，剩余等待 {format_retry_after(decision.retry_after_seconds)}\n错误码: ERR_RATE_LIMITED"
            )
            return

        await context.rate_limiter.consume(now, message.chat.id, message.from_user.id)

        task_id = uuid4().hex
        await context.db.create_task(
            task_id=task_id,
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            file_name=message.document.file_name,
            created_at=now.isoformat(),
        )

        position = await context.job_manager.enqueue(
            JobRequest(
                task_id=task_id,
                bot=message.bot,
                chat_id=message.chat.id,
                user_id=message.from_user.id,
                reply_to_message_id=message.message_id,
                document=message.document,
            )
        )
        if position > 1:
            await message.reply(f"任务已进入队列，前方还有 {position - 1} 个任务。")
        else:
            await message.reply("任务已接收，开始处理。")

    return router


async def process_job(context: AppContext, job: JobRequest) -> None:
    now = now_in_timezone(context.settings.timezone)
    await context.db.mark_task_running(job.task_id, now.isoformat())

    workspace = context.settings.tmp_dir / job.task_id
    workspace.mkdir(parents=True, exist_ok=True)
    zip_path = workspace / (job.document.file_name or "upload.zip")

    try:
        await asyncio.wait_for(_process_job_inner(context, job, workspace, zip_path), timeout=context.settings.task_timeout_seconds)
    except asyncio.TimeoutError:
        error = UserVisibleError("ERR_TASK_TIMEOUT", "任务处理超时")
        await context.db.mark_task_failed(
            job.task_id,
            error.code,
            error.message,
            now_in_timezone(context.settings.timezone).isoformat(),
        )
        await job.bot.send_message(chat_id=job.chat_id, text=format_user_error(error), reply_to_message_id=job.reply_to_message_id)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


async def _process_job_inner(context: AppContext, job: JobRequest, workspace: Path, zip_path: Path) -> None:
    try:
        await job.bot.download(job.document, destination=zip_path)

        title_date = now_in_timezone(context.settings.timezone).strftime("%Y-%m-%d")
        prepared = context.zip_processor.prepare(zip_path=zip_path, workspace=workspace, title_date=title_date)

        image_urls: list[str] = []
        for image in prepared.images:
            image_urls.append(await context.telegraph_client.upload_image(image.path))

        page_url = await context.telegraph_client.create_page(prepared.title, image_urls)

        finished_at = now_in_timezone(context.settings.timezone).isoformat()
        await context.db.mark_task_succeeded(job.task_id, page_url, finished_at)
        await job.bot.send_message(chat_id=job.chat_id, text=page_url, reply_to_message_id=job.reply_to_message_id)
    except UserVisibleError as error:
        finished_at = now_in_timezone(context.settings.timezone).isoformat()
        await context.db.mark_task_failed(job.task_id, error.code, error.message, finished_at)
        await job.bot.send_message(chat_id=job.chat_id, text=format_user_error(error), reply_to_message_id=job.reply_to_message_id)


async def cleanup_stale_tmp(tmp_dir: Path) -> None:
    for path in tmp_dir.iterdir():
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)

