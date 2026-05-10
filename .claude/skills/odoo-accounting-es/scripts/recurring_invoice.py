#!/usr/bin/env python3
"""Genera facturas recurrentes desde una plantilla draft.

Patron sin sale_subscription: una factura draft sirve como plantilla;
cada periodo se duplica con copy() y se setea fecha + ref.

Soporta frecuencias: monthly, quarterly, yearly. Detecta y evita
duplicados por `ref` (idempotente).
"""
from __future__ import annotations

import argparse
import json
import sys
from calendar import monthrange
from datetime import date
from typing import Any

from _common import OdooError
from odoo_client import OdooClient


def _next_period_label(today: date, frequency: str) -> str:
    if frequency == "monthly":
        return today.strftime("%Y-%m")
    if frequency == "quarterly":
        return f"{today.year}Q{(today.month - 1) // 3 + 1}"
    if frequency == "yearly":
        return f"{today.year}"
    raise OdooError(f"Frequency invalido: {frequency}")


def _period_dates(today: date, frequency: str) -> tuple[date, date]:
    if frequency == "monthly":
        last = monthrange(today.year, today.month)[1]
        return today.replace(day=1), today.replace(day=last)
    if frequency == "quarterly":
        q = (today.month - 1) // 3
        start_m = q * 3 + 1
        end_m = start_m + 2
        last = monthrange(today.year, end_m)[1]
        return date(today.year, start_m, 1), date(today.year, end_m, last)
    if frequency == "yearly":
        return date(today.year, 1, 1), date(today.year, 12, 31)
    raise OdooError(f"Frequency invalido: {frequency}")


def generate_recurring(
    client: OdooClient,
    *,
    template_id: int,
    frequency: str,
    today: date | None = None,
    ref_prefix: str = "REC",
    post: bool = False,
) -> dict[str, Any]:
    today = today or date.today()
    label = _next_period_label(today, frequency)
    period_start, period_end = _period_dates(today, frequency)

    template = client.search_read(
        "account.move",
        [("id", "=", template_id), ("state", "=", "draft")],
        ["id", "partner_id", "ref", "move_type"],
        limit=1,
    )
    if not template:
        raise OdooError(
            f"Plantilla {template_id} no encontrada o no esta en draft"
        )
    template = template[0]

    new_ref = f"{ref_prefix}-{template['partner_id'][0]}-{label}"

    existing = client.search_read(
        "account.move",
        [("ref", "=", new_ref),
         ("partner_id", "=", template["partner_id"][0]),
         ("move_type", "=", template["move_type"])],
        ["id", "state", "name"],
        limit=1,
    )
    if existing:
        return {
            "template_id": template_id,
            "period": label,
            "ref": new_ref,
            "existing_invoice": existing[0],
            "status": "already_generated",
        }

    new_id = client.call(
        "account.move", "copy",
        [[template_id]],
        {"default": {
            "invoice_date": period_start.isoformat(),
            "invoice_date_due": period_end.isoformat(),
            "ref": new_ref,
        }},
    )
    if isinstance(new_id, list):
        new_id = new_id[0]

    if post:
        client.action("account.move", [new_id], "action_post")

    final = client.search_read(
        "account.move", [("id", "=", new_id)],
        ["id", "name", "ref", "state", "amount_total"],
        limit=1,
    )[0]
    final["status"] = "generated"
    return {
        "template_id": template_id,
        "period": label,
        "invoice": final,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template-id", type=int, required=True,
                        help="ID de account.move (draft) a usar como plantilla")
    parser.add_argument("--frequency", choices=["monthly", "quarterly", "yearly"],
                        default="monthly")
    parser.add_argument("--ref-prefix", default="REC")
    parser.add_argument("--today", help="YYYY-MM-DD (default: hoy)")
    parser.add_argument("--post", action="store_true")
    ns = parser.parse_args()

    today = date.fromisoformat(ns.today) if ns.today else date.today()
    client = OdooClient()
    result = generate_recurring(
        client,
        template_id=ns.template_id,
        frequency=ns.frequency,
        today=today,
        ref_prefix=ns.ref_prefix,
        post=ns.post,
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
