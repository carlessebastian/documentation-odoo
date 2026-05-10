#!/usr/bin/env python3
"""Ejecuta un modelo AEAT (303/347/349/390/111/115/130) para un periodo.

Detecta Enterprise (`l10n_es_reports`, motor `account.report`) o OCA
(`l10n_es_aeat_mod*`, modelos `l10n.es.aeat.mod*.report`) y exporta en el
formato pedido (boe / xlsx / pdf).
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from typing import Any

from _common import OdooError
from odoo_client import OdooClient


SUPPORTED = {"111", "115", "130", "232", "303", "347", "349", "369", "390", "720"}


def _period_to_dates(period: str) -> tuple[str, str, str]:
    """Convierte '2026Q1' o '2026-05' o '2026' a (date_from, date_to, oca_period)."""
    m = re.fullmatch(r"(\d{4})Q([1-4])", period)
    if m:
        y, q = int(m.group(1)), int(m.group(2))
        starts = {1: ("01", "03", "31"), 2: ("04", "06", "30"),
                  3: ("07", "09", "30"), 4: ("10", "12", "31")}
        sm, em, ed = starts[q]
        return f"{y}-{sm}-01", f"{y}-{em}-{ed}", f"{q}T"
    m = re.fullmatch(r"(\d{4})-(\d{2})", period)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        if not 1 <= mo <= 12:
            raise OdooError(f"Mes invalido en periodo: {period}")
        from calendar import monthrange
        last = monthrange(y, mo)[1]
        return f"{y}-{mo:02d}-01", f"{y}-{mo:02d}-{last}", f"{mo:02d}"
    m = re.fullmatch(r"(\d{4})", period)
    if m:
        y = int(m.group(1))
        return f"{y}-01-01", f"{y}-12-31", "0A"
    raise OdooError(f"Periodo invalido: {period} (use 2026Q1, 2026-05 o 2026)")


def _detect_provider(client: OdooClient, model_code: str) -> str | None:
    rows = client.search_read(
        "ir.module.module",
        [
            ("name", "in", [
                "l10n_es_reports",
                f"l10n_es_aeat_mod{model_code}",
            ]),
            ("state", "=", "installed"),
        ],
        ["name"],
    )
    names = {r["name"] for r in rows}
    if "l10n_es_reports" in names:
        return "enterprise"
    if f"l10n_es_aeat_mod{model_code}" in names:
        return "oca"
    return None


def run_oca_report(
    client: OdooClient,
    model_code: str,
    period: str,
    *,
    company_id: int = 1,
    output_format: str = "boe",
) -> dict[str, Any]:
    date_from, date_to, oca_period = _period_to_dates(period)
    year = int(date_from.split("-")[0])
    model = f"l10n.es.aeat.mod{model_code}.report"

    report_id = client.create(model, {
        "name": f"{model_code}-{period}",
        "company_id": company_id,
        "year": year,
        "period_type": oca_period,
        "tipo_declaracion": "I",
    })
    client.action(model, [report_id], "calculate")
    client.action(model, [report_id], "confirm")

    if output_format == "boe":
        boe = client.call(model, "export_boe", [[report_id]])
        if isinstance(boe, str):
            boe = base64.b64decode(boe)
        return {
            "report_id": report_id,
            "model": model_code,
            "period": period,
            "boe_b64": base64.b64encode(boe).decode("ascii"),
        }
    return {"report_id": report_id, "model": model_code, "period": period}


def run_enterprise_report(
    client: OdooClient,
    model_code: str,
    period: str,
    *,
    output_format: str = "pdf",
) -> dict[str, Any]:
    date_from, date_to, _ = _period_to_dates(period)
    name_pattern = f"%{model_code}%"
    reports = client.search_read(
        "account.report",
        [("name", "ilike", name_pattern), ("country_id.code", "=", "ES")],
        ["id", "name"],
        limit=1,
    )
    if not reports:
        raise OdooError(
            f"No se encontro account.report para modelo {model_code}"
        )
    report_id = reports[0]["id"]

    options = client.call(
        "account.report",
        "_get_options",
        [report_id, {
            "date": {
                "date_from": date_from,
                "date_to": date_to,
                "filter": "custom",
                "mode": "range",
            },
        }],
    )
    lines = client.call("account.report", "_get_lines", [report_id, options])
    return {
        "report_id": report_id,
        "report_name": reports[0]["name"],
        "model": model_code,
        "period": period,
        "date_from": date_from,
        "date_to": date_to,
        "line_count": len(lines),
        "lines_preview": lines[:10],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True,
                        help="Codigo del modelo: 303, 347, 349, 390, 111, 115, 130")
    parser.add_argument("--period", required=True,
                        help="2026Q1, 2026-05 o 2026")
    parser.add_argument("--company-id", type=int, default=1)
    parser.add_argument("--format", dest="output_format",
                        choices=["boe", "pdf", "xlsx"], default="boe")
    ns = parser.parse_args()

    if ns.model not in SUPPORTED:
        raise OdooError(f"Modelo no soportado: {ns.model}")

    client = OdooClient()
    provider = _detect_provider(client, ns.model)
    if not provider:
        raise OdooError(
            f"Ningun modulo para modelo {ns.model} "
            "(esperado l10n_es_reports o l10n_es_aeat_mod{ns.model})"
        )

    if provider == "oca":
        result = run_oca_report(
            client, ns.model, ns.period,
            company_id=ns.company_id,
            output_format=ns.output_format,
        )
    else:
        result = run_enterprise_report(
            client, ns.model, ns.period,
            output_format=ns.output_format,
        )
    result["provider"] = provider
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False, default=str)
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
