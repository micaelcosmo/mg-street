from app import calculate_cart_total


def test_calculate_cart_total_sums_price_times_quantity():
    items = [{"price": 10, "quantity": 2}, {"price": 5.5, "quantity": 1}]
    assert calculate_cart_total(items) == 25.5


def test_calculate_cart_total_ignores_malformed_items():
    items = [{"price": "abc", "quantity": 1}, {"price": 10, "quantity": 2}]
    assert calculate_cart_total(items) == 20


def test_calculate_cart_total_empty():
    assert calculate_cart_total([]) == 0
