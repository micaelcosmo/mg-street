"""Entrada WSGI para produção (ex.: gunicorn wsgi:app).

Diferente do dev server (`python app.py`), aqui inicializamos a conexão e o schema
explicitamente, pois o bloco `__main__` de `app.py` não roda sob gunicorn.
"""
from app import app, init_db_connection, initialize_database


init_db_connection(app)
initialize_database(app)
