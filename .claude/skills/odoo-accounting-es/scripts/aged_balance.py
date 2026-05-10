#!/usr/bin/env python3
"""Aged receivables / payables - antigüedad de saldos por partner.

Agrupa lineas pendientes en buckets (no_vencido, 1-30, 31-60, 61-90, +90).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date, datetime
from typing import Any

from _common import OdooError
from odoo_client import OdooClient


BUCKETS = ["not_due", "1-30", "31-60", "61-90", "+90"]


def _bucket(due: str | None, today: date) -> str:
    if not due:
        return "not_due"
    d = date.fromisoformat(due[:10])
    delta = (today - d).days
    if delta <= 0:
        return "not_due"
    if delta <= 30:
        return "1-30"
    if delta <= 60:
        return "31-60"
    if delta <= 90:
        return "61-90"
    return "+90"


def aged_balance(
    client: OdooClient,
    *,
    account_type: str = "asset_receivable",
    today: date | None = None,
    company_id: int = 1,
    partner_filter: list | None = None,
) -> dict[str, Any]:
    if account_type not in ("asset_receivable", "liability_payable"):
        raise OdooError(f"account_type invalido: {account_type}")
    today = today or date.today()

    domain: list = [
        ("account_id.account_type", "=", account_type),
        ("parent_state", "=", "posted"),
        ("reconciled", "=", False),
        ("amount_residual", "!=", 0),
        ("company_id", "=", company_id),
    ]
    if partner_filter:
        domain.append(("partner_id", "in", partner_filter))

    rows = client.search_read(
        "account.move.line",
        domain,
        fields=[
            "id", "partner_id", "move_id", "date", "date_maturity",
            "amount_residual", "amount_residual_currency", "currency_id",
            "name",
        ],
        limit=100000,
    )

    by_partner: dict[int, dict[str, Any]] = defaultdict(
        lambda: {"name": "", "buckets": {b: 0.0 for b in BUCKETS}, "total": 0.0}
    )
    grand_total = {b: 0.0 for b in BUCKETS}
    grand_total_sum = 0.0

    for ln in rows:
        if not ln.get("partner_id"):
            continue
        pid = ln["partner_id"][0]
        pname = ln["partner_id"][1]
        b = _bucket(ln.get("date_maturity") or ln.get("date"), today)
        amount = ln["amount_residual"]
        # Para payable, amount_residual es negativo; lo convertimos a positivo
        # para presentacion (montos "que debemos").
        if account_type == "liability_payable":
            amount = -amount
        by_partner[pid]["name"] = pname
        by_partner[pid]["buckets"][b] += amount
        by_partner[pid]["total"] += amount
        grand_total[b] += amount
        grand_total_sum += amount

    return {
        "as_of": today.isoformat(),
        "account_type": account_type,
        "company_id": company_id,
        "buckets": BUCKETS,
        "by_partner": [
            {
                "partner_id": pid,
                "partner_name": data["name"],
                "buckets": data["buckets"],
                "total": data["total"],
            }
            for pid, data in sorted(
                by_partner.items(), key=lambda kv: -kv[1]["total"]
            )
        ],
        "totals": {"buckets": grand_total, "total": grand_total_sum},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--type",
        dest="account_type",
        choices=["receivable", "payable"],
        default="receivable",
    )
    parser.add_argument("--as-of", help="YYYY-MM-DD (default: hoy)")
    parser.add_argument("--company-id", type=int, default=1)
    parser.add_argument(
        "--partner-id",
        type=int,
        action="append",
        help="Filtra por partner (repetible)",
    )
    parser.add_argument(
        "--top", type=int, default=0,
        help="Mostrar solo los N partners con mayor saldo (0 = todos)",
    )
    ns = parser.parse_args()

    today = datetime.fromisoformat(ns.as_of).date() if ns.as_of else date.today()
    map_ = {"receivable": "asset_receivable", "payable": "liability_payable"}
    client = OdooClient()
    result = aged_balance(
        client,
        account_type=map_[ns.account_type],
        today=today,
        company_id=ns.company_id,
        partner_filter=ns.partner_id,
    )
    if ns.top > 0:
        result["by_partner"] = result["by_partner"][: ns.top]
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False, default=str)
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
