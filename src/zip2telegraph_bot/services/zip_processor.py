from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from zip2telegraph_bot.errors import UserVisibleError
from zip2telegraph_bot.models import PreparedImage, PreparedJob
from zip2telegraph_bot.utils.naming import build_page_title, sanitize_stem
from zip2telegraph_bot.utils.sorting import natural_sort_key


SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
CONVERT_TO_PNG_SUFFIXES = {".webp", ".bmp", ".tif", ".tiff"}


class ZipProcessor:
    def __init__(
        self,
        image_max_size_bytes: int,
        extracted_max_total_bytes: int,
        zip_max_size_bytes: int,
    ) -> None:
        self._image_max_size_bytes = image_max_size_bytes
        self._extracted_max_total_bytes = extracted_max_total_bytes
        self._zip_max_size_bytes = zip_max_size_bytes

    def prepare(self, zip_path: Path, workspace: Path, title_date: str) -> PreparedJob:
        if zip_path.stat().st_size >= self._zip_max_size_bytes:
            raise UserVisibleError("ERR_ZIP_TOO_LARGE", "ZIP 文件超过限制")

        extract_dir = workspace / "images"
        extract_dir.mkdir(parents=True, exist_ok=True)

        images: list[PreparedImage] = []
        total_uncompressed = 0

        with zipfile.ZipFile(zip_path) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                suffix = Path(info.filename).suffix.lower()
                if suffix not in SUPPORTED_IMAGE_SUFFIXES:
                    continue
                if info.file_size > self._image_max_size_bytes:
                    raise UserVisibleError("ERR_IMAGE_TOO_LARGE", f"图片过大: {Path(info.filename).name}")
                total_uncompressed += info.file_size
                if total_uncompressed > self._extracted_max_total_bytes:
                    raise UserVisibleError("ERR_EXTRACTED_SIZE_EXCEEDED", "解压总大小超过限制")

                destination = self._safe_destination(extract_dir, info.filename)
                destination.parent.mkdir(parents=True, exist_ok=True)

                with archive.open(info) as src, destination.open("wb") as dst:
                    shutil.copyfileobj(src, dst)

                prepared_path = self._normalize_image(destination)
                images.append(
                    PreparedImage(
                        original_name=Path(info.filename).name,
                        path=prepared_path,
                        size_bytes=prepared_path.stat().st_size,
                    )
                )

        if not images:
            raise UserVisibleError("ERR_EMPTY_ZIP", "ZIP 中没有可用图片")

        images.sort(key=lambda item: natural_sort_key(item.original_name))
        title = build_page_title(zip_path.stem, title_date)
        return PreparedJob(title=title, images=images)

    def _safe_destination(self, root: Path, archive_name: str) -> Path:
        cleaned_parts = [sanitize_stem(part) for part in Path(archive_name).parts if part not in {"", ".", ".."}]
        if not cleaned_parts:
            raise UserVisibleError("ERR_INVALID_ZIP_ENTRY", "ZIP 中存在非法文件路径")
        destination = root.joinpath(*cleaned_parts)
        resolved = destination.resolve()
        root_resolved = root.resolve()
        if root_resolved not in resolved.parents and resolved != root_resolved:
            raise UserVisibleError("ERR_INVALID_ZIP_ENTRY", "ZIP 中存在非法文件路径")
        return resolved

    def _normalize_image(self, path: Path) -> Path:
        suffix = path.suffix.lower()
        try:
            with Image.open(path) as image:
                image.verify()
        except (UnidentifiedImageError, OSError) as exc:
            raise UserVisibleError("ERR_INVALID_IMAGE", f"无效图片: {path.name}") from exc

        if suffix not in CONVERT_TO_PNG_SUFFIXES:
            return path

        converted = path.with_suffix(".png")
        with Image.open(path) as image:
            image.save(converted, format="PNG")
        path.unlink()
        return converted
