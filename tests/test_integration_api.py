import jwt

from app import hash_password
from ratelimit import RateLimiter


def test_ping(client):
    resp = client.get("/ping")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_login_success_returns_token_with_exp(client, application, set_cursor):
    password_hash = hash_password("minhasenha")
    set_cursor(fetchone=(1, password_hash, "admin"))
    resp = client.post("/api/login", json={"email": "a@b.com", "password": "minhasenha"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "token" in data
    assert data["role"] == "admin"  # role explicito na resposta (frontend nao parseia JWT)
    payload = jwt.decode(
        data["token"], application.config["JWT_SECRET"], algorithms=["HS256"]
    )
    assert payload["role"] == "admin"
    assert "exp" in payload


def test_login_invalid_credentials(client, application, set_cursor):
    password_hash = hash_password("correta")
    set_cursor(fetchone=(1, password_hash, "user"))
    resp = client.post("/api/login", json={"email": "a@b.com", "password": "errada"})
    assert resp.status_code == 401


def test_login_rate_limited_after_too_many_attempts(client, application, set_cursor):
    # limiter pequeno e deterministico para o teste
    application.login_limiter = RateLimiter(max_attempts=2, window_seconds=60)
    set_cursor(fetchone=None)  # credencial sempre invalida -> 401, mas conta no limiter
    assert client.post("/api/login", json={"email": "a@b.com", "password": "x"}).status_code == 401
    assert client.post("/api/login", json={"email": "a@b.com", "password": "x"}).status_code == 401
    # terceira tentativa excede o limite
    assert client.post("/api/login", json={"email": "a@b.com", "password": "x"}).status_code == 429


def test_checkout_empty_cart_is_rejected(client, application):
    token = jwt.encode(
        {"id": 1, "role": "user"},
        application.config["JWT_SECRET"],
        algorithm="HS256",
    )
    resp = client.post(
        "/api/checkout",
        json={"items": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_checkout_creates_order(client, application, set_cursor):
    # fetchone -> id do pedido recém-inserido.
    set_cursor(fetchone=(10,))
    token = jwt.encode(
        {"id": 1, "role": "user"},
        application.config["JWT_SECRET"],
        algorithm="HS256",
    )
    resp = client.post(
        "/api/checkout",
        json={"items": [{"id": 1, "name": "Camiseta", "price": 49.9, "quantity": 2}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.get_json()["order_id"] == 10
