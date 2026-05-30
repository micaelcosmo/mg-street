import jwt

from app import hash_password


def test_ping(client):
    resp = client.get("/ping")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_products_require_token(client):
    resp = client.get("/api/products")
    assert resp.status_code == 401


def test_create_product_requires_admin(client, application):
    token = jwt.encode(
        {"id": 1, "role": "user"},
        application.config["JWT_SECRET"],
        algorithm="HS256",
    )
    resp = client.post(
        "/api/products",
        json={"name": "Camiseta", "price": 10},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_login_success_returns_token_with_exp(client, application, set_cursor):
    password_hash = hash_password("minhasenha")
    set_cursor(fetchone=(1, password_hash, "admin"))
    resp = client.post("/api/login", json={"email": "a@b.com", "password": "minhasenha"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "token" in data
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
