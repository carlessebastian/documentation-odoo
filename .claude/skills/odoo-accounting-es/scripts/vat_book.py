#!/usr/bin/env python3
"""Genera libro IVA emitido y/o recibido para un periodo (OCA l10n_es_vat_book).

Soporta libro emitido (out_invoice + out_refund) y recibido
(in_invoice + in_refund). Exporta a XLSX si el modulo lo permite.
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


def _period_to_oca(period: str) -> tuple[int, str]:
    m = re.fullmatch(r"(\d{4})Q([1-4])", period)
    if m:
        return int(m.group(1)), f"{m.group(2)}T"
    m = re.fullmatch(r"(\d{4})-(\d{2})", period)
    if m:
        return int(m.group(1)), m.group(2)
    m = re.fullmatch(r"(\d{4})", period)
    if m:
        return int(m.group(1)), "0A"
    raise OdooError(f"Periodo invalido: {period}")


def generate_vat_book(
    client: OdooClient,
    *,
    period: str,
    company_id: int = 1,
    book_type: str = "all",
    export_xlsx: bool = False,
) -> dict[str, Any]:
    rows = client.search_read(
        "ir.module.module",
        [("name", "=", "l10n_es_vat_book"), ("state", "=", "installed")],
        ["name"], limit=1,
    )
    if not rows:
        raise OdooError(
            "Modulo l10n_es_vat_book no instalado. "
            "Instalar desde OCA/l10n-spain o usar SII para sustituirlo."
        )

    year, period_type = _period_to_oca(period)
    book_id = client.create("l10n.es.vat.book", {
        "name": f"VAT Book {period}",
        "company_id": company_id,
        "year": year,
        "period_type": period_type,
    })
    client.action("l10n.es.vat.book", [book_id], "calculate")
    client.action("l10n.es.vat.book", [book_id], "confirm")

    summary: dict[str, Any] = {
        "book_id": book_id,
        "period": period,
        "company_id": company_id,
    }

    if book_type in ("issued", "all"):
        issued = client.search_read(
            "l10n.es.vat.book.line",
            [("vat_book_id", "=", book_id), ("line_type", "=", "issued")],
            ["id", "invoice_date", "ref", "partner_id",
             "base_amount", "tax_amount", "total_amount"],
            limit=10000,
        )
        summary["issued"] = {
            "count": len(issued),
            "total_base": sum(r["base_amount"] for r in issued),
            "total_tax": sum(r["tax_amount"] for r in issued),
            "total_amount": sum(r["total_amount"] for r in issued),
        }
    if book_type in ("received", "all"):
        received = client.search_read(
            "l10n.es.vat.book.line",
            [("vat_book_id", "=", book_id), ("line_type", "=", "received")],
            ["id", "invoice_date", "ref", "partner_id",
             "base_amount", "tax_amount", "total_amount"],
            limit=10000,
        )
        summary["received"] = {
            "count": len(received),
            "total_base": sum(r["base_amount"] for r in received),
            "total_tax": sum(r["tax_amount"] for r in received),
            "total_amount": sum(r["total_amount"] for r in received),
        }

    if export_xlsx:
        try:
            xlsx = client.call("l10n.es.vat.book", "export_xlsx", [[book_id]])
            if isinstance(xlsx, str):
                xlsx = base64.b64decode(xlsx)
            summary["xlsx_b64"] = base64.b64encode(xlsx).decode("ascii")
        except OdooError as e:
            summary["xlsx_error"] = str(e)

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--period", required=True,
                        help="2026Q1, 2026-05 o 2026")
    parser.add_argument("--type", dest="book_type",
                        choices=["issued", "received", "all"], default="all")
    parser.add_argument("--company-id", type=int, default=1)
    parser.add_argument("--xlsx", action="store_true",
                        help="Incluye exportacion XLSX en base64 en el output")
    ns = parser.parse_args()

    client = OdooClient()
    result = generate_vat_book(
        client,
        period=ns.period,
        company_id=ns.company_id,
        book_type=ns.book_type,
        export_xlsx=ns.xlsx,
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
