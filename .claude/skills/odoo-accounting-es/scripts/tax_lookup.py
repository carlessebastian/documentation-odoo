#!/usr/bin/env python3
"""Busca impuestos (account.tax) por nombre y/o uso (sale/purchase)."""
from __future__ import annotations

import argparse
import json
import sys

from _common import OdooError
from odoo_client import OdooClient


def lookup(
    client: OdooClient,
    *,
    name: str | None = None,
    use: str | None = None,
    country_code: str = "ES",
    limit: int = 50,
) -> list[dict]:
    domain: list = [("active", "=", True)]
    if name:
        domain.append(("name", "ilike", name))
    if use:
        domain.append(("type_tax_use", "=", use))
    if country_code:
        domain.append(("country_id.code", "=", country_code))

    fields = [
        "id", "name", "amount", "amount_type", "type_tax_use",
        "tax_group_id", "price_include", "country_id",
    ]
    return client.search_read("account.tax", domain, fields=fields, limit=limit)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", help="Nombre o XML-ID parcial (p.ej. S_IVA21B)")
    parser.add_argument(
        "--use",
        choices=["sale", "purchase", "none"],
        help="Filtra por type_tax_use",
    )
    parser.add_argument("--country", default="ES")
    parser.add_argument("--limit", type=int, default=50)
    ns = parser.parse_args()

    client = OdooClient()
    rows = lookup(
        client,
        name=ns.name,
        use=ns.use,
        country_code=ns.country,
        limit=ns.limit,
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
