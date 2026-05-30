import jwt

import payments


def _token(application):
    return jwt.encode(
        {"id": 10, "role": "user"},
        application.config["JWT_SECRET"],
        algorithm="HS256",
    )


def _headers(application):
    return {"Authorization": f"Bearer {_token(application)}"}


def test_checkout_returns_init_point_when_enabled(client, application, set_cursor, monkeypatch):
    set_cursor(fetchone=(10,))
    monkeypatch.setattr(payments, "is_enabled", lambda: True)
    monkeypatch.setattr(
        payments,
        "create_preference",
        lambda order_id, items, base: {"init_point": "http://mp/checkout", "sandbox_init_point": "http://mp/sb", "preference_id": "p1"},
    )
    resp = client.post(
        "/api/checkout",
        json={"items": [{"id": 1, "name": "X", "price": 10, "quantity": 1}]},
        headers=_headers(application),
    )
    assert resp.status_code == 201
    assert resp.get_json()["init_point"] == "http://mp/checkout"


def test_checkout_fallback_when_disabled(client, application, set_cursor, monkeypatch):
    set_cursor(fetchone=(11,))
    monkeypatch.setattr(payments, "is_enabled", lambda: False)
    resp = client.post(
        "/api/checkout",
        json={"items": [{"id": 1, "name": "X", "price": 10, "quantity": 1}]},
        headers=_headers(application),
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["order_id"] == 11
    assert "init_point" not in data


def test_confirm_marks_order_paid(client, application, set_cursor, monkeypatch):
    set_cursor()  # mark_paid faz UPDATE, sem fetch
    monkeypatch.setattr(payments, "get_payment", lambda pid: {"status": "approved", "external_reference": "10", "id": pid})
    resp = client.post("/api/payments/confirm", json={"payment_id": "PAY1"}, headers=_headers(application))
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "paid"


def test_confirm_not_approved(client, application, monkeypatch):
    monkeypatch.setattr(payments, "get_payment", lambda pid: {"status": "rejected", "external_reference": "10", "id": pid})
    resp = client.post("/api/payments/confirm", json={"payment_id": "PAY1"}, headers=_headers(application))
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "rejected"


def test_confirm_requires_payment_id(client, application):
    resp = client.post("/api/payments/confirm", json={}, headers=_headers(application))
    assert resp.status_code == 400


def test_webhook_marks_paid(client, application, set_cursor, monkeypatch):
    set_cursor()
    monkeypatch.setattr(payments, "get_payment", lambda pid: {"status": "approved", "external_reference": "10", "id": pid})
    resp = client.post("/api/payments/webhook", json={"type": "payment", "data": {"id": "PAY999"}})
    assert resp.status_code == 200
