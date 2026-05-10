#!/usr/bin/env python3
"""Reportes financieros: P&L, Balance, Trial Balance comparativos multi-periodo.

Calcula via account.move.line directamente (no depende del motor
account.report). Soporta comparacion de hasta 4 periodos.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from _common import OdooError
from odoo_client import OdooClient


ACCOUNT_GROUPS = {
    "income": ("income", "income_other"),
    "expense": ("expense", "expense_depreciation", "expense_direct_cost"),
    "asset_current": ("asset_current", "asset_cash", "asset_receivable",
                      "asset_prepayments"),
    "asset_non_current": ("asset_non_current", "asset_fixed"),
    "liability_current": ("liability_current", "liability_payable"),
    "liability_non_current": ("liability_non_current",),
    "equity": ("equity", "equity_unaffected"),
}


def _balance_for_types(
    client: OdooClient, *, types: tuple[str, ...],
    date_from: str | None, date_to: str, company_id: int,
) -> float:
    domain = [
        ("account_id.account_type", "in", list(types)),
        ("parent_state", "=", "posted"),
        ("date", "<=", date_to),
        ("company_id", "=", company_id),
    ]
    if date_from:
        domain.append(("date", ">=", date_from))
    rg = client.call("account.move.line", "read_group",
                     [domain, ["balance:sum"], []])
    return rg[0]["balance"] if rg else 0.0


def profit_and_loss(
    client: OdooClient, *, periods: list[dict], company_id: int,
) -> dict[str, Any]:
    rows: list[dict] = []
    for label, dates in [("Income", "income"), ("Expense", "expense")]:
        row: dict[str, Any] = {"section": label, "values": {}}
        for p in periods:
            bal = _balance_for_types(
                client, types=ACCOUNT_GROUPS[dates],
                date_from=p["from"], date_to=p["to"], company_id=company_id,
            )
            row["values"][p["label"]] = round(-bal if dates == "income" else bal, 2)
        rows.append(row)

    profit_row: dict[str, Any] = {"section": "Net Profit", "values": {}}
    for p in periods:
        income = next(r for r in rows if r["section"] == "Income")["values"][p["label"]]
        expense = next(r for r in rows if r["section"] == "Expense")["values"][p["label"]]
        profit_row["values"][p["label"]] = round(income - expense, 2)
    rows.append(profit_row)

    return {
        "report": "Profit and Loss",
        "company_id": company_id,
        "periods": periods,
        "rows": rows,
    }


def balance_sheet(
    client: OdooClient, *, as_of_dates: list[str], company_id: int,
) -> dict[str, Any]:
    sections = [
        ("Current Assets", "asset_current"),
        ("Non-current Assets", "asset_non_current"),
        ("Current Liabilities", "liability_current"),
        ("Non-current Liabilities", "liability_non_current"),
        ("Equity", "equity"),
    ]
    rows: list[dict] = []
    for label, key in sections:
        row: dict[str, Any] = {"section": label, "values": {}}
        for d in as_of_dates:
            bal = _balance_for_types(
                client, types=ACCOUNT_GROUPS[key],
                date_from=None, date_to=d, company_id=company_id,
            )
            sign = -1 if "Liabilit" in label or label == "Equity" else 1
            row["values"][d] = round(bal * sign, 2)
        rows.append(row)
    return {
        "report": "Balance Sheet",
        "company_id": company_id,
        "as_of": as_of_dates,
        "rows": rows,
    }


def trial_balance(
    client: OdooClient, *, date_from: str, date_to: str, company_id: int,
) -> dict[str, Any]:
    rg = client.call(
        "account.move.line", "read_group",
        [[("parent_state", "=", "posted"),
          ("date", ">=", date_from),
          ("date", "<=", date_to),
          ("company_id", "=", company_id)],
         ["debit:sum", "credit:sum", "balance:sum"],
         ["account_id"]],
        {"orderby": "account_id"},
    )
    rows = [
        {
            "account": r["account_id"],
            "debit": round(r["debit"] or 0, 2),
            "credit": round(r["credit"] or 0, 2),
            "balance": round(r["balance"] or 0, 2),
        }
        for r in rg if (r.get("debit") or r.get("credit"))
    ]
    return {
        "report": "Trial Balance",
        "company_id": company_id,
        "period": {"from": date_from, "to": date_to},
        "row_count": len(rows),
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report",
                        choices=["pl", "balance", "trial"],
                        required=True)
    parser.add_argument("--from", dest="date_from",
                        help="YYYY-MM-DD (pl/trial)")
    parser.add_argument("--to", dest="date_to", required=True,
                        help="YYYY-MM-DD")
    parser.add_argument("--compare-from",
                        help="Periodo comparativo: YYYY-MM-DD inicio")
    parser.add_argument("--compare-to",
                        help="Periodo comparativo: YYYY-MM-DD fin")
    parser.add_argument("--company-id", type=int, default=1)
    ns = parser.parse_args()

    client = OdooClient()
    if ns.report == "pl":
        if not ns.date_from:
            raise OdooError("--from requerido para P&L")
        periods = [
            {"label": f"{ns.date_from}..{ns.date_to}",
             "from": ns.date_from, "to": ns.date_to}
        ]
        if ns.compare_from and ns.compare_to:
            periods.append({
                "label": f"{ns.compare_from}..{ns.compare_to}",
                "from": ns.compare_from, "to": ns.compare_to,
            })
        result = profit_and_loss(client, periods=periods,
                                 company_id=ns.company_id)
    elif ns.report == "balance":
        as_of = [ns.date_to]
        if ns.compare_to:
            as_of.append(ns.compare_to)
        result = balance_sheet(client, as_of_dates=as_of,
                               company_id=ns.company_id)
    else:
        if not ns.date_from:
            raise OdooError("--from requerido para trial balance")
        result = trial_balance(client, date_from=ns.date_from,
                               date_to=ns.date_to,
                               company_id=ns.company_id)

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False, default=str)
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
