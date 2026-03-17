from __future__ import annotations

import shutil
from pathlib import Path
from urllib.parse import quote

from zip2telegraph_bot.models import PreparedImage
from zip2telegraph_bot.utils.naming import sanitize_stem


class StaticImagePublisher:
    def __init__(self, public_image_dir: Path, public_image_base_url: str) -> None:
        self._public_image_dir = public_image_dir
        self._public_image_base_url = public_image_base_url.rstrip("/")

    def publish(self, task_id: str, images: list[PreparedImage]) -> list[str]:
        task_dir = self._public_image_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        published_urls: list[str] = []
        for index, image in enumerate(images, start=1):
            suffix = image.path.suffix.lower() or ".bin"
            stem = sanitize_stem(Path(image.original_name).stem).replace(" ", "_")
            target_name = f"{index:04d}-{stem}{suffix}"
            target_path = task_dir / target_name
            shutil.copy2(image.path, target_path)
            published_urls.append(f"{self._public_image_base_url}/{quote(task_id)}/{quote(target_name)}")

        return published_urls
