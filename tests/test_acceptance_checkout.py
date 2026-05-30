import os

import pytest


pytestmark = pytest.mark.skipif(
    not os.getenv("MGSTREET_DB_TESTS"),
    reason="Jornada E2E exige Postgres ativo (defina MGSTREET_DB_TESTS=1).",
)


def test_customer_purchase_journey():
    """Semente da jornada de aceitação (alto nível).

    Fluxo a implementar contra um banco real:
      1. Login como cliente demo -> recebe token.
      2. GET /api/products -> lista o catálogo.
      3. POST /api/checkout com items -> cria pedido (201).
      4. Login admin -> GET /api/orders confirma o pedido criado.
      5. GET /api/orders/stats reflete total e receita.

    Implementação completa rastreada em spec/04-tasks.md.
    """
    assert True
