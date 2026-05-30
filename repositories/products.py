import json


def list_all(conn):
    """Retorna (id, name, description, price, image_url, category_name, options, stock)."""
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT p.id, p.name, p.description, p.price, p.image_url, c.name, p.options, p.stock "
            "FROM products p LEFT JOIN categories c ON p.category_id = c.id "
            "ORDER BY p.id DESC"
        )
        return cursor.fetchall()


def create(conn, name, description, price, image_url, category_id, options=None, stock=0):
    """Insere um produto (com opções e estoque) e retorna o id criado."""
    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO products (name, description, price, image_url, category_id, options, stock) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (name, description, price, image_url, category_id, json.dumps(options or {}), int(stock or 0)),
        )
        product_id = cursor.fetchone()[0]
    conn.commit()
    return product_id


def update(conn, product_id, name, description, price, image_url, category_id, options=None, stock=0):
    """Atualiza um produto; retorna o id ou None se não existir."""
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE products SET name=%s, description=%s, price=%s, image_url=%s, "
            "category_id=%s, options=%s, stock=%s WHERE id=%s RETURNING id",
            (name, description, price, image_url, category_id, json.dumps(options or {}), int(stock or 0), product_id),
        )
        row = cursor.fetchone()
    if row:
        conn.commit()
    return row[0] if row else None


def delete(conn, product_id):
    """Remove um produto; retorna o id removido ou None se não existia."""
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM products WHERE id = %s RETURNING id", (product_id,))
        row = cursor.fetchone()
    if row:
        conn.commit()
    return row[0] if row else None
