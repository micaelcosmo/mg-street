import jwt

import repositories.users as users_mod


def _admin(application):
    return jwt.encode({"id": 1, "role": "admin"}, application.config["JWT_SECRET"], algorithm="HS256")


def _user(application):
    return jwt.encode({"id": 2, "role": "user"}, application.config["JWT_SECRET"], algorithm="HS256")


def test_login_missing_fields(client):
    assert client.post("/api/login", json={}).status_code == 400


def test_checkout_invalid_items(client, application):
    h = {"Authorization": f"Bearer {_user(application)}"}
    assert client.post("/api/checkout", json={"items": "nope"}, headers=h).status_code == 400


def test_register_duplicate_email_rejected(client, monkeypatch):
    def boom(*args, **kwargs):
        raise Exception("duplicate email")

    monkeypatch.setattr(users_mod, "create", boom)
    resp = client.post("/api/register", json={"name": "X", "email": "a@b.com", "password": "segredo"})
    assert resp.status_code == 400


def test_orders_requires_admin(client, application):
    h = {"Authorization": f"Bearer {_user(application)}"}
    assert client.get("/api/orders", headers=h).status_code == 403


def test_orders_stats_requires_admin(client, application):
    h = {"Authorization": f"Bearer {_user(application)}"}
    assert client.get("/api/orders/stats", headers=h).status_code == 403


def test_orders_stats_returns_totals(client, application, set_cursor):
    set_cursor(fetchone=(3, 150.0))
    resp = client.get("/api/orders/stats", headers={"Authorization": f"Bearer {_admin(application)}"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total_orders"] == 3
    assert data["total_revenue"] == 150.0


def test_preview_token_returns_token(client, application, set_cursor):
    set_cursor(fetchone=(2, "Cliente Demo", "cliente@mgstreet.com", "user"))
    resp = client.get("/api/preview_token", headers={"Authorization": f"Bearer {_admin(application)}"})
    assert resp.status_code == 200
    assert "token" in resp.get_json()


def test_preview_token_requires_admin(client, application):
    h = {"Authorization": f"Bearer {_user(application)}"}
    assert client.get("/api/preview_token", headers=h).status_code == 403


def test_update_product_requires_token(client):
    assert client.put("/api/products/1", json={"name": "X", "price": 10}).status_code == 401


def test_list_products_empty(client, application, set_cursor):
    set_cursor(fetchall=[])
    resp = client.get("/api/products", headers={"Authorization": f"Bearer {_user(application)}"})
    assert resp.status_code == 200
    assert resp.get_json()["products"] == []
