#!/usr/bin/env python3
"""Calcula prorrata IVA de un ano fiscal: % deduccion definitivo.

Compara el % calculado con el provisional aplicado durante el ano y
devuelve la diferencia para regularizacion del 4T.

Identifica operaciones con/sin derecho a deduccion via tags fiscales
configurados en account.tax (prefijo `+sujeto deducible` y `+exento`).
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from _common import OdooError
from odoo_client import OdooClient


def _sum_by_tag(
    client: OdooClient,
    *,
    year: int,
    company_id: int,
    tag_pattern: str,
) -> float:
    domain = [
        ("date", ">=", f"{year}-01-01"),
        ("date", "<=", f"{year}-12-31"),
        ("parent_state", "=", "posted"),
        ("company_id", "=", company_id),
        ("tax_ids.tag_ids.name", "ilike", tag_pattern),
        ("display_type", "=", "product"),
    ]
    rg = client.call(
        "account.move.line", "read_group",
        [domain, ["balance:sum"], []],
    )
    if not rg:
        return 0.0
    return abs(rg[0].get("balance") or 0.0)


def compute_prorate(
    client: OdooClient,
    *,
    year: int,
    company_id: int = 1,
    provisional_pct: float | None = None,
) -> dict[str, Any]:
    with_right = _sum_by_tag(
        client, year=year, company_id=company_id,
        tag_pattern="sujeto deducible",
    )
    without_right = _sum_by_tag(
        client, year=year, company_id=company_id,
        tag_pattern="exento",
    )

    total = with_right + without_right
    if total == 0:
        return {
            "year": year,
            "company_id": company_id,
            "with_deduction_right": 0.0,
            "without_deduction_right": 0.0,
            "definitive_pct": None,
            "warning": "Sin operaciones encontradas - revisar tags fiscales",
        }

    definitive_pct = round((with_right / total) * 100, 2)

    result: dict[str, Any] = {
        "year": year,
        "company_id": company_id,
        "with_deduction_right": round(with_right, 2),
        "without_deduction_right": round(without_right, 2),
        "definitive_pct": definitive_pct,
    }

    if provisional_pct is not None:
        delta = round(definitive_pct - provisional_pct, 2)
        result["provisional_pct"] = provisional_pct
        result["delta_pct"] = delta
        result["regularizacion_required"] = abs(delta) > 0
        result["sign"] = "increase_deduction" if delta > 0 else "decrease_deduction"

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--company-id", type=int, default=1)
    parser.add_argument("--provisional",
                        type=float,
                        help="% prorrata provisional aplicado (para calc delta)")
    ns = parser.parse_args()

    client = OdooClient()
    result = compute_prorate(
        client,
        year=ns.year,
        company_id=ns.company_id,
        provisional_pct=ns.provisional,
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
