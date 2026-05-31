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
    email = f"e2e_{uuid.uuid4().hex[:8]}@test.local"
    password = "e2e-pass"
    order_id = None
    try:
        # 1. registra e loga um comprador novo
        registro = live_client.post(
            "/api/register",
            json={"name": "E2E Buyer", "email": email, "password": password},
        )
        assert registro.status_code == 201

        login = live_client.post(
            "/api/login", json={"email": email, "password": password}
        )
        assert login.status_code == 200
        auth = {"Authorization": f"Bearer {login.get_json()['token']}"}

        # 2. lista o catalogo (o seed garante produtos)
        catalogo = live_client.get("/api/products", headers=auth)
        assert catalogo.status_code == 200
        produtos = catalogo.get_json()["products"]
        assert len(produtos) >= 1
        produto = produtos[0]

        # 3. checkout cria o pedido (orders + order_items, atomico)
        checkout = live_client.post(
            "/api/checkout",
            headers=auth,
            json={
                "items": [
                    {
                        "id": produto["id"],
                        "name": produto["name"],
                        "price": produto["price"],
                        "quantity": 2,
                    }
                ]
            },
        )
        assert checkout.status_code == 201
        order_id = checkout.get_json()["order_id"]

        # 4. admin ve o pedido com os itens agregados (json_agg)
        admin_auth = {"Authorization": f"Bearer {_admin_token(live_app)}"}
        pedidos = live_client.get("/api/orders", headers=admin_auth)
        assert pedidos.status_code == 200
        criado = next((o for o in pedidos.get_json()["orders"] if o["id"] == order_id), None)
        assert criado is not None
        assert len(criado["items"]) == 1
        item = criado["items"][0]
        assert item["name"] == produto["name"]
        assert item["quantity"] == 2
        assert criado["total"] == pytest.approx(produto["price"] * 2, abs=0.01)

        # 5. stats refletem ao menos este pedido
        stats = live_client.get("/api/orders/stats", headers=admin_auth)
        assert stats.status_code == 200
        assert stats.get_json()["total_orders"] >= 1

        # 6. estoque deu baixa (2 unidades) no checkout
        if produto.get("stock") is not None:
            recat = live_client.get("/api/products", headers=auth)
            atual = next((p for p in recat.get_json()["products"] if p["id"] == produto["id"]), None)
            assert atual is not None
            assert atual["stock"] == produto["stock"] - 2

        # 7. "meus pedidos" lista o pedido do comprador
        meus = live_client.get("/api/orders/me", headers=auth)
        assert meus.status_code == 200
        assert any(o["id"] == order_id for o in meus.get_json()["orders"])

        # 8. carrinho persiste no servidor (PUT -> GET)
        salvar = live_client.put(
            "/api/cart",
            headers=auth,
            json={"items": [{"id": produto["id"], "name": produto["name"], "price": produto["price"], "quantity": 1}]},
        )
        assert salvar.status_code == 200
        ler = live_client.get("/api/cart", headers=auth)
        assert ler.status_code == 200
        assert len(ler.get_json()["items"]) == 1
    finally:
        # limpeza: remove o pedido (cascade nos itens) e o usuario de teste
        with live_app.db_conn.cursor() as cursor:
            if order_id is not None:
                cursor.execute("DELETE FROM orders WHERE id = %s", (order_id,))
            cursor.execute("DELETE FROM users WHERE email = %s", (email,))
        live_app.db_conn.commit()
