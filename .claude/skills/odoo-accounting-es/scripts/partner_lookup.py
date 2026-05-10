#!/usr/bin/env python3
"""Busca partners (clientes/proveedores) en Odoo por VAT, nombre o email."""
from __future__ import annotations

import argparse
import json
import sys

from _common import OdooError
from odoo_client import OdooClient


def lookup(
    client: OdooClient,
    *,
    vat: str | None = None,
    name: str | None = None,
    email: str | None = None,
    limit: int = 20,
    only_companies: bool = False,
) -> list[dict]:
    domain: list = []
    if vat:
        domain.append(("vat", "ilike", vat))
    if name:
        domain.append(("name", "ilike", name))
    if email:
        domain.append(("email", "ilike", email))
    if only_companies:
        domain.append(("is_company", "=", True))
    if not domain:
        raise OdooError("Indique al menos --vat, --name o --email")

    fields = [
        "id", "name", "vat", "email", "phone", "country_id", "lang",
        "customer_rank", "supplier_rank", "credit", "debit",
        "property_payment_term_id",
    ]
    return client.search_read("res.partner", domain, fields=fields, limit=limit)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vat", help="VAT (NIF/CIF) parcial o completo")
    parser.add_argument("--name", help="Nombre o razon social parcial")
    parser.add_argument("--email", help="Email parcial")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--only-companies", action="store_true")
    ns = parser.parse_args()

    client = OdooClient()
    rows = lookup(
        client,
        vat=ns.vat,
        name=ns.name,
        email=ns.email,
        limit=ns.limit,
        only_companies=ns.only_companies,
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
