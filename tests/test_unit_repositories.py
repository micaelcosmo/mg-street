from unittest.mock import MagicMock

import pytest

from repositories import categories, orders, products, users


def _conn(fetchone=None, fetchall=None):
    """Conexão mockada: cursor de contexto com retornos controlados."""
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = fetchone
    cursor.fetchall.return_value = fetchall or []
    conn.cursor.return_value.__enter__.return_value = cursor
    return conn


# ---- categories ----

def test_resolve_id_empty_returns_none():
    assert categories.resolve_id(_conn(), None) is None
    assert categories.resolve_id(_conn(), "") is None


def test_resolve_id_returns_existing_id():
    assert categories.resolve_id(_conn(fetchone=(5,)), "camisetas") == 5


# ---- users ----

def test_get_credentials_by_email_returns_row():
    row = (1, "hash", "admin")
    assert users.get_credentials_by_email(_conn(fetchone=row), "a@b.com") == row


def test_get_credentials_by_email_missing_returns_none():
    assert users.get_credentials_by_email(_conn(fetchone=None), "x@y.com") is None


def test_get_by_email_returns_row():
    row = (2, "Cliente Demo", "cliente@mgstreet.com", "user")
    assert users.get_by_email(_conn(fetchone=row), "cliente@mgstreet.com") == row


# ---- products ----

def test_list_all_returns_rows():
    rows = [(1, "Camiseta", "desc", 49.9, "", "camisetas")]
    assert products.list_all(_conn(fetchall=rows)) == rows


def test_create_returns_new_id():
    assert products.create(_conn(fetchone=(9,)), "Camiseta", "d", 49.9, "", None) == 9


def test_create_with_options_returns_id():
    assert products.create(_conn(fetchone=(9,)), "Camiseta", "d", 49.9, "", None, {"Cor": ["Preto"]}) == 9


def test_update_existing_returns_id():
    assert products.update(_conn(fetchone=(5,)), 5, "n", "d", 10, "", None, {}) == 5


def test_update_missing_returns_none():
    assert products.update(_conn(fetchone=None), 999, "n", "d", 10, "", None, {}) is None


def test_delete_existing_returns_id():
    assert products.delete(_conn(fetchone=(1,)), 1) == 1


def test_delete_missing_returns_none():
    assert products.delete(_conn(fetchone=None), 999) is None


# ---- orders ----

def test_stats_returns_count_and_revenue():
    assert orders.stats(_conn(fetchone=(3, 99.5))) == (3, 99.5)


def test_create_with_items_returns_order_id_and_restores_autocommit():
    conn = _conn(fetchone=(10,))
    order_id = orders.create_with_items(
        conn,
        user_id=1,
        items=[{"id": 1, "name": "Camiseta", "price": 49.9, "quantity": 2}],
        total=99.8,
    )
    assert order_id == 10
    conn.commit.assert_called_once()
    assert conn.autocommit is True  # religado no finally


def test_create_with_items_out_of_stock_raises_and_rolls_back():
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = (10,)  # id do pedido
    cursor.rowcount = 0  # UPDATE de estoque não afetou linhas -> sem saldo
    conn.cursor.return_value.__enter__.return_value = cursor
    with pytest.raises(orders.OutOfStockError):
        orders.create_with_items(conn, 1, [{"id": 1, "name": "Camiseta", "price": 10, "quantity": 5}], 50)
    conn.rollback.assert_called_once()
    assert conn.autocommit is True


def test_create_with_items_rolls_back_on_error():
    conn = MagicMock()
    cursor = MagicMock()
    cursor.execute.side_effect = Exception("boom")
    conn.cursor.return_value.__enter__.return_value = cursor
    with pytest.raises(Exception):
        orders.create_with_items(conn, 1, [{"id": 1}], 10)
    conn.rollback.assert_called_once()
    assert conn.autocommit is True  # religado no finally mesmo no erro
