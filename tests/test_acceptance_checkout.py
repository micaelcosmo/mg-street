import os
import uuid

import jwt
import pytest


pytestmark = pytest.mark.skipif(
    not os.getenv("MGSTREET_DB_TESTS"),
    reason="Jornada E2E exige Postgres ativo (defina MGSTREET_DB_TESTS=1).",
)


@pytest.fixture
def live_app():
    """App com conexao REAL ao Postgres (so quando MGSTREET_DB_TESTS=1)."""
    import app as app_module

    application = app_module.create_app()
    app_module.init_db_connection(application)
    app_module.initialize_database(application)
    application.config["TESTING"] = True
    return application


@pytest.fixture
def live_client(live_app):
    return live_app.test_client()


def _admin_token(application):
    # Token admin emitido direto (evita depender da senha do seed).
    return jwt.encode(
        {"id": 0, "role": "admin"},
        application.config["JWT_SECRET"],
        algorithm="HS256",
    )


def test_customer_purchase_journey(live_app, live_client):
    """Jornada completa, AUTOSSUFICIENTE: cria o próprio produto (não mexe no seed),
    compra, valida estoque/pedido/meus-pedidos/carrinho e limpa tudo no fim — pode
    rodar repetidamente (inclusive a cada refresh do /tests/report)."""
    email = f"e2e_{uuid.uuid4().hex[:8]}@test.local"
    password = "e2e-pass"
    admin_auth = {"Authorization": f"Bearer {_admin_token(live_app)}"}
    order_id = None
    product_id = None
    try:
        # 1. admin cria um produto dedicado (estoque conhecido)
        novo = live_client.post(
            "/api/products",
            headers=admin_auth,
            json={"name": f"E2E Prod {uuid.uuid4().hex[:6]}", "price": 50.0, "stock": 50},
        )
        assert novo.status_code == 201
        product_id = novo.get_json()["id"]

        # 2. registra e loga um comprador novo
        assert live_client.post(
            "/api/register", json={"name": "E2E Buyer", "email": email, "password": password}
        ).status_code == 201
        login = live_client.post("/api/login", json={"email": email, "password": password})
        assert login.status_code == 200
        auth = {"Authorization": f"Bearer {login.get_json()['token']}"}

        # 3. checkout (2 unidades) cria pedido + itens (atômico)
        checkout = live_client.post(
            "/api/checkout",
            headers=auth,
            json={"items": [{"id": product_id, "name": "E2E Prod", "price": 50.0, "quantity": 2}]},
        )
        assert checkout.status_code == 201
        order_id = checkout.get_json()["order_id"]

        # 4. admin vê o pedido com os itens agregados
        pedidos = live_client.get("/api/orders", headers=admin_auth)
        assert pedidos.status_code == 200
        criado = next((o for o in pedidos.get_json()["orders"] if o["id"] == order_id), None)
        assert criado is not None
        assert len(criado["items"]) == 1
        assert criado["items"][0]["quantity"] == 2
        assert criado["total"] == pytest.approx(100.0, abs=0.01)

        # 5. stats refletem o pedido
        assert live_client.get("/api/orders/stats", headers=admin_auth).get_json()["total_orders"] >= 1

        # 6. estoque deu baixa: 50 -> 48
        recat = live_client.get("/api/products", headers=auth).get_json()["products"]
        atual = next((p for p in recat if p["id"] == product_id), None)
        assert atual is not None and atual["stock"] == 48

        # 7. "meus pedidos" lista o pedido do comprador
        meus = live_client.get("/api/orders/me", headers=auth)
        assert meus.status_code == 200
        assert any(o["id"] == order_id for o in meus.get_json()["orders"])

        # 8. carrinho persiste no servidor (PUT -> GET)
        assert live_client.put(
            "/api/cart",
            headers=auth,
            json={"items": [{"id": product_id, "name": "E2E Prod", "price": 50.0, "quantity": 1}]},
        ).status_code == 200
        ler = live_client.get("/api/cart", headers=auth)
        assert ler.status_code == 200 and len(ler.get_json()["items"]) == 1
    finally:
        # limpeza total: pedido (cascade nos itens), usuário (cascade no carrinho) e produto
        with live_app.db_conn.cursor() as cursor:
            if order_id is not None:
                cursor.execute("DELETE FROM orders WHERE id = %s", (order_id,))
            cursor.execute("DELETE FROM users WHERE email = %s", (email,))
            if product_id is not None:
                cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
        live_app.db_conn.commit()
