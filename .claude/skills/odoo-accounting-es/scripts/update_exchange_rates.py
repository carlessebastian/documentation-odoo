#!/usr/bin/env python3
"""Actualiza res.currency.rate desde el feed XML del Banco Central Europeo.

Fuentes:
  - hoy:           https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml
  - 90 dias:       https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml
  - historico:     https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml

Asume que la moneda de la compania es EUR (caso espanol estandar). Las
tasas ECB son "EUR -> X" (ej. rate=1.0823 significa 1 EUR = 1.0823 USD),
que coincide con la convencion de Odoo cuando company_currency es EUR.

Idempotente: salta tasas ya existentes para esa fecha+moneda.
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from datetime import date
from typing import Any

from _common import OdooError, retry_on_network
from odoo_client import OdooClient


ECB_DAILY = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
ECB_90D = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
ECB_HIST = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml"

NS = {
    "gesmes": "http://www.gesmes.org/xml/2002-08-01",
    "ecb": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref",
}


def fetch_ecb(scope: str = "daily") -> list[dict[str, Any]]:
    """Devuelve lista de {date, rates: {CCY: rate}} parseando ECB XML."""
    import requests
    url = {"daily": ECB_DAILY, "90d": ECB_90D, "history": ECB_HIST}[scope]
    r = retry_on_network(lambda: requests.get(url, timeout=30))
    r.raise_for_status()
    root = ET.fromstring(r.content)

    out: list[dict[str, Any]] = []
    cube_root = root.find("ecb:Cube", NS)
    if cube_root is None:
        raise OdooError("Estructura XML ECB inesperada (sin <Cube> raiz)")
    for time_cube in cube_root.findall("ecb:Cube", NS):
        d = time_cube.get("time")
        rates = {}
        for c in time_cube.findall("ecb:Cube", NS):
            rates[c.get("currency")] = float(c.get("rate"))
        if d:
            out.append({"date": d, "rates": rates})
    return out


def update_rates(
    client: OdooClient,
    *,
    scope: str = "daily",
    currencies: list[str] | None = None,
    company_id: int = 1,
) -> dict[str, Any]:
    company = client.search_read(
        "res.company", [("id", "=", company_id)],
        ["currency_id", "name"], limit=1,
    )
    if not company:
        raise OdooError(f"Compania {company_id} no existe")
    company_curr_id = company[0]["currency_id"][0]
    company_curr = client.search_read(
        "res.currency", [("id", "=", company_curr_id)],
        ["name"], limit=1,
    )[0]["name"]
    if company_curr != "EUR":
        return {
            "warning": (
                f"Moneda de compania es {company_curr}, no EUR. "
                "El script asume EUR; las tasas ECB no aplican directamente."
            ),
            "company_currency": company_curr,
        }

    feed = fetch_ecb(scope)
    if not feed:
        return {"feed_dates": 0, "warning": "Feed ECB vacio"}

    requested_currs = set(currencies) if currencies else None
    available_currs: set[str] = set()
    for entry in feed:
        available_currs.update(entry["rates"].keys())
    target_currs = (
        requested_currs & available_currs if requested_currs
        else available_currs
    )

    odoo_currs = client.search_read(
        "res.currency",
        [("name", "in", list(target_currs)), ("active", "=", True)],
        ["id", "name"],
    )
    by_name = {c["name"]: c["id"] for c in odoo_currs}
    missing_in_odoo = target_currs - set(by_name)

    created = 0
    skipped = 0
    errors: list[dict] = []

    for entry in feed:
        d = entry["date"]
        for ccy, rate in entry["rates"].items():
            if requested_currs and ccy not in requested_currs:
                continue
            ccy_id = by_name.get(ccy)
            if not ccy_id:
                continue
            existing = client.search_read(
                "res.currency.rate",
                [("currency_id", "=", ccy_id),
                 ("name", "=", d),
                 ("company_id", "=", company_id)],
                ["id"], limit=1,
            )
            if existing:
                skipped += 1
                continue
            try:
                client.create("res.currency.rate", {
                    "currency_id": ccy_id,
                    "name": d,
                    "rate": rate,
                    "company_id": company_id,
                })
                created += 1
            except OdooError as e:
                errors.append({"date": d, "currency": ccy, "error": str(e)})

    return {
        "scope": scope,
        "feed_dates": len(feed),
        "company_currency": "EUR",
        "currencies_requested": sorted(target_currs),
        "currencies_missing_in_odoo": sorted(missing_in_odoo),
        "rates_created": created,
        "rates_skipped_existing": skipped,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scope",
        choices=["daily", "90d", "history"],
        default="daily",
        help="Ventana del feed ECB (default: daily = solo hoy)",
    )
    parser.add_argument(
        "--currencies",
        help="Lista de monedas separadas por coma (ej. USD,GBP,JPY). "
             "Si se omite, importa todas las disponibles en Odoo.",
    )
    parser.add_argument("--company-id", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true",
                        help="Solo descarga y parsea ECB, no escribe en Odoo")
    ns = parser.parse_args()

    if ns.dry_run:
        feed = fetch_ecb(ns.scope)
        json.dump({
            "scope": ns.scope,
            "feed_dates": len(feed),
            "first_date": feed[0]["date"] if feed else None,
            "last_date": feed[-1]["date"] if feed else None,
            "preview": feed[:3],
        }, sys.stdout, indent=2, ensure_ascii=False, default=str)
        print()
        return 0

    currs = (
        [c.strip().upper() for c in ns.currencies.split(",") if c.strip()]
        if ns.currencies else None
    )
    client = OdooClient()
    result = update_rates(
        client, scope=ns.scope, currencies=currs, company_id=ns.company_id,
    )
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False, default=str)
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
