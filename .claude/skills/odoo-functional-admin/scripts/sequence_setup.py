#!/usr/bin/env python3
"""Crea o actualiza una `ir.sequence`. Idempotente sobre `(company_id, code)`.

Uso:
    python3 sequence_setup.py --code account.move.kt --name "KT Customer Invoices" \\
        --prefix "KT/%(range_year)s/" --padding 5 --no-gap --use-date-range \\
        --company 2
"""
from __future__ import annotations

import argparse
import json
import sys

from _common import OdooError
from odoo_client import OdooClient


def upsert_sequence(
    client: OdooClient,
    *,
    code: str,
    name: str,
    prefix: str,
    padding: int,
    no_gap: bool,
    use_date_range: bool,
    company_id: int,
) -> tuple[int, str]:
    domain = [("code", "=", code), ("company_id", "=", company_id)]
    existing = client.call("ir.sequence", "search", [domain], {"limit": 1})
    vals = {
        "name": name,
        "code": code,
        "prefix": prefix,
        "padding": padding,
        "implementation": "no_gap" if no_gap else "standard",
        "use_date_range": use_date_range,
        "company_id": company_id,
    }
    if existing:
        client.call("ir.sequence", "write", [[existing[0]], vals])
        return existing[0], "updated"
    rec_id = client.call("ir.sequence", "create", [vals])
    return rec_id, "created"


def ensure_date_ranges(
    client: OdooClient, sequence_id: int, years: list[int]
) -> list[int]:
    """Crea ir.sequence.date_range para cada anyo si falta."""
    created: list[int] = []
    for y in years:
        existing = client.call(
            "ir.sequence.date_range",
            "search",
            [
                [
                    ("sequence_id", "=", sequence_id),
                    ("date_from", "=", f"{y}-01-01"),
                ]
            ],
            {"limit": 1},
        )
        if existing:
            continue
        rec_id = client.call(
            "ir.sequence.date_range",
            "create",
            [
                {
                    "sequence_id": sequence_id,
                    "date_from": f"{y}-01-01",
                    "date_to": f"{y}-12-31",
                    "number_next": 1,
                }
            ],
        )
        created.append(rec_id)
    return created


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--prefix", default="")
    parser.add_argument("--padding", type=int, default=5)
    parser.add_argument("--no-gap", action="store_true")
    parser.add_argument("--use-date-range", action="store_true")
    parser.add_argument("--company", type=int, required=True)
    parser.add_argument(
        "--ensure-years",
        default="",
        help="CSV de anyos a crear como date_range (p.ej. 2026,2027,2028).",
    )
    ns = parser.parse_args()

    client = OdooClient()
    rec_id, action = upsert_sequence(
        client,
        code=ns.code,
        name=ns.name,
        prefix=ns.prefix,
        padding=ns.padding,
        no_gap=ns.no_gap,
        use_date_range=ns.use_date_range,
        company_id=ns.company,
    )
    ranges_created: list[int] = []
    if ns.ensure_years and ns.use_date_range:
        years = [int(y.strip()) for y in ns.ensure_years.split(",") if y.strip()]
        ranges_created = ensure_date_ranges(client, rec_id, years)

    json.dump(
        {
            "id": rec_id,
            "action": action,
            "code": ns.code,
            "company_id": ns.company,
            "date_ranges_created": ranges_created,
        },
        sys.stdout,
        indent=2,
        ensure_ascii=False,
    )
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
