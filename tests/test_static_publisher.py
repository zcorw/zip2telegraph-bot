from pathlib import Path

from zip2telegraph_bot.models import PreparedImage
from zip2telegraph_bot.services.static_publisher import StaticImagePublisher


def test_static_publisher_copies_files_and_builds_urls(tmp_path: Path) -> None:
    public_dir = tmp_path / "public"
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    source_path = source_dir / "page 1.png"
    source_path.write_bytes(b"png-data")

    publisher = StaticImagePublisher(
        public_image_dir=public_dir,
        public_image_base_url="https://img.example.com/zip2telegraph",
    )

    urls = publisher.publish(
        "task123",
        [
            PreparedImage(
                original_name="page 1.png",
                path=source_path,
                size_bytes=source_path.stat().st_size,
            )
        ],
    )

    assert urls == ["https://img.example.com/zip2telegraph/task123/0001-page_1.png"]
    assert (public_dir / "task123" / "0001-page_1.png").read_bytes() == b"png-data"

