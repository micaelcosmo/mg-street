def get_credentials_by_email(conn, email):
    """Retorna (id, password_hash, role) do usuário, ou None se não existir."""
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT id, password_hash, role FROM users WHERE email = %s",
            (email,),
        )
        return cursor.fetchone()


def get_by_email(conn, email):
    """Retorna (id, name, email, role) do usuário, ou None se não existir."""
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT id, name, email, role FROM users WHERE email = %s",
            (email,),
        )
        return cursor.fetchone()


def create(conn, name, email, password_hash, role="user"):
    """Insere um usuário. Pode levantar exceção em caso de email duplicado."""
    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
            (name, email, password_hash, role),
        )
    conn.commit()
