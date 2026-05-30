import json


def get_items(conn, user_id):
    """Retorna a lista de itens do carrinho do usuário (vazia se não houver)."""
    with conn.cursor() as cursor:
        cursor.execute("SELECT items FROM carts WHERE user_id = %s", (user_id,))
        row = cursor.fetchone()
    return row[0] if row and row[0] is not None else []


def save_items(conn, user_id, items):
    """Salva (upsert) o carrinho do usuário."""
    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO carts (user_id, items, updated_at) VALUES (%s, %s, now()) "
            "ON CONFLICT (user_id) DO UPDATE SET items = EXCLUDED.items, updated_at = now()",
            (user_id, json.dumps(items)),
        )
    conn.commit()
