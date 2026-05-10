#!/usr/bin/env python3
"""Auditoria de `ir.model.access` y `ir.rule` para un modelo.

Uso:
    python3 access_rule_audit.py --model res.partner
    python3 access_rule_audit.py --model crm.lead --group sales_team.group_sale_salesman
"""
from __future__ import annotations

import argparse
import json
import sys

from _common import OdooError
from odoo_client import OdooClient


def list_access(client: OdooClient, model: str) -> list[dict]:
    return client.call(
        "ir.model.access",
        "search_read",
        [[("model_id.model", "=", model)]],
        {
            "fields": [
                "id",
                "name",
                "group_id",
                "perm_read",
                "perm_write",
                "perm_create",
                "perm_unlink",
                "active",
            ],
            "order": "group_id, name",
        },
    )


def list_rules(client: OdooClient, model: str, group_xmlid: str | None) -> list[dict]:
    domain: list = [("model_id.model", "=", model), ("active", "=", True)]
    if group_xmlid:
        module, name = group_xmlid.split(".", 1)
        rec = client.call(
            "ir.model.data",
            "search_read",
            [
                [
                    ("module", "=", module),
                    ("name", "=", name),
                    ("model", "=", "res.groups"),
                ]
            ],
            {"fields": ["res_id"], "limit": 1},
        )
        if not rec:
            raise OdooError(f"Grupo {group_xmlid!r} no encontrado.")
        domain.append(("groups", "in", [rec[0]["res_id"]]))
    return client.call(
        "ir.rule",
        "search_read",
        [domain],
        {
            "fields": [
                "id",
                "name",
                "groups",
                "domain_force",
                "perm_read",
                "perm_write",
                "perm_create",
                "perm_unlink",
                "global",
            ],
            "order": "global desc, id",
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Modelo, p.ej. res.partner")
    parser.add_argument(
        "--group",
        help="(Opcional) XML-ID de grupo para filtrar reglas.",
    )
    ns = parser.parse_args()

    client = OdooClient()
    out = {
        "model": ns.model,
        "ir_model_access": list_access(client, ns.model),
        "ir_rule": list_rules(client, ns.model, ns.group),
    }
    json.dump(out, sys.stdout, indent=2, ensure_ascii=False, default=str)
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
