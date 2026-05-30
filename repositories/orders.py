import json


def create_with_items(conn, user_id, items, total):
    """Cria um pedido e seus itens de forma atômica; retorna o order_id.

    Os itens entram em `order_items` como snapshot (product_name/unit_price e as
    opções escolhidas). A conexão usa autocommit; aqui ele é desligado só na transação.
    """
    conn.autocommit = False
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO orders (user_id, total) VALUES (%s, %s) RETURNING id",
                (user_id, total),
            )
            order_id = cursor.fetchone()[0]
            for item in items:
                cursor.execute(
                    "INSERT INTO order_items "
                    "(order_id, product_id, product_name, unit_price, quantity, selected_options) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (
                        order_id,
                        item.get("id"),
                        item.get("name", ""),
                        float(item.get("price", 0) or 0),
                        int(item.get("quantity", 1) or 1),
                        json.dumps(item.get("options") or {}),
                    ),
                )
        conn.commit()
        return order_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.autocommit = True


def list_with_items(conn, user_id=None):
    """Retorna linhas (id, user_id, total, created_at, items) com itens agregados.

    Se `user_id` for informado, filtra apenas os pedidos daquele usuário.
    """
    where = "WHERE o.user_id = %s " if user_id is not None else ""
    params = (user_id,) if user_id is not None else ()
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT o.id, o.user_id, o.total, o.created_at, "
            "COALESCE(json_agg(json_build_object("
            "'product_id', oi.product_id, 'name', oi.product_name, "
            "'unit_price', oi.unit_price, 'quantity', oi.quantity, "
            "'options', oi.selected_options)) "
            "FILTER (WHERE oi.id IS NOT NULL), '[]') AS items "
            "FROM orders o LEFT JOIN order_items oi ON oi.order_id = o.id "
            + where
            + "GROUP BY o.id ORDER BY o.created_at DESC",
            params,
        )
        return cursor.fetchall()


def stats(conn):
    """Retorna (total_orders, total_revenue)."""
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(1), COALESCE(SUM(total),0) FROM orders")
        return cursor.fetchone()
