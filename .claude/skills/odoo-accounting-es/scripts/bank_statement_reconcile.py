#!/usr/bin/env python3
"""Reconciliacion automatica de lineas de extracto bancario contra facturas.

Heuristica:
1. Match por importe exacto (tolerancia centimos) Y partner.
2. Match por partner Y ref de la factura presente en payment_ref.
3. Match por amount_residual igual al amount de la statement_line.

Modo --dry-run muestra los matches propuestos sin ejecutar.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from _common import OdooError
from odoo_client import OdooClient


def _candidates_for_line(
    client: OdooClient, line: dict, tolerance: float = 0.05
) -> list[dict]:
    if not line.get("partner_id"):
        return []
    partner_id = line["partner_id"][0]
    amount = abs(line["amount"])
    is_inbound = line["amount"] > 0  # cobro de cliente

    move_type = "out_invoice" if is_inbound else "in_invoice"
    domain = [
        ("partner_id", "=", partner_id),
        ("state", "=", "posted"),
        ("payment_state", "in", ["not_paid", "partial"]),
        ("move_type", "=", move_type),
        ("amount_residual", ">=", amount - tolerance),
        ("amount_residual", "<=", amount + tolerance),
    ]
    return client.search_read(
        "account.move",
        domain,
        ["id", "name", "ref", "amount_total", "amount_residual",
         "invoice_date", "invoice_date_due"],
        order="invoice_date_due asc",
        limit=10,
    )


def _ref_match_score(stmt_ref: str, invoice_ref: str | None,
                     invoice_name: str | None) -> int:
    if not stmt_ref:
        return 0
    s = stmt_ref.upper()
    score = 0
    for candidate in (invoice_ref or "", invoice_name or ""):
        c = (candidate or "").upper()
        if not c:
            continue
        if c in s:
            score += 10
        elif len(c) >= 6 and c[-6:] in s:
            score += 5
    return score


def reconcile_statement(
    client: OdooClient,
    statement_id: int,
    *,
    dry_run: bool = False,
    tolerance: float = 0.05,
) -> dict[str, Any]:
    lines = client.search_read(
        "account.bank.statement.line",
        [("statement_id", "=", statement_id), ("is_reconciled", "=", False)],
        ["id", "date", "payment_ref", "amount", "partner_id",
         "ref", "narration"],
    )
    if not lines:
        return {
            "statement_id": statement_id,
            "lines_total": 0,
            "matched": 0,
            "matches": [],
        }

    proposals: list[dict] = []
    for ln in lines:
        cands = _candidates_for_line(client, ln, tolerance=tolerance)
        if not cands:
            proposals.append({
                "statement_line_id": ln["id"],
                "payment_ref": ln.get("payment_ref"),
                "amount": ln["amount"],
                "match": None,
                "reason": "no candidates",
            })
            continue
        # Re-rank candidates by ref match
        scored = sorted(
            cands,
            key=lambda inv: -_ref_match_score(
                ln.get("payment_ref") or "", inv.get("ref"), inv.get("name")
            ),
        )
        best = scored[0]
        score = _ref_match_score(
            ln.get("payment_ref") or "", best.get("ref"), best.get("name")
        )
        proposals.append({
            "statement_line_id": ln["id"],
            "payment_ref": ln.get("payment_ref"),
            "amount": ln["amount"],
            "match": {
                "invoice_id": best["id"],
                "invoice_name": best["name"],
                "amount_residual": best["amount_residual"],
                "ref_score": score,
            },
            "alternatives": len(scored) - 1,
        })

    if not dry_run:
        for prop in proposals:
            if not prop.get("match"):
                continue
            inv_id = prop["match"]["invoice_id"]
            sl_id = prop["statement_line_id"]
            # Buscar el aml receivable/payable de la factura que sigue abierto
            amls = client.search_read(
                "account.move.line",
                [("move_id", "=", inv_id),
                 ("account_id.account_type", "in",
                  ["asset_receivable", "liability_payable"]),
                 ("reconciled", "=", False)],
                ["id"],
                limit=1,
            )
            if not amls:
                prop["error"] = "no open receivable/payable line on invoice"
                continue
            try:
                client.call(
                    "account.bank.statement.line",
                    "set_line_bank_statement_line",
                    [[sl_id]],
                    {"counterpart_aml_dicts": [{"id": amls[0]["id"]}]},
                )
                prop["status"] = "reconciled"
            except OdooError as e:
                prop["error"] = str(e)

    matched = sum(1 for p in proposals if p.get("match"))
    return {
        "statement_id": statement_id,
        "dry_run": dry_run,
        "lines_total": len(lines),
        "matched": matched,
        "proposals": proposals,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--statement-id", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--tolerance", type=float, default=0.05,
                        help="Tolerancia en EUR para match de importe")
    ns = parser.parse_args()

    client = OdooClient()
    result = reconcile_statement(
        client, ns.statement_id,
        dry_run=ns.dry_run, tolerance=ns.tolerance,
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
