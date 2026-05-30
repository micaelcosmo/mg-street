def resolve_id(conn, name):
    """Retorna o id da categoria pelo nome, criando-a se necessário; None se vazio."""
    if not name:
        return None
    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO categories (name) VALUES (%s) ON CONFLICT (name) DO NOTHING;",
            (name,),
        )
        cursor.execute("SELECT id FROM categories WHERE name = %s", (name,))
        row = cursor.fetchone()
    return row[0] if row else None
