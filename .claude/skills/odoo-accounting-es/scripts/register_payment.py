#!/usr/bin/env python3
"""Registra cobro o pago de una factura via wizard account.payment.register."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from _common import OdooError
from odoo_client import OdooClient


def register_payment(
    client: OdooClient,
    invoice_id: int,
    *,
    journal_id: int | None = None,
    amount: float | None = None,
    payment_date: str | None = None,
    communication: str | None = None,
    payment_method_line_id: int | None = None,
) -> dict[str, Any]:
    invs = client.search_read(
        "account.move",
        [("id", "=", invoice_id)],
        ["id", "name", "state", "payment_state", "amount_residual",
         "move_type", "company_id"],
        limit=1,
    )
    if not invs:
        raise OdooError(f"Factura {invoice_id} no encontrada")
    inv = invs[0]
    if inv["state"] != "posted":
        raise OdooError(
            f"Factura {invoice_id} en estado {inv['state']}, no posted"
        )
    if inv["payment_state"] in ("paid", "reversed"):
        return {
            "id": inv["id"],
            "name": inv["name"],
            "payment_state": inv["payment_state"],
            "status": "noop",
        }

    if not journal_id:
        company_id = inv["company_id"][0]
        journals = client.search_read(
            "account.journal",
            [("type", "in", ["bank", "cash"]), ("company_id", "=", company_id)],
            ["id"], limit=1,
        )
        if not journals:
            raise OdooError("No hay diario bancario/caja disponible")
        journal_id = journals[0]["id"]

    ctx = {"active_model": "account.move", "active_ids": [invoice_id]}
    vals: dict[str, Any] = {"journal_id": journal_id}
    if amount is not None:
        vals["amount"] = amount
    if payment_date:
        vals["payment_date"] = payment_date
    if communication:
        vals["communication"] = communication
    if payment_method_line_id:
        vals["payment_method_line_id"] = payment_method_line_id

    reg_id = client.call("account.payment.register", "create", [vals], {"context": ctx})
    client.call(
        "account.payment.register",
        "action_create_payments",
        [[reg_id]],
        {"context": ctx},
    )

    after = client.search_read(
        "account.move",
        [("id", "=", invoice_id)],
        ["id", "name", "payment_state", "amount_residual"],
        limit=1,
    )[0]
    after["status"] = "registered"
    return after


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--invoice-id", type=int, required=True)
    parser.add_argument("--journal-id", type=int, help="Diario bancario/caja")
    parser.add_argument("--amount", type=float, help="Importe parcial (default: total pendiente)")
    parser.add_argument("--date", dest="payment_date", help="YYYY-MM-DD")
    parser.add_argument("--communication", help="Concepto del pago")
    ns = parser.parse_args()

    client = OdooClient()
    result = register_payment(
        client,
        ns.invoice_id,
        journal_id=ns.journal_id,
        amount=ns.amount,
        payment_date=ns.payment_date,
        communication=ns.communication,
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
