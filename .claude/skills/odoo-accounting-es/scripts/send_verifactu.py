#!/usr/bin/env python3
"""Envia una factura a Veri*Factu (auto-detecta Enterprise vs OCA).

Detecta `l10n_es_edi_verifactu` (Enterprise) o `l10n_es_verifactu_oca`
(OCA) y llama al metodo de envio correspondiente. Modo --dry-run para
simulacion sin tocar la AEAT.
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
            ("name", "in", ["l10n_es_edi_verifactu", "l10n_es_verifactu_oca"]),
            ("state", "=", "installed"),
        ],
        ["name"],
    )
    names = {r["name"] for r in rows}
    if "l10n_es_edi_verifactu" in names:
        return "enterprise"
    if "l10n_es_verifactu_oca" in names:
        return "oca"
    return None


def _method_name(provider: str) -> str:
    if provider == "enterprise":
        return "l10n_es_edi_verifactu_send"
    return "verifactu_send"


def _state_field(provider: str) -> str:
    if provider == "enterprise":
        return "l10n_es_edi_verifactu_state"
    return "verifactu_state"


def send_verifactu(
    client: OdooClient, invoice_id: int, *, dry_run: bool = False
) -> dict[str, Any]:
    provider = _detect_provider(client)
    if not provider:
        raise OdooError(
            "Ningun modulo Veri*Factu instalado "
            "(l10n_es_edi_verifactu o l10n_es_verifactu_oca)"
        )

    state_field = _state_field(provider)
    inv = client.search_read(
        "account.move",
        [("id", "=", invoice_id)],
        ["id", "name", "state", "move_type", state_field],
        limit=1,
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
            "current_verifactu_state": inv.get(state_field),
        }

    try:
        client.action("account.move", [invoice_id], _method_name(provider))
    except OdooError as e:
        # Veri*Factu devuelve [3000] cuando se reenvia una factura ya enviada;
        # tratarlo como noop.
        if "3000" in str(e) and "Duplicate" in str(e):
            return {
                "invoice_id": invoice_id,
                "provider": provider,
                "status": "already_sent",
            }
        raise

    after = client.search_read(
        "account.move",
        [("id", "=", invoice_id)],
        ["id", "name", state_field],
        limit=1,
    )[0]
    return {
        "invoice_id": invoice_id,
        "provider": provider,
        "verifactu_state": after.get(state_field),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--invoice-id", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    ns = parser.parse_args()

    client = OdooClient()
    result = send_verifactu(client, ns.invoice_id, dry_run=ns.dry_run)
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False, default=str)
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
