#!/usr/bin/env python3
"""Operaciones en lote sobre account.move: post, payment, cancel, send.

Acepta IDs o un dominio JSON. Acciones soportadas:
  --action post    -> action_post
  --action payment -> wizard account.payment.register (--journal-id)
  --action cancel  -> button_cancel
  --action send    -> message_post_with_template (--template-id)
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from _common import OdooError
from odoo_client import OdooClient


def _resolve_ids(client: OdooClient, ids: list[int] | None,
                 domain_json: str | None) -> list[int]:
    if ids:
        return ids
    if domain_json:
        domain = json.loads(domain_json)
        rows = client.search_read("account.move", domain, ["id"], limit=10000)
        return [r["id"] for r in rows]
    raise OdooError("Se requiere --ids o --domain")


def batch_post(client: OdooClient, ids: list[int]) -> dict[str, Any]:
    failures: list[dict] = []
    success: list[int] = []
    for i in ids:
        try:
            client.action("account.move", [i], "action_post")
            success.append(i)
        except OdooError as e:
            failures.append({"id": i, "error": str(e)})
    return {"action": "post", "total": len(ids),
            "ok": len(success), "failed": len(failures), "failures": failures}


def batch_payment(client: OdooClient, ids: list[int],
                  *, journal_id: int, group_payment: bool = True,
                  payment_date: str | None = None) -> dict[str, Any]:
    if not ids:
        return {"action": "payment", "total": 0}
    ctx = {"active_model": "account.move", "active_ids": ids}
    vals: dict[str, Any] = {"journal_id": journal_id, "group_payment": group_payment}
    if payment_date:
        vals["payment_date"] = payment_date
    reg_id = client.call("account.payment.register", "create", [vals],
                         {"context": ctx})
    client.call("account.payment.register", "action_create_payments",
                [[reg_id]], {"context": ctx})
    return {"action": "payment", "total": len(ids),
            "register_id": reg_id, "group_payment": group_payment}


def batch_cancel(client: OdooClient, ids: list[int]) -> dict[str, Any]:
    failures: list[dict] = []
    success: list[int] = []
    for i in ids:
        try:
            client.action("account.move", [i], "button_cancel")
            success.append(i)
        except OdooError as e:
            failures.append({"id": i, "error": str(e)})
    return {"action": "cancel", "total": len(ids),
            "ok": len(success), "failed": len(failures), "failures": failures}


def batch_send(client: OdooClient, ids: list[int],
               *, template_id: int) -> dict[str, Any]:
    failures: list[dict] = []
    success: list[int] = []
    for i in ids:
        try:
            client.action("account.move", [i], "message_post_with_template",
                          ctx={"template_id": template_id})
            success.append(i)
        except OdooError as e:
            failures.append({"id": i, "error": str(e)})
    return {"action": "send", "total": len(ids), "template_id": template_id,
            "ok": len(success), "failed": len(failures), "failures": failures}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action",
                        choices=["post", "payment", "cancel", "send"],
                        required=True)
    parser.add_argument("--ids", help="IDs separados por coma")
    parser.add_argument("--domain", help="Dominio JSON p.ej. '[[\"state\",\"=\",\"draft\"]]'")
    parser.add_argument("--journal-id", type=int,
                        help="Para --action payment")
    parser.add_argument("--payment-date",
                        help="YYYY-MM-DD (--action payment)")
    parser.add_argument("--no-group", action="store_true",
                        help="Para --action payment: NO agrupar en un solo pago")
    parser.add_argument("--template-id", type=int,
                        help="Para --action send")
    parser.add_argument("--limit", type=int, default=0,
                        help="Maximo de registros (0 = sin limite)")
    ns = parser.parse_args()

    client = OdooClient()
    ids_list = (
        [int(x) for x in ns.ids.split(",") if x.strip()] if ns.ids else None
    )
    ids = _resolve_ids(client, ids_list, ns.domain)
    if ns.limit > 0:
        ids = ids[: ns.limit]

    if ns.action == "post":
        result = batch_post(client, ids)
    elif ns.action == "payment":
        if not ns.journal_id:
            raise OdooError("--journal-id requerido para --action payment")
        result = batch_payment(client, ids,
                               journal_id=ns.journal_id,
                               group_payment=not ns.no_group,
                               payment_date=ns.payment_date)
    elif ns.action == "cancel":
        result = batch_cancel(client, ids)
    else:
        if not ns.template_id:
            raise OdooError("--template-id requerido para --action send")
        result = batch_send(client, ids, template_id=ns.template_id)

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False, default=str)
    print()
    return 0 if result.get("failed", 0) == 0 else 6


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
