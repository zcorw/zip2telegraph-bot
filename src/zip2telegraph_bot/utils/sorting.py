from __future__ import annotations

import re
from typing import Any


TOKEN_RE = re.compile(r"(\d+)")


def natural_sort_key(value: str) -> list[Any]:
    parts = TOKEN_RE.split(value.lower())
    result: list[Any] = []
    for part in parts:
        if part.isdigit():
            result.append(int(part))
        elif part:
            result.append(part)
    return result

