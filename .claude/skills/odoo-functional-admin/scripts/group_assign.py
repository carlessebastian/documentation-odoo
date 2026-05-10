#!/usr/bin/env python3
"""Anyade o quita grupos de un usuario sin tocar el resto.

Uso:
    python3 group_assign.py --login [email protected] \\
        --add account.group_account_invoice \\
        --remove sales_team.group_sale_salesman
    python3 group_assign.py --user-id 7 --add base.group_multi_company
"""
from __future__ import annotations

import argparse
import json
import sys

from _common import OdooError
from odoo_client import OdooClient


def resolve_group(client: OdooClient, xmlid: str) -> int:
    module, name = xmlid.split(".", 1)
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
        raise OdooError(f"Grupo {xmlid!r} no encontrado.")
    return rec[0]["res_id"]


def resolve_user(
    client: OdooClient, login: str | None, user_id: int | None
) -> int:
    if user_id:
        return user_id
    if not login:
        raise OdooError("Indica --login o --user-id.")
    rec = client.call(
        "res.users",
        "search",
        [[("login", "=", login)]],
        {"limit": 1},
    )
    if not rec:
        raise OdooError(f"Usuario con login {login!r} no encontrado.")
    return rec[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--login")
    parser.add_argument("--user-id", type=int)
    parser.add_argument(
        "--add",
        default="",
        help="CSV de XML-IDs a anyadir.",
    )
    parser.add_argument(
        "--remove",
        default="",
        help="CSV de XML-IDs a quitar.",
    )
    ns = parser.parse_args()

    client = OdooClient()
    uid = resolve_user(client, ns.login, ns.user_id)
    if uid == 1:
        raise OdooError(
            "Se ha solicitado modificar grupos de admin (uid 1). "
            "Confirma explicitamente con el usuario antes de continuar; "
            "este script se detiene por seguridad."
        )

    add_xmlids = [g.strip() for g in ns.add.split(",") if g.strip()]
    remove_xmlids = [g.strip() for g in ns.remove.split(",") if g.strip()]
    add_ids = [resolve_group(client, x) for x in add_xmlids]
    remove_ids = [resolve_group(client, x) for x in remove_xmlids]

    ops = [(4, gid) for gid in add_ids] + [(3, gid) for gid in remove_ids]
    if not ops:
        raise OdooError("Nada que hacer; indica --add y/o --remove.")

    client.call("res.users", "write", [[uid], {"groups_id": ops}])
    json.dump(
        {
            "user_id": uid,
            "added": list(zip(add_xmlids, add_ids)),
            "removed": list(zip(remove_xmlids, remove_ids)),
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
