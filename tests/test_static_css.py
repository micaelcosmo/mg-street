"""Testes da arquitetura CSS em camadas (spec/frontend/02-code-style.md).

Protegem o refactor: garantem que o Flask serve o índice e todos os partials (um 404 aqui
deixaria a loja sem estilo em produção), que o índice importa cada camada e que os partials
de camada não têm cor crua (só tokens via var()).
"""
import os
import re

import pytest


STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
CSS_DIR = os.path.join(STATIC_DIR, "css")
LAYER_FILES = ["tokens.css", "base.css", "layout.css", "components.css", "utilities.css"]
# Partials que NÃO podem ter cor crua (apenas tokens.css define literais).
NON_TOKEN_LAYERS = ["base.css", "layout.css", "components.css", "utilities.css"]

# #fff / #ffffff / #abc123 etc.
HEX_COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b")
# rgb( / rgba(
RGB_COLOR = re.compile(r"\brgba?\(")


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def test_index_links_only_style_css_served(client):
    """O índice style.css é servido (é o único que os templates linkam)."""
    resp = client.get("/static/style.css")
    assert resp.status_code == 200


@pytest.mark.parametrize("name", LAYER_FILES)
def test_layer_files_are_served(client, name):
    """Cada partial de camada é servido pelo Flask (sem 404 — evita site sem estilo)."""
    resp = client.get(f"/static/css/{name}")
    assert resp.status_code == 200, f"/static/css/{name} retornou {resp.status_code}"


def test_index_declares_and_imports_all_layers():
    """style.css declara a ordem das camadas e importa cada partial na sua @layer."""
    index = _read(os.path.join(STATIC_DIR, "style.css"))
    assert "@layer tokens, base, layout, components, utilities;" in index
    for name in LAYER_FILES:
        layer = name.replace(".css", "")
        assert f'@import url("css/{name}") layer({layer});' in index


@pytest.mark.parametrize("name", NON_TOKEN_LAYERS)
def test_layer_files_have_no_raw_colors(name):
    """Sem cor crua fora de tokens.css: regra 'sem hex solto' (02-code-style §3)."""
    content = _read(os.path.join(CSS_DIR, name))
    assert not HEX_COLOR.search(content), f"{name} tem cor hex crua; use um token var()"
    assert not RGB_COLOR.search(content), f"{name} tem rgb()/rgba() cru; use um token var()"


def test_critical_classes_preserved():
    """Nenhuma classe usada por HTML/JS ficou órfã após o split/consolidação."""
    all_css = "\n".join(_read(os.path.join(CSS_DIR, name)) for name in LAYER_FILES)
    required = [
        ".btn", ".btn-ghost", ".btn-danger", ".buy-btn",
        ".product-card", ".product-img", ".product-tag", ".product-footer",
        ".products-grid", ".filter-chip", ".cart-button", ".cart-panel", ".cart-item",
        ".qty-btn", ".modal", ".modal-content", ".mg-toast", ".carousel",
        ".products-table", ".sales-dashboard", ".user-preview", ".muted",
    ]
    missing = [selector for selector in required if selector not in all_css]
    assert not missing, f"classes ausentes no CSS: {missing}"
