"""Auditoria de contraste WCAG AAA (texto normal >= 7:1) a partir dos tokens reais.

Lê os tokens de cor em static/css/tokens.css e verifica os pares foreground/background
usados na UI. Falha se algum par cair abaixo de AAA — trava a acessibilidade contra regressão.
"""
import os
import re

import pytest


TOKENS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "css", "tokens.css"
)
AAA_NORMAL = 7.0

# Pares (texto, fundo) por nome de token, como aparecem na UI.
PAIRS = [
    ("ink", "bg"),
    ("ink", "surface"),
    ("ink", "surface-alt"),
    ("muted", "bg"),
    ("muted", "surface"),
    ("muted", "surface-alt"),
    ("ink-on-brand", "btn-bg"),          # texto do botão primário
    ("ink-on-brand", "btn-bg-hover"),    # botão primário em hover
    ("ink-on-brand", "danger-strong"),   # btn-danger
    ("ink-on-light", "brand-cyan"),      # cart-button / filter-chip ativo
    ("ink-on-light", "cyan-hover"),      # cart-button hover
    ("ink-on-light", "brand-accent"),    # section-kicker / product-tag
    ("danger", "surface-alt"),           # texto "remover" no carrinho
    ("link", "surface"),                 # link auth-alt
]


def _read_tokens():
    with open(TOKENS_PATH, encoding="utf-8") as handle:
        content = handle.read()
    tokens = {}
    for name, value in re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{3,8})", content):
        tokens[name] = value
    return tokens


def _channel(value):
    value = value / 255
    return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4


def _luminance(hex_color):
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(ch * 2 for ch in hex_color)
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def _contrast(fg, bg):
    high, low = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (high + 0.05) / (low + 0.05)


TOKENS = _read_tokens()


@pytest.mark.parametrize("fg,bg", PAIRS)
def test_pair_meets_aaa(fg, bg):
    assert fg in TOKENS, f"token --{fg} ausente em tokens.css"
    assert bg in TOKENS, f"token --{bg} ausente em tokens.css"
    ratio = _contrast(TOKENS[fg], TOKENS[bg])
    assert ratio >= AAA_NORMAL, (
        f"{fg} sobre {bg}: {ratio:.2f}:1 < {AAA_NORMAL}:1 (AAA). Ajuste o token."
    )
