from __future__ import annotations


def format_retry_after(seconds: int) -> str:
    minutes, remain = divmod(max(seconds, 0), 60)
    hours, minutes = divmod(minutes, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours} 小时")
    if minutes:
        parts.append(f"{minutes} 分钟")
    if remain or not parts:
        parts.append(f"{remain} 秒")
    return "".join(parts)

