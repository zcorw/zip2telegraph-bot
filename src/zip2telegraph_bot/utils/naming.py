from __future__ import annotations

import re


INVALID_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._ -]+")
WHITESPACE_RE = re.compile(r"\s+")


def sanitize_stem(value: str) -> str:
    cleaned = INVALID_FILENAME_CHARS.sub("_", value).strip(" ._")
    return cleaned or "file"


def build_page_title(zip_stem: str, date_str: str) -> str:
    base = WHITESPACE_RE.sub(" ", zip_stem.replace("_", " ").replace("-", " ")).strip()
    base = base or "Untitled"
    return f"{base} - {date_str}"

