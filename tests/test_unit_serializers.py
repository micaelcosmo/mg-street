from app import serialize_orders, serialize_products


def test_serialize_products_full_row():
    rows = [(1, "Camiseta", "desc", 49.9, "http://img", "camisetas", {"Cor": ["Preto"]}, 10)]
    out = serialize_products(rows)
    assert out[0]["name"] == "Camiseta"
    assert out[0]["price"] == 49.9
    assert out[0]["options"] == {"Cor": ["Preto"]}
    assert out[0]["stock"] == 10


def test_serialize_products_short_row_defaults():
    rows = [(1, "X", None, 10.0, "", "cat")]  # sem options/stock
    out = serialize_products(rows)
    assert out[0]["options"] == {}
    assert out[0]["stock"] is None


def test_serialize_products_empty():
    assert serialize_products([]) == []


def test_serialize_orders_with_status():
    rows = [(7, 2, 100.0, None, "paid", [{"name": "X", "quantity": 1}])]
    out = serialize_orders(rows)
    assert out[0]["id"] == 7
    assert out[0]["status"] == "paid"
    assert len(out[0]["items"]) == 1


def test_serialize_orders_legacy_row_defaults_pending():
    rows = [(7, 2, 100.0, None, [{"name": "X"}])]  # 5 colunas (legado)
    out = serialize_orders(rows)
    assert out[0]["status"] == "pending"
    assert len(out[0]["items"]) == 1
