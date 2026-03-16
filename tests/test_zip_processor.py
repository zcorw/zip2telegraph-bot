import zipfile
from pathlib import Path

import pytest
from PIL import Image

from zip2telegraph_bot.errors import UserVisibleError
from zip2telegraph_bot.services.zip_processor import ZipProcessor


def _write_png(path: Path) -> None:
    image = Image.new("RGB", (10, 10), color="red")
    image.save(path, format="PNG")


def test_zip_processor_extracts_and_sorts_images(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    _write_png(source_dir / "10.png")
    _write_png(source_dir / "2.png")

    archive_path = tmp_path / "images.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.write(source_dir / "10.png", arcname="10.png")
        archive.write(source_dir / "2.png", arcname="2.png")
        archive.writestr("note.txt", "ignored")

    processor = ZipProcessor(
        image_max_size_bytes=10_000_000,
        extracted_max_total_bytes=20_000_000,
        zip_max_size_bytes=20_000_000,
    )

    prepared = processor.prepare(archive_path, tmp_path / "workspace", "2026-03-16")
    assert [image.original_name for image in prepared.images] == ["2.png", "10.png"]
    assert prepared.title == "images - 2026-03-16"


def test_zip_processor_fails_on_invalid_image(tmp_path: Path) -> None:
    archive_path = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("bad.png", b"not-an-image")

    processor = ZipProcessor(
        image_max_size_bytes=10_000_000,
        extracted_max_total_bytes=20_000_000,
        zip_max_size_bytes=20_000_000,
    )

    with pytest.raises(UserVisibleError) as exc_info:
        processor.prepare(archive_path, tmp_path / "workspace", "2026-03-16")

    assert exc_info.value.code == "ERR_INVALID_IMAGE"
