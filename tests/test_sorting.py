from zip2telegraph_bot.utils.sorting import natural_sort_key


def test_natural_sort_orders_numeric_suffixes() -> None:
    values = ["10.png", "2.png", "1.png"]
    assert sorted(values, key=natural_sort_key) == ["1.png", "2.png", "10.png"]

