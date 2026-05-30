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


def test_landing_page_is_public(client):
    # A vitrine inicial abre sem login.
    assert client.get("/").status_code == 200


def test_login_page_served(client):
    assert client.get("/login").status_code == 200


def test_public_products_no_auth(client, set_cursor):
    set_cursor(fetchall=[(1, "Camiseta", "algodao", 49.9, "", "camisetas")])
    resp = client.get("/api/public/products")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["products"]) == 1
    assert data["products"][0]["name"] == "Camiseta"


def test_register_page_served(client):
    assert client.get("/register").status_code == 200


def test_register_creates_user(client, set_cursor):
    set_cursor()  # create() só executa INSERT + commit, sem fetch
    resp = client.post(
        "/api/register",
        json={"name": "Novo", "email": "novo@x.com", "password": "segredo"},
    )
    assert resp.status_code == 201


def test_register_incomplete_is_rejected(client):
    resp = client.post("/api/register", json={"email": "x@y.com"})
    assert resp.status_code == 400


def test_register_invalid_email_is_rejected(client):
    resp = client.post(
        "/api/register",
        json={"name": "X", "email": "naoeemail", "password": "segredo"},
    )
    assert resp.status_code == 400


def test_register_short_password_is_rejected(client):
    resp = client.post(
        "/api/register",
        json={"name": "X", "email": "x@y.com", "password": "12"},
    )
    assert resp.status_code == 400


def test_register_rate_limited(client, application):
    application.register_limiter = RateLimiter(max_attempts=1, window_seconds=60)
    body = {"name": "A", "email": "a@b.com", "password": "segredo"}
    assert client.post("/api/register", json=body).status_code in (201, 400)
    assert client.post("/api/register", json=body).status_code == 429


def test_checkout_rate_limited(client, application, set_cursor):
    application.checkout_limiter = RateLimiter(max_attempts=1, window_seconds=60)
    set_cursor(fetchone=(10,))
    token = jwt.encode({"id": 1, "role": "user"}, application.config["JWT_SECRET"], algorithm="HS256")
    headers = {"Authorization": f"Bearer {token}"}
    body = {"items": [{"id": 1, "name": "X", "price": 10, "quantity": 1}]}
    assert client.post("/api/checkout", json=body, headers=headers).status_code == 201
    assert client.post("/api/checkout", json=body, headers=headers).status_code == 429


def test_upload_requires_admin(client, application):
    token = jwt.encode({"id": 1, "role": "user"}, application.config["JWT_SECRET"], algorithm="HS256")
    resp = client.post("/api/upload", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_upload_without_file_is_rejected(client, application):
    token = jwt.encode({"id": 1, "role": "admin"}, application.config["JWT_SECRET"], algorithm="HS256")
    resp = client.post("/api/upload", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


def test_upload_bad_extension_is_rejected(client, application):
    import io
    token = jwt.encode({"id": 1, "role": "admin"}, application.config["JWT_SECRET"], algorithm="HS256")
    resp = client.post(
        "/api/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"file": (io.BytesIO(b"x"), "evil.txt")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_cart_requires_token(client):
    assert client.get("/api/cart").status_code == 401


def test_save_cart(client, application, set_cursor):
    set_cursor()
    token = jwt.encode({"id": 2, "role": "user"}, application.config["JWT_SECRET"], algorithm="HS256")
    resp = client.put(
        "/api/cart",
        json={"items": [{"id": 1, "name": "Camiseta", "price": 49.9, "quantity": 1}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


def test_save_cart_invalid_items(client, application):
    token = jwt.encode({"id": 2, "role": "user"}, application.config["JWT_SECRET"], algorithm="HS256")
    resp = client.put("/api/cart", json={"items": "nope"}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


def test_get_cart_returns_items(client, application, set_cursor):
    set_cursor(fetchone=([{"id": 1, "name": "Camiseta", "quantity": 2}],))
    token = jwt.encode({"id": 2, "role": "user"}, application.config["JWT_SECRET"], algorithm="HS256")
    resp = client.get("/api/cart", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.get_json()["items"]) == 1


def test_my_orders_requires_token(client):
    assert client.get("/api/orders/me").status_code == 401


def test_my_orders_returns_user_orders(client, application, set_cursor):
    set_cursor(fetchall=[(1, 2, 99.8, None, [{"name": "Camiseta", "quantity": 2}])])
    token = jwt.encode(
        {"id": 2, "role": "user"},
        application.config["JWT_SECRET"],
        algorithm="HS256",
    )
    resp = client.get("/api/orders/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["orders"]) == 1
    assert data["orders"][0]["id"] == 1
