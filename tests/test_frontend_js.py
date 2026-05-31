"""Testes da extração de JS e da limpeza dos templates (spec/frontend/02-code-style.md).

Garantem que os módulos JS são servidos, que os templates os referenciam e que não há
mais `<script>` inline (com lógica) nem `style=`/`<style>` inline no admin.
"""
import os
import re

import pytest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS_DIR = os.path.join(ROOT, "static", "js")
TEMPLATES_DIR = os.path.join(ROOT, "templates")

JS_FILES = ["api.js", "ui.js", "admin.js", "shop.js", "landing.js", "login.js", "register.js"]
TEMPLATES = ["landing.html", "shop.html", "login.html", "register.html", "admin.html"]

# Abre um <script ...> que NÃO tem atributo src (ou seja, script inline com código).
INLINE_SCRIPT = re.compile(r"<script(?![^>]*\bsrc\b)[^>]*>")


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


@pytest.mark.parametrize("name", JS_FILES)
def test_js_modules_are_served(client, name):
    """Cada módulo JS é servido pelo Flask (sem 404)."""
    resp = client.get(f"/static/js/{name}")
    assert resp.status_code == 200, f"/static/js/{name} retornou {resp.status_code}"


@pytest.mark.parametrize("name", TEMPLATES)
def test_templates_have_no_inline_script(name):
    """Nenhum template tem <script> inline com lógica (tudo via <script src>)."""
    html = _read(os.path.join(TEMPLATES_DIR, name))
    assert not INLINE_SCRIPT.search(html), f"{name} ainda tem <script> inline"


def test_admin_has_no_inline_styles():
    """admin.html não tem mais style= inline nem bloco <style> (02-code-style §2)."""
    html = _read(os.path.join(TEMPLATES_DIR, "admin.html"))
    assert "style=" not in html
    assert "<style" not in html


def test_templates_reference_their_modules():
    """Cada página linka seu módulo de JS correspondente."""
    expected = {
        "landing.html": "js/landing.js",
        "shop.html": "js/shop.js",
        "login.html": "js/login.js",
        "register.html": "js/register.js",
        "admin.html": "js/admin.js",
    }
    for template, module in expected.items():
        html = _read(os.path.join(TEMPLATES_DIR, template))
        assert module in html, f"{template} não referencia {module}"
