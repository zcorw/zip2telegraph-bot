from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo


PUBLIC_BOT_API_DOWNLOAD_LIMIT_BYTES = 20 * 1024 * 1024


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return int(value)


@dataclass(slots=True)
class Settings:
    bot_token: str
    telegraph_access_token: str | None
    telegraph_short_name: str
    telegraph_author_name: str
    telegraph_author_url: str | None
    telegraph_api_url: str
    telegraph_upload_url: str
    telegram_api_base: str | None
    telegram_local_mode: bool
    timezone: ZoneInfo
    data_dir: Path
    tmp_dir: Path
    log_level: str
    chat_rate_limit_window_seconds: int
    chat_rate_limit_max_calls: int
    user_rate_limit_window_seconds: int
    user_rate_limit_max_calls: int
    zip_max_size_bytes: int
    image_max_size_bytes: int
    extracted_max_total_bytes: int
    task_timeout_seconds: int

    @property
    def database_path(self) -> Path:
        return self.data_dir / "app.db"

    @property
    def transport_zip_limit_bytes(self) -> int:
        if self.telegram_local_mode:
            return self.zip_max_size_bytes
        return min(self.zip_max_size_bytes, PUBLIC_BOT_API_DOWNLOAD_LIMIT_BYTES)


def load_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is required")

    data_dir = Path(os.getenv("DATA_DIR", "./data")).resolve()
    tmp_dir = Path(os.getenv("TMP_DIR", "./tmp")).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    telegraph_access_token = os.getenv("TELEGRAPH_ACCESS_TOKEN", "").strip() or None
    telegraph_author_url = os.getenv("TELEGRAPH_AUTHOR_URL", "").strip() or None
    telegram_api_base = os.getenv("TELEGRAM_API_BASE", "").strip() or None

    return Settings(
        bot_token=bot_token,
        telegraph_access_token=telegraph_access_token,
        telegraph_short_name=os.getenv("TELEGRAPH_SHORT_NAME", "zip2telegraph").strip(),
        telegraph_author_name=os.getenv("TELEGRAPH_AUTHOR_NAME", "zip2telegraph-bot").strip(),
        telegraph_author_url=telegraph_author_url,
        telegraph_api_url=os.getenv("TELEGRAPH_API_URL", "https://api.telegra.ph").rstrip("/"),
        telegraph_upload_url=os.getenv("TELEGRAPH_UPLOAD_URL", "https://telegra.ph/upload").rstrip("/"),
        telegram_api_base=telegram_api_base,
        telegram_local_mode=_env_bool("TELEGRAM_LOCAL_MODE", False),
        timezone=ZoneInfo(os.getenv("TIMEZONE", "Asia/Tokyo")),
        data_dir=data_dir,
        tmp_dir=tmp_dir,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        chat_rate_limit_window_seconds=_env_int("CHAT_RATE_LIMIT_WINDOW_SECONDS", 300),
        chat_rate_limit_max_calls=_env_int("CHAT_RATE_LIMIT_MAX_CALLS", 1),
        user_rate_limit_window_seconds=_env_int("USER_RATE_LIMIT_WINDOW_SECONDS", 3600),
        user_rate_limit_max_calls=_env_int("USER_RATE_LIMIT_MAX_CALLS", 3),
        zip_max_size_bytes=_env_int("ZIP_MAX_SIZE_BYTES", 1_073_741_824),
        image_max_size_bytes=_env_int("IMAGE_MAX_SIZE_BYTES", 10_485_760),
        extracted_max_total_bytes=_env_int("EXTRACTED_MAX_TOTAL_BYTES", 2_147_483_648),
        task_timeout_seconds=_env_int("TASK_TIMEOUT_SECONDS", 1_200),
    )

