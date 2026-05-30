"""Gera um relatório de testes (HTML) rodando a suíte pytest sob demanda.

Usado pela rota GET /tests/report (somente em desenvolvimento). Roda o pytest em
subprocesso, lê o resultado via JUnit XML e renderiza uma página HTML dividida por
nível (alto: aceitação/integração; baixo: unitário).
"""
import html
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


def load_status():
    """Lê o status do projeto de status.json (Feito/Fazendo/Próximo); None se ausente."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "status.json")
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return None


def run_pytest():
    """Roda a suíte e retorna (summary, cases, raw_tail)."""
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    xml_path = os.path.join(tempfile.gettempdir(), "mgstreet_report.xml")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--junitxml", xml_path],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        timeout=180,
    )
    summary, cases = _parse_junit(xml_path)
    return summary, cases, proc.stdout[-3000:]


def _parse_junit(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    suite = root.find("testsuite") if root.tag == "testsuites" else root

    summary = {
        "tests": int(suite.get("tests", 0)),
        "failures": int(suite.get("failures", 0)),
        "errors": int(suite.get("errors", 0)),
        "skipped": int(suite.get("skipped", 0)),
        "time": float(suite.get("time", 0.0)),
    }
    summary["passed"] = (
        summary["tests"] - summary["failures"] - summary["errors"] - summary["skipped"]
    )

    cases = []
    for testcase in suite.findall("testcase"):
        status = "passed"
        message = ""
        for tag in ("failure", "error", "skipped"):
            node = testcase.find(tag)
            if node is not None:
                status = "failed" if tag == "failure" else tag
                message = node.get("message", "")
                break
        cases.append(
            {
                "classname": testcase.get("classname", ""),
                "name": testcase.get("name", ""),
                "time": float(testcase.get("time", 0.0)),
                "status": status,
                "message": message,
            }
        )
    return summary, cases


_BADGE_COLORS = {
    "passed": "#1f9d55",
    "failed": "#cc1f1a",
    "error": "#cc1f1a",
    "skipped": "#8a8a8a",
}


def _level_of(classname):
    """Classifica o teste em ('alto'|'baixo', rótulo) pelo nome do módulo."""
    name = classname.lower()
    if "acceptance" in name:
        return ("alto", "Aceitação (E2E)")
    if "integration" in name:
        return ("alto", "Integração")
    if "unit" in name:
        return ("baixo", "Unitário")
    return ("baixo", "Outros")


def _render_rows(cases):
    rows = []
    for case in cases:
        color = _BADGE_COLORS.get(case["status"], "#8a8a8a")
        message = html.escape(case["message"]) if case["message"] else ""
        label = _level_of(case["classname"])[1]
        rows.append(
            f"<tr>"
            f"<td>{html.escape(label)}</td>"
            f"<td>{html.escape(case['classname'])}</td>"
            f"<td>{html.escape(case['name'])}</td>"
            f"<td><span class='badge' style='background:{color}'>{case['status']}</span></td>"
            f"<td class='num'>{case['time']:.3f}s</td>"
            f"<td class='msg'>{message}</td>"
            f"</tr>"
        )
    return "\n".join(rows)


def _section(title, subtitle, cases):
    if not cases:
        return ""
    passed = sum(1 for c in cases if c["status"] == "passed")
    failed = sum(1 for c in cases if c["status"] in ("failed", "error"))
    skipped = sum(1 for c in cases if c["status"] == "skipped")
    return f"""
        <section class="level">
            <h2>{html.escape(title)} <small>{subtitle}</small></h2>
            <div class="counts">{len(cases)} testes &middot; {passed} &#10003; &middot; {failed} &#10007; &middot; {skipped} skip</div>
            <table>
                <thead><tr><th>Nível</th><th>Módulo</th><th>Teste</th><th>Status</th><th>Tempo</th><th>Mensagem</th></tr></thead>
                <tbody>
{_render_rows(cases)}
                </tbody>
            </table>
        </section>"""


def _status_panel(status):
    """Painel simples de status do projeto (Feito / Fazendo / Próximo)."""
    if not status:
        return ""
    feito = "".join(f"<li>{html.escape(str(x))}</li>" for x in status.get("feito", []))
    fazendo = html.escape(str(status.get("fazendo", "—")))
    proximo = html.escape(str(status.get("proximo", "—")))
    return f"""
        <section class="status">
            <h2>Status do projeto</h2>
            <div class="status-grid">
                <div><strong>✅ Feito</strong><ul>{feito}</ul></div>
                <div><strong>🔄 Fazendo</strong><p>{fazendo}</p></div>
                <div><strong>➡️ Próximo</strong><p>{proximo}</p></div>
            </div>
        </section>"""


def _cost_box(status):
    """Quadrado de custo (estimativa MANUAL — o app não acessa o faturamento real)."""
    custo = (status or {}).get("custo")
    if not custo:
        return ""
    faixa = html.escape(str(custo.get("faixa", "—")))
    nota = html.escape(str(custo.get("nota", "")))
    return f"""
        <section class="cost">
            <h2>💸 Custo Claude (estimativa)</h2>
            <div class="cost-val">{faixa}</div>
            <div class="cost-note">{nota}</div>
        </section>"""


def render_html(summary, cases, raw_tail, generated_at, refresh_seconds=15):
    """Renderiza o relatório de testes como HTML, dividido por nível."""
    ok = summary["failures"] == 0 and summary["errors"] == 0
    header_color = "#1f9d55" if ok else "#cc1f1a"
    header_text = "TODOS OS TESTES PASSARAM" if ok else "HÁ FALHAS NA SUÍTE"

    alto = [c for c in cases if _level_of(c["classname"])[0] == "alto"]
    baixo = [c for c in cases if _level_of(c["classname"])[0] == "baixo"]
    sections = (
        _section("Alto nível", "aceitação &amp; integração — jornadas e endpoints", alto)
        + _section("Baixo nível", "unitário — funções isoladas", baixo)
    )
    raw = html.escape(raw_tail)
    status = load_status()
    status_html = _status_panel(status)
    cost_html = _cost_box(status)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="{refresh_seconds}">
    <title>MG Street - Relatório de Testes</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; background: #f4f1ea; color: #222; }}
        header {{ background: {header_color}; color: #fff; padding: 18px 24px; }}
        header h1 {{ margin: 0 0 4px 0; font-size: 1.3rem; }}
        header .sub {{ opacity: .9; font-size: .9rem; }}
        .wrap {{ padding: 20px 24px; }}
        .cards {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 18px; }}
        .card {{ background: #fff; border: 2px solid #e3ddcf; border-radius: 8px; padding: 12px 16px; min-width: 92px; }}
        .card .n {{ font-size: 1.5rem; font-weight: 700; }}
        .card .l {{ font-size: .8rem; color: #666; }}
        .status {{ background: #fff; border: 2px solid #e3ddcf; border-radius: 8px; padding: 12px 16px; margin-bottom: 18px; }}
        .status h2 {{ margin: 0 0 8px 0; font-size: 1.1rem; }}
        .status-grid {{ display: grid; grid-template-columns: 1.4fr 1fr 1fr; gap: 16px; }}
        .status-grid ul {{ margin: 6px 0 0 18px; padding: 0; font-size: .85rem; }}
        .status-grid p {{ margin: 6px 0 0 0; font-size: .9rem; }}
        @media (max-width: 720px) {{ .status-grid {{ grid-template-columns: 1fr; }} }}
        .cost {{ background: #fff; border: 2px solid #e3ddcf; border-left: 6px solid #6f4bd9; border-radius: 8px; padding: 12px 16px; margin-bottom: 18px; }}
        .cost h2 {{ margin: 0 0 4px 0; font-size: 1.0rem; }}
        .cost-val {{ font-size: 1.3rem; font-weight: 700; }}
        .cost-note {{ color: #777; font-size: .8rem; margin-top: 4px; }}
        .level {{ margin-bottom: 22px; }}
        .level h2 {{ margin: 0 0 2px 0; font-size: 1.1rem; }}
        .level h2 small {{ font-weight: 400; color: #777; font-size: .8rem; }}
        .counts {{ color: #555; font-size: .85rem; margin-bottom: 8px; }}
        table {{ width: 100%; border-collapse: collapse; background: #fff; border: 2px solid #e3ddcf; border-radius: 8px; overflow: hidden; }}
        th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #eee; font-size: .88rem; }}
        th {{ background: #efeadd; }}
        td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
        td.msg {{ color: #999; font-size: .8rem; }}
        .badge {{ color: #fff; padding: 2px 8px; border-radius: 10px; font-size: .72rem; text-transform: uppercase; }}
        details {{ margin-top: 10px; }}
        pre {{ background: #1e1e1e; color: #ddd; padding: 12px; border-radius: 8px; overflow: auto; font-size: .8rem; }}
    </style>
</head>
<body>
    <header>
        <h1>MG Street — Relatório de Testes</h1>
        <div class="sub">{header_text} · gerado em {html.escape(generated_at)} · auto-refresh {refresh_seconds}s</div>
    </header>
    <div class="wrap">
        <div class="cards">
            <div class="card"><div class="n">{summary['tests']}</div><div class="l">Total</div></div>
            <div class="card"><div class="n" style="color:#1f9d55">{summary['passed']}</div><div class="l">Passou</div></div>
            <div class="card"><div class="n" style="color:#cc1f1a">{summary['failures']}</div><div class="l">Falhou</div></div>
            <div class="card"><div class="n" style="color:#cc1f1a">{summary['errors']}</div><div class="l">Erros</div></div>
            <div class="card"><div class="n" style="color:#8a8a8a">{summary['skipped']}</div><div class="l">Pulou</div></div>
            <div class="card"><div class="n">{summary['time']:.2f}s</div><div class="l">Duração</div></div>
        </div>
{status_html}
{cost_html}
{sections}
        <details>
            <summary>Saída bruta do pytest</summary>
            <pre>{raw}</pre>
        </details>
    </div>
</body>
</html>
"""
