#!/usr/bin/env python3
"""
Gera um relatorio HTML simples a partir de dados reais (ASCII only).

- Le o relatorio mais recente em reports/metadata_report_*.json, se existir
- Opcional: usar um JSON especifico via --json caminho/arquivo.json
- Mostra metricas basicas: total, sucesso, falhas, campos ausentes
- Salva advanced_algorithms_report.html na raiz (pode ser alterado via --output)

Nao usa dados falsos; se nao houver relatorio, cria um resumo minimo da pasta books/.
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
import argparse

ROOT = Path(__file__).parent
REPORTS = ROOT / "reports"
BOOKS = ROOT / "books"
DEFAULT_OUT = REPORTS / "advanced_algorithms_report.html"


def load_latest_report():
    if not REPORTS.exists():
        return None
    candidates = sorted(REPORTS.glob("metadata_report_*.json"))
    if not candidates:
        return None
    try:
        with open(candidates[-1], "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def summarize_from_json(data: dict) -> dict:
    summary = data.get("summary") or {}
    total = summary.get("total_files") or summary.get("total_books") or 0
    success = summary.get("successful") or summary.get("success") or 0
    failed = summary.get("failed") or summary.get("failures") or 0
    missing = summary.get("missing_fields") or {}
    publishers = data.get("publisher_stats") or {}
    return {
        "total": int(total),
        "success": int(success),
        "failed": int(failed),
        "missing": missing,
        "publishers": publishers,
    }


def summarize_from_books() -> dict:
    if not BOOKS.exists():
        return {"total": 0, "success": 0, "failed": 0, "missing": {}, "publishers": {}}
    files = [p for p in BOOKS.iterdir() if p.suffix.lower() in {".pdf", ".epub"}]
    return {"total": len(files), "success": 0, "failed": 0, "missing": {}, "publishers": {}}


def render_html(summary: dict) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    missing_html = "".join(
        f"<li>{field}: {count}</li>" for field, count in (summary.get("missing") or {}).items()
    )
    pub_html = "".join(
        f"<li>{pub}: {cnt}</li>" for pub, cnt in list((summary.get("publishers") or {}).items())[:20]
    )
    return f"""
<!doctype html>
<html lang=\"pt-BR\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Relatorio de Processamento - RenamePDFEPUB</title>
  <style>
    body {{ font-family: -apple-system, system-ui, Segoe UI, Roboto, Ubuntu, Cantarell, 'Helvetica Neue', Arial, sans-serif; margin: 24px; }}
    h1 {{ margin-bottom: 0; }}
    .muted {{ color: #666; margin-top: 4px; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, minmax(180px, 1fr)); gap: 12px; margin: 16px 0 24px; }}
    .card {{ border: 1px solid #ddd; padding: 12px; border-radius: 8px; }}
    h2 {{ margin-top: 28px; }}
  </style>
  </head>
<body>
  <h1>Relatorio de Processamento</h1>
  <div class=\"muted\">Atualizado: {now}</div>

  <div class=\"grid\">
    <div class=\"card\"><strong>Total de arquivos</strong><br/>{summary.get('total', 0)}</div>
    <div class=\"card\"><strong>Processados com sucesso</strong><br/>{summary.get('success', 0)}</div>
    <div class=\"card\"><strong>Falhas</strong><br/>{summary.get('failed', 0)}</div>
  </div>

  <h2>Campos ausentes</h2>
  <ul>{missing_html or '<li>Sem dados</li>'}</ul>

  <h2>Editoras (amostra)</h2>
  <ul>{pub_html or '<li>Sem dados</li>'}</ul>

</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Gerador HTML simples (ASCII only)")
    parser.add_argument("--json", dest="json_path", help="Arquivo JSON especifico a usar")
    parser.add_argument("--output", dest="output_html", help="Arquivo HTML de saida")
    args = parser.parse_args()

    data = None
    if args.json_path:
        p = Path(args.json_path)
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                data = None
        else:
            print(f"[WARNING] JSON nao encontrado: {p}")
    if data is None:
        data = load_latest_report()

    if isinstance(data, dict):
        summary = summarize_from_json(data)
    else:
        summary = summarize_from_books()

    html = render_html(summary)
    out = Path(args.output_html) if args.output_html else DEFAULT_OUT
    out.write_text(html, encoding="utf-8")
    print(f"Relatorio gerado: {out}")


if __name__ == "__main__":
    main()
