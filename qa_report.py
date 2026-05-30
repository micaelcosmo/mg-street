"""Gera um relatório de testes (HTML) rodando a suíte pytest sob demanda.

Usado pela rota GET /tests/report (somente em desenvolvimento). Roda o pytest em
subprocesso, lê o resultado via JUnit XML e renderiza uma página HTML.
"""
import datetime
import html
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


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


def render_html(summary, cases, raw_tail, generated_at, refresh_seconds=15):
    """Renderiza o relatório de testes como HTML."""
    ok = summary["failures"] == 0 and summary["errors"] == 0
    header_color = "#1f9d55" if ok else "#cc1f1a"
    header_text = "TODOS OS TESTES PASSARAM" if ok else "HÁ FALHAS NA SUÍTE"

    rows = []
    for case in cases:
        color = _BADGE_COLORS.get(case["status"], "#8a8a8a")
        message = html.escape(case["message"]) if case["message"] else ""
        rows.append(
            f"<tr>"
            f"<td>{html.escape(case['classname'])}</td>"
            f"<td>{html.escape(case['name'])}</td>"
            f"<td><span class='badge' style='background:{color}'>{case['status']}</span></td>"
            f"<td class='num'>{case['time']:.3f}s</td>"
            f"<td class='msg'>{message}</td>"
            f"</tr>"
        )
    rows_html = "\n".join(rows)
    raw = html.escape(raw_tail)

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
        .card {{ background: #fff; border: 2px solid #e3ddcf; border-radius: 8px;
                 padding: 12px 16px; min-width: 96px; }}
        .card .n {{ font-size: 1.5rem; font-weight: 700; }}
        .card .l {{ font-size: .8rem; color: #666; }}
        table {{ width: 100%; border-collapse: collapse; background: #fff;
                 border: 2px solid #e3ddcf; border-radius: 8px; overflow: hidden; }}
        th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #eee; font-size: .9rem; }}
        th {{ background: #efeadd; }}
        td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
        td.msg {{ color: #999; font-size: .8rem; }}
        .badge {{ color: #fff; padding: 2px 8px; border-radius: 10px; font-size: .75rem; text-transform: uppercase; }}
        details {{ margin-top: 18px; }}
        pre {{ background: #1e1e1e; color: #ddd; padding: 12px; border-radius: 8px; overflow:auto; font-size: .8rem; }}
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
        <table>
            <thead><tr><th>Módulo</th><th>Teste</th><th>Status</th><th>Tempo</th><th>Mensagem</th></tr></thead>
            <tbody>
{rows_html}
            </tbody>
        </table>
        <details>
            <summary>Saída bruta do pytest</summary>
            <pre>{raw}</pre>
        </details>
    </div>
</body>
</html>
"""
