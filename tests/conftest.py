import os
from unittest.mock import MagicMock

import pytest


# Segredos determinísticos para os testes (definidos antes de importar o app;
# load_dotenv não sobrescreve variáveis já presentes no ambiente).
os.environ.setdefault("JWT_SECRET", "test_jwt_secret")
os.environ.setdefault("PASSWORD_SALT", "test_salt")

import app as app_module


@pytest.fixture
def application():
    app = app_module.create_app()
    app.config["TESTING"] = True
    # Conexão de banco mockada: os testes de integração injetam cursores.
    app.db_conn = MagicMock()
    return app


@pytest.fixture
def client(application):
    return application.test_client()


@pytest.fixture
def set_cursor(application):
    """Fábrica que injeta um cursor mockado com retornos controlados."""

    def _set(fetchone=None, fetchall=None):
        cursor = MagicMock()
        cursor.fetchone.return_value = fetchone
        cursor.fetchall.return_value = fetchall or []
        application.db_conn.cursor.return_value.__enter__.return_value = cursor
        return cursor

    return _set
