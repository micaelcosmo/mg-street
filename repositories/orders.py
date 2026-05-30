import json


class OutOfStockError(Exception):
    """Levantada quando não há estoque suficiente para um item do pedido."""


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
                product_id = item.get("id")
                quantity = int(item.get("quantity", 1) or 1)
                # Baixa de estoque atômica: só desce se houver saldo suficiente.
                if product_id is not None:
                    cursor.execute(
                        "UPDATE products SET stock = stock - %s WHERE id = %s AND stock >= %s",
                        (quantity, product_id, quantity),
                    )
                    if cursor.rowcount == 0:
                        raise OutOfStockError(item.get("name", "produto"))
                cursor.execute(
                    "INSERT INTO order_items "
                    "(order_id, product_id, product_name, unit_price, quantity, selected_options) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (
                        order_id,
                        product_id,
                        item.get("name", ""),
                        float(item.get("price", 0) or 0),
                        quantity,
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
            "SELECT o.id, o.user_id, o.total, o.created_at, o.status, "
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


def get_user_email(conn, order_id):
    """E-mail do dono do pedido (para confirmação); None se não houver."""
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT u.email FROM orders o JOIN users u ON u.id = o.user_id WHERE o.id = %s",
            (order_id,),
        )
        row = cursor.fetchone()
    return row[0] if row else None


def mark_paid(conn, order_id, payment_id):
    """Marca o pedido como pago e guarda o id do pagamento."""
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE orders SET status = 'paid', payment_id = %s WHERE id = %s",
            (payment_id, order_id),
        )
    conn.commit()


def stats(conn):
    """Retorna (total_orders, total_revenue)."""
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(1), COALESCE(SUM(total),0) FROM orders")
        return cursor.fetchone()
