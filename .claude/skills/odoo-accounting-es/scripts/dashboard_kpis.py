#!/usr/bin/env python3
"""Dashboard de KPIs financieros: DSO, DPO, working capital, ratios.

Calcula KPIs estandar para un periodo y compania. Util para reporting
mensual o como input a dashboards externos (Metabase, Grafana).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from typing import Any

from _common import OdooError
from odoo_client import OdooClient


def _sum_balance(
    client: OdooClient,
    *,
    account_types: list[str],
    date_from: str | None = None,
    date_to: str | None = None,
    company_id: int = 1,
    only_open: bool = False,
) -> float:
    domain: list = [
        ("account_id.account_type", "in", account_types),
        ("parent_state", "=", "posted"),
        ("company_id", "=", company_id),
    ]
    if date_from:
        domain.append(("date", ">=", date_from))
    if date_to:
        domain.append(("date", "<=", date_to))
    if only_open:
        domain.append(("reconciled", "=", False))
    rg = client.call(
        "account.move.line", "read_group",
        [domain, ["balance:sum", "amount_residual:sum"], []],
    )
    if not rg:
        return 0.0
    if only_open:
        return rg[0].get("amount_residual") or 0.0
    return rg[0].get("balance") or 0.0


def compute_kpis(
    client: OdooClient,
    *,
    date_from: str,
    date_to: str,
    company_id: int = 1,
) -> dict[str, Any]:
    df = date.fromisoformat(date_from)
    dt = date.fromisoformat(date_to)
    days = (dt - df).days + 1

    receivables = _sum_balance(
        client,
        account_types=["asset_receivable"],
        date_to=date_to,
        company_id=company_id,
        only_open=True,
    )
    payables = -_sum_balance(
        client,
        account_types=["liability_payable"],
        date_to=date_to,
        company_id=company_id,
        only_open=True,
    )
    sales = -_sum_balance(
        client,
        account_types=["income", "income_other"],
        date_from=date_from,
        date_to=date_to,
        company_id=company_id,
    )
    purchases = _sum_balance(
        client,
        account_types=["expense", "expense_direct_cost"],
        date_from=date_from,
        date_to=date_to,
        company_id=company_id,
    )
    inventory = _sum_balance(
        client,
        account_types=["asset_current"],
        date_to=date_to,
        company_id=company_id,
    )
    cogs = _sum_balance(
        client,
        account_types=["expense_direct_cost"],
        date_from=date_from,
        date_to=date_to,
        company_id=company_id,
    )

    current_assets = _sum_balance(
        client,
        account_types=["asset_current", "asset_cash", "asset_receivable"],
        date_to=date_to,
        company_id=company_id,
    )
    current_liabilities = -_sum_balance(
        client,
        account_types=["liability_current", "liability_payable"],
        date_to=date_to,
        company_id=company_id,
    )

    cash = _sum_balance(
        client,
        account_types=["asset_cash"],
        date_to=date_to,
        company_id=company_id,
    )

    dso = (receivables / sales * days) if sales else None
    dpo = (payables / purchases * days) if purchases else None
    dio = (inventory / cogs * days) if cogs else None
    ccc = (
        (dso or 0) + (dio or 0) - (dpo or 0)
        if dso is not None and dpo is not None
        else None
    )
    working_capital = current_assets - current_liabilities
    quick_ratio = (
        (current_assets - inventory) / current_liabilities
        if current_liabilities
        else None
    )
    current_ratio = (
        current_assets / current_liabilities if current_liabilities else None
    )

    return {
        "period": {"from": date_from, "to": date_to, "days": days},
        "company_id": company_id,
        "raw": {
            "receivables_open": round(receivables, 2),
            "payables_open": round(payables, 2),
            "sales_period": round(sales, 2),
            "purchases_period": round(purchases, 2),
            "inventory_balance": round(inventory, 2),
            "cogs_period": round(cogs, 2),
            "current_assets": round(current_assets, 2),
            "current_liabilities": round(current_liabilities, 2),
            "cash_balance": round(cash, 2),
        },
        "kpis": {
            "DSO_days": round(dso, 1) if dso is not None else None,
            "DPO_days": round(dpo, 1) if dpo is not None else None,
            "DIO_days": round(dio, 1) if dio is not None else None,
            "CCC_days": round(ccc, 1) if ccc is not None else None,
            "working_capital": round(working_capital, 2),
            "quick_ratio": round(quick_ratio, 2) if quick_ratio is not None else None,
            "current_ratio": round(current_ratio, 2) if current_ratio is not None else None,
        },
    }


def _default_period() -> tuple[str, str]:
    today = date.today()
    first_of_month = today.replace(day=1)
    last_month_end = first_of_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    return last_month_start.isoformat(), last_month_end.isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    df, dt = _default_period()
    parser.add_argument("--from", dest="date_from", default=df,
                        help=f"YYYY-MM-DD (default: {df})")
    parser.add_argument("--to", dest="date_to", default=dt,
                        help=f"YYYY-MM-DD (default: {dt})")
    parser.add_argument("--company-id", type=int, default=1)
    ns = parser.parse_args()

    client = OdooClient()
    result = compute_kpis(
        client,
        date_from=ns.date_from,
        date_to=ns.date_to,
        company_id=ns.company_id,
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
