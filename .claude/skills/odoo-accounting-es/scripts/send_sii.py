#!/usr/bin/env python3
"""Envia una factura al SII de la AEAT (auto-detecta Enterprise vs OCA).

Detecta `l10n_es_edi_sii` (Enterprise) o `l10n_es_aeat_sii_oca` (OCA) y
llama al metodo apropiado. En Enterprise el envio normalmente lo hace un
cron; este script lo fuerza.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from _common import OdooError
from odoo_client import OdooClient


def _detect_provider(client: OdooClient) -> str | None:
    rows = client.search_read(
        "ir.module.module",
        [
            ("name", "in", ["l10n_es_edi_sii", "l10n_es_aeat_sii_oca"]),
            ("state", "=", "installed"),
        ],
        ["name"],
    )
    names = {r["name"] for r in rows}
    if "l10n_es_edi_sii" in names:
        return "enterprise"
    if "l10n_es_aeat_sii_oca" in names:
        return "oca"
    return None


def send_sii(
    client: OdooClient, invoice_id: int, *, dry_run: bool = False
) -> dict[str, Any]:
    provider = _detect_provider(client)
    if not provider:
        raise OdooError(
            "Ningun modulo SII instalado (l10n_es_edi_sii o l10n_es_aeat_sii_oca)"
        )

    fields = ["id", "name", "state", "move_type"]
    state_field = (
        "l10n_es_edi_sii_state" if provider == "enterprise" else "sii_state"
    )
    fields.append(state_field)

    inv = client.search_read(
        "account.move", [("id", "=", invoice_id)], fields, limit=1
    )
    if not inv:
        raise OdooError(f"Factura {invoice_id} no encontrada")
    inv = inv[0]
    if inv["state"] != "posted":
        raise OdooError(f"Factura no posteada (estado: {inv['state']})")

    if dry_run:
        return {
            "invoice_id": invoice_id,
            "provider": provider,
            "would_call": _method_name(provider),
            "current_sii_state": inv.get(state_field),
        }

    method = _method_name(provider)
    client.action("account.move", [invoice_id], method)

    after = client.search_read(
        "account.move", [("id", "=", invoice_id)],
        ["id", "name", state_field], limit=1,
    )[0]
    return {
        "invoice_id": invoice_id,
        "provider": provider,
        "method": method,
        "sii_state": after.get(state_field),
    }


def _method_name(provider: str) -> str:
    if provider == "enterprise":
        return "l10n_es_edi_sii_send_invoices"
    return "send_sii"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--invoice-id", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    ns = parser.parse_args()

    client = OdooClient()
    result = send_sii(client, ns.invoice_id, dry_run=ns.dry_run)
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False, default=str)
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
