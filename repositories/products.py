import json


def search(conn, q=None, limit=None, offset=0):
    """Lista produtos, opcionalmente filtrando por nome (q) e paginando (limit/offset)."""
    where = ""
    params = []
    if q:
        where = "WHERE p.name ILIKE %s "
        params.append("%" + q + "%")
    sql = (
        "SELECT p.id, p.name, p.description, p.price, p.image_url, c.name, p.options, p.stock "
        "FROM products p LEFT JOIN categories c ON p.category_id = c.id "
        + where
        + "ORDER BY p.id DESC"
    )
    if limit is not None:
        sql += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])
    with conn.cursor() as cursor:
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()


def list_all(conn):
    """Atalho: todos os produtos (sem filtro/paginação)."""
    return search(conn)


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
