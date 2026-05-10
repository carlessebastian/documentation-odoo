#!/usr/bin/env python3
"""Crea factura rectificativa via wizard account.move.reversal.

Modos:
  reverse: rectificativa por diferencias (credito puro). Default.
  modify : cancela la original y crea una nueva (sustitucion).
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from _common import OdooError
from odoo_client import OdooClient


def create_credit_note(
    client: OdooClient,
    invoice_id: int,
    *,
    mode: str = "reverse",
    date: str | None = None,
    reason: str | None = None,
    journal_id: int | None = None,
) -> dict[str, Any]:
    if mode not in ("reverse", "modify"):
        raise OdooError(f"mode invalido: {mode}")

    inv = client.search_read(
        "account.move",
        [("id", "=", invoice_id)],
        ["id", "name", "state", "move_type", "journal_id"],
        limit=1,
    )
    if not inv:
        raise OdooError(f"Factura {invoice_id} no encontrada")
    inv = inv[0]
    if inv["state"] != "posted":
        raise OdooError(
            f"Solo se rectifican facturas posteadas (estado actual: {inv['state']})"
        )

    journal_id = journal_id or inv["journal_id"][0]

    ctx = {"active_model": "account.move", "active_ids": [invoice_id]}
    vals: dict[str, Any] = {"journal_id": journal_id}
    if date:
        vals["date"] = date
    if reason:
        vals["reason"] = reason

    rev_id = client.call("account.move.reversal", "create", [vals], {"context": ctx})
    method = "reverse_moves" if mode == "reverse" else "modify_moves"
    client.call("account.move.reversal", method, [[rev_id]], {"context": ctx})

    new_moves = client.search_read(
        "account.move",
        [("reversed_entry_id", "=", invoice_id)],
        ["id", "name", "state", "move_type", "amount_total"],
        order="id desc",
        limit=5,
    )
    return {
        "original_invoice_id": invoice_id,
        "mode": mode,
        "created_moves": new_moves,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--invoice-id", type=int, required=True)
    parser.add_argument("--mode", choices=["reverse", "modify"], default="reverse")
    parser.add_argument("--date", help="YYYY-MM-DD de la rectificativa")
    parser.add_argument("--reason", required=True, help="Motivo (obligatorio)")
    parser.add_argument("--journal-id", type=int)
    ns = parser.parse_args()

    client = OdooClient()
    result = create_credit_note(
        client,
        ns.invoice_id,
        mode=ns.mode,
        date=ns.date,
        reason=ns.reason,
        journal_id=ns.journal_id,
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
