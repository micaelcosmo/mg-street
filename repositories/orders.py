def create_with_items(conn, user_id, items, total):
    """Cria um pedido e seus itens de forma atômica; retorna o order_id.

    Os itens entram em `order_items` como snapshot (product_name/unit_price).
    A conexão usa autocommit; aqui ele é desligado só durante a transação.
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
                    "INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (
                        order_id,
                        item.get("id"),
                        item.get("name", ""),
                        float(item.get("price", 0) or 0),
                        int(item.get("quantity", 1) or 1),
                    ),
                )
        conn.commit()
        return order_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.autocommit = True


def list_with_items(conn):
    """Retorna linhas (id, user_id, total, created_at, items) com itens agregados."""
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT o.id, o.user_id, o.total, o.created_at, "
            "COALESCE(json_agg(json_build_object("
            "'product_id', oi.product_id, 'name', oi.product_name, "
            "'unit_price', oi.unit_price, 'quantity', oi.quantity)) "
            "FILTER (WHERE oi.id IS NOT NULL), '[]') AS items "
            "FROM orders o LEFT JOIN order_items oi ON oi.order_id = o.id "
            "GROUP BY o.id ORDER BY o.created_at DESC"
        )
        return cursor.fetchall()


def stats(conn):
    """Retorna (total_orders, total_revenue)."""
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(1), COALESCE(SUM(total),0) FROM orders")
        return cursor.fetchone()
