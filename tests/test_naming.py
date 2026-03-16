from zip2telegraph_bot.utils.naming import build_page_title


def test_build_page_title_normalizes_filename() -> None:
    assert build_page_title("My_zip-file", "2026-03-16") == "My zip file - 2026-03-16"

