#!/usr/bin/env python3
"""Configura reglas de intercompany entre dos `res.company`.

Requiere modulo `account_intercompany` (Enterprise) o el OCA equivalente
`account_invoice_inter_company`. Si no esta instalado, deriva al skill
`odoo-module-admin`.

Uso:
    python3 intercompany_setup.py --src 2 --dst 3 --rule sale_purchase
"""
from __future__ import annotations

import argparse
import json
import sys

from _common import OdooError
from odoo_client import OdooClient


def is_module_installed(client: OdooClient, name: str) -> bool:
    rec = client.call(
        "ir.module.module",
        "search_read",
        [[("name", "=", name)]],
        {"fields": ["state"], "limit": 1},
    )
    return bool(rec) and rec[0]["state"] == "installed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=int, required=True, help="Company origen")
    parser.add_argument("--dst", type=int, required=True, help="Company destino")
    parser.add_argument(
        "--rule",
        default="sale_purchase",
        choices=("sale_purchase", "purchase", "no"),
        help="Que generar en el destino al crear venta en el origen.",
    )
    ns = parser.parse_args()

    client = OdooClient()
    has_oca = is_module_installed(client, "account_invoice_inter_company")
    has_ent = is_module_installed(client, "account_intercompany")
    if not (has_oca or has_ent):
        raise OdooError(
            "Ningun modulo de intercompany instalado. Instala "
            "`account_invoice_inter_company` (OCA) o `account_intercompany` "
            "(Enterprise) usando el skill `odoo-module-admin`."
        )

    field = "intercompany_generate_sales_orders" if has_ent else "rule_type"
    if has_ent:
        vals = {
            "intercompany_generate_sales_orders": ns.rule == "sale_purchase",
            "intercompany_generate_purchase_orders": ns.rule in ("sale_purchase", "purchase"),
            "intercompany_user_id": 1,  # admin como ejecutor
        }
    else:
        vals = {"rule_type": ns.rule}

    client.call("res.company", "write", [[ns.src], vals])

    json.dump(
        {
            "src": ns.src,
            "dst": ns.dst,
            "module": "account_intercompany" if has_ent else "account_invoice_inter_company",
            "applied": vals,
        },
        sys.stdout,
        indent=2,
        ensure_ascii=False,
    )
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
