"""Testes da camada visual (fonte display + hero) — vibe hype/street.

Protegem o "update visível": fonte display ligada nos templates e aplicada via token,
e o CTA do hero na landing.
"""
import os

import pytest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS_DIR = os.path.join(ROOT, "static", "css")
TEMPLATES_DIR = os.path.join(ROOT, "templates")
TEMPLATES = ["landing.html", "shop.html", "login.html", "register.html", "admin.html"]


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def test_display_font_token_defined():
    """tokens.css define --font-display usando a fonte display (Anton)."""
    tokens = _read(os.path.join(CSS_DIR, "tokens.css"))
    assert "--font-display" in tokens
    assert "Anton" in tokens


def test_display_font_applied_to_headings():
    """A fonte display é aplicada às headings (layout.css usa var(--font-display))."""
    layout = _read(os.path.join(CSS_DIR, "layout.css"))
    assert "var(--font-display)" in layout


@pytest.mark.parametrize("name", TEMPLATES)
def test_templates_link_display_font(name):
    """Todo template carrega a fonte display via <link> (Google Fonts)."""
    html = _read(os.path.join(TEMPLATES_DIR, name))
    assert "fonts.googleapis.com" in html
    assert "family=Anton" in html


def test_landing_renders_font_and_cta(client):
    """A landing (/) responde 200, carrega a fonte display e tem o CTA do hero."""
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "family=Anton" in body
    assert "Entrar e comprar" in body
