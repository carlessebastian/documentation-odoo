#!/usr/bin/env python3
"""Crea (o actualiza) una factura en Odoo de forma idempotente y la postea.

Idempotencia: busca por (ref, partner_id, move_type) antes de crear. Si la
factura existe en estado `draft`, la actualiza; si esta `posted`, la
respeta y devuelve `already_posted`.

Codigos de impuesto en `lines[*].tax_codes`: nombres tipo "S_IVA21B",
"P_IRPF15", etc. (ver `references/localizacion-espana.md`).

Lee payload JSON desde --file o stdin. Ver `assets/invoice_template.json`.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from _common import OdooError
from odoo_client import OdooClient


def _resolve_partner(client: OdooClient, vat: str | None, partner_id: int | None) -> int:
    if partner_id:
        return partner_id
    if not vat:
        raise OdooError("Se requiere partner_vat o partner_id")
    rows = client.search_read(
        "res.partner", [("vat", "=", vat)], ["id"], limit=1
    )
    if not rows:
        raise OdooError(f"Partner con VAT {vat} no encontrado")
    return rows[0]["id"]


def _resolve_journal(client: OdooClient, journal_id: int | None, move_type: str) -> int:
    if journal_id:
        return journal_id
    jtype = "sale" if move_type.startswith("out_") else "purchase"
    rows = client.search_read(
        "account.journal", [("type", "=", jtype)], ["id"], limit=1
    )
    if not rows:
        raise OdooError(f"Diario {jtype} no encontrado")
    return rows[0]["id"]


def _resolve_taxes(client: OdooClient, codes: list[str], use: str) -> list[int]:
    if not codes:
        return []
    rows = client.search_read(
        "account.tax",
        [("name", "in", codes), ("type_tax_use", "=", use)],
        ["id", "name"],
    )
    found = {r["name"] for r in rows}
    missing = [c for c in codes if c not in found]
    if missing:
        raise OdooError(f"Impuestos no encontrados (use={use}): {missing}")
    return [r["id"] for r in rows]


def create_or_update_invoice(client: OdooClient, payload: dict) -> dict[str, Any]:
    move_type = payload.get("move_type", "out_invoice")
    if move_type not in ("out_invoice", "out_refund", "in_invoice", "in_refund"):
        raise OdooError(f"move_type invalido: {move_type}")

    partner_id = _resolve_partner(
        client, payload.get("partner_vat"), payload.get("partner_id")
    )
    journal_id = _resolve_journal(client, payload.get("journal_id"), move_type)
    ref = payload.get("ref")
    if not ref:
        raise OdooError("'ref' es obligatorio para idempotencia")

    tax_use = "sale" if move_type.startswith("out_") else "purchase"
    invoice_lines: list[tuple] = []
    for ln in payload.get("lines", []):
        line_vals: dict[str, Any] = {
            "name": ln["name"],
            "quantity": ln.get("qty", ln.get("quantity", 1)),
            "price_unit": ln["price_unit"],
        }
        if ln.get("product_default_code"):
            prod = client.search_read(
                "product.product",
                [("default_code", "=", ln["product_default_code"])],
                ["id"], limit=1,
            )
            if prod:
                line_vals["product_id"] = prod[0]["id"]
        tax_ids = _resolve_taxes(client, ln.get("tax_codes", []), tax_use)
        if tax_ids:
            line_vals["tax_ids"] = [(6, 0, tax_ids)]
        if ln.get("discount") is not None:
            line_vals["discount"] = ln["discount"]
        if ln.get("account_id"):
            line_vals["account_id"] = ln["account_id"]
        invoice_lines.append((0, 0, line_vals))

    base_vals: dict[str, Any] = {
        "move_type": move_type,
        "partner_id": partner_id,
        "journal_id": journal_id,
        "ref": ref,
    }
    for k in ("invoice_date", "invoice_date_due", "fiscal_position_id",
              "currency_id", "narration"):
        if payload.get(k) is not None:
            base_vals[k] = payload[k]

    existing = client.search_read(
        "account.move",
        [("ref", "=", ref), ("partner_id", "=", partner_id),
         ("move_type", "=", move_type)],
        ["id", "state", "name"], limit=1,
    )

    if existing and existing[0]["state"] == "posted":
        return {
            "id": existing[0]["id"],
            "name": existing[0]["name"],
            "status": "already_posted",
        }

    if existing and existing[0]["state"] == "draft":
        invoice_id = existing[0]["id"]
        client.write("account.move", [invoice_id], base_vals)
        client.write(
            "account.move",
            [invoice_id],
            {"invoice_line_ids": [(5, 0, 0)] + invoice_lines},
        )
        status = "updated"
    else:
        base_vals["invoice_line_ids"] = invoice_lines
        invoice_id = client.create("account.move", base_vals)
        status = "created"

    if payload.get("post"):
        client.action("account.move", [invoice_id], "action_post")

    final = client.search_read(
        "account.move",
        [("id", "=", invoice_id)],
        ["id", "name", "state", "amount_untaxed", "amount_tax",
         "amount_total", "amount_residual", "payment_state"],
        limit=1,
    )[0]
    final["status"] = status
    return final


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", help="Path a JSON con payload")
    parser.add_argument("--stdin", action="store_true",
                        help="Leer payload JSON de stdin")
    parser.add_argument("--post", action="store_true",
                        help="Postear (action_post) tras crear/actualizar")
    parser.add_argument("--dry-run", action="store_true",
                        help="Imprime payload resuelto sin tocar Odoo")
    ns = parser.parse_args()

    if ns.file:
        with open(ns.file, encoding="utf-8") as fh:
            payload = json.load(fh)
    elif ns.stdin:
        payload = json.load(sys.stdin)
    else:
        print("error: se requiere --file o --stdin", file=sys.stderr)
        return 1

    if ns.post:
        payload["post"] = True

    if ns.dry_run:
        json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return 0

    client = OdooClient()
    result = create_or_update_invoice(client, payload)
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False, default=str)
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
