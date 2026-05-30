"""Integração de pagamento (Mercado Pago Checkout Pro).

Isola o SDK do Mercado Pago para manter as rotas finas e os testes mockáveis. O import
do SDK é lazy: se o pacote/credencial não existir, o pagamento fica desabilitado e o app
cai no fluxo atual (pedido sem pagamento) — sem quebrar dev/CI/container.
"""
import os


def _sdk():
    token = os.getenv("MP_ACCESS_TOKEN")
    if not token:
        return None
    try:
        import mercadopago
    except ImportError:
        return None
    return mercadopago.SDK(token)


def is_enabled():
    """Há credencial e SDK disponíveis para processar pagamento?"""
    return _sdk() is not None


def create_preference(order_id, items, base_url):
    """Cria uma preferência de Checkout Pro e retorna init_point/sandbox_init_point/id.

    `items`: lista de dicts do carrinho (name, price, quantity). Retorna None se desabilitado.
    """
    sdk = _sdk()
    if sdk is None:
        return None
    preference = {
        "items": [
            {
                "title": str(item.get("name", "Produto")),
                "quantity": int(item.get("quantity", 1) or 1),
                "unit_price": float(item.get("price", 0) or 0),
                "currency_id": "BRL",
            }
            for item in items
        ],
        "external_reference": str(order_id),
        "back_urls": {
            "success": f"{base_url}/shop?payment=success",
            "failure": f"{base_url}/shop?payment=failure",
            "pending": f"{base_url}/shop?payment=pending",
        },
        "auto_return": "approved",
        "notification_url": f"{base_url}/api/payments/webhook",
    }
    response = sdk.preference().create(preference).get("response", {})
    return {
        "init_point": response.get("init_point"),
        "sandbox_init_point": response.get("sandbox_init_point"),
        "preference_id": response.get("id"),
    }


def get_payment(payment_id):
    """Consulta um pagamento; retorna {status, external_reference, id} ou None."""
    sdk = _sdk()
    if sdk is None:
        return None
    response = sdk.payment().get(payment_id).get("response", {})
    return {
        "status": response.get("status"),
        "external_reference": response.get("external_reference"),
        "id": response.get("id"),
    }
