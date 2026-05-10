#!/usr/bin/env python3
"""Busca productos en Odoo por default_code (SKU) o nombre."""
from __future__ import annotations

import argparse
import json
import sys

from _common import OdooError
from odoo_client import OdooClient


def lookup(
    client: OdooClient,
    *,
    code: str | None = None,
    name: str | None = None,
    limit: int = 20,
    only_active: bool = True,
) -> list[dict]:
    domain: list = []
    if code:
        domain.append(("default_code", "ilike", code))
    if name:
        domain.append(("name", "ilike", name))
    if only_active:
        domain.append(("active", "=", True))
    if not (code or name):
        raise OdooError("Indique al menos --code o --name")

    fields = [
        "id", "name", "default_code", "list_price", "standard_price",
        "type", "uom_id", "taxes_id", "supplier_taxes_id",
        "property_account_income_id", "property_account_expense_id",
        "categ_id",
    ]
    return client.search_read("product.product", domain, fields=fields, limit=limit)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code", help="default_code (SKU) parcial")
    parser.add_argument("--name", help="Nombre parcial")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--include-archived", action="store_true")
    ns = parser.parse_args()

    client = OdooClient()
    rows = lookup(
        client,
        code=ns.code,
        name=ns.name,
        limit=ns.limit,
        only_active=not ns.include_archived,
    )
    json.dump(rows, sys.stdout, indent=2, ensure_ascii=False, default=str)
    print()
    return 0 if rows else 4


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
