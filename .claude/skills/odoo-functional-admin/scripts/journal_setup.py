#!/usr/bin/env python3
"""Crea o actualiza un `account.journal`. Idempotente sobre `(company_id, code)`.

Si --auto-sequence, crea/asigna una `ir.sequence` con prefijo
`<CODE>/%(range_year)s/` para diarios de tipo sale/purchase.

Uso:
    python3 journal_setup.py --type sale --code VENT --company 2 \\
        --name "Customer Invoices" --auto-sequence --no-gap
"""
from __future__ import annotations

import argparse
import json
import sys

from _common import OdooError
from odoo_client import OdooClient


VALID_TYPES = ("sale", "purchase", "bank", "cash", "general")


def upsert_sequence_for_journal(
    client: OdooClient, code: str, company_id: int, no_gap: bool
) -> int:
    seq_code = f"account.journal.{code.lower()}"
    domain = [("code", "=", seq_code), ("company_id", "=", company_id)]
    existing = client.call("ir.sequence", "search", [domain], {"limit": 1})
    vals = {
        "name": f"{code} Sequence",
        "code": seq_code,
        "prefix": f"{code}/%(range_year)s/",
        "padding": 5,
        "implementation": "no_gap" if no_gap else "standard",
        "use_date_range": True,
        "company_id": company_id,
    }
    if existing:
        client.call("ir.sequence", "write", [[existing[0]], vals])
        return existing[0]
    return client.call("ir.sequence", "create", [vals])


def upsert_journal(
    client: OdooClient,
    *,
    type_: str,
    code: str,
    name: str,
    company_id: int,
    sequence_id: int | None,
    restrict_mode_hash_table: bool,
) -> tuple[int, str]:
    if type_ not in VALID_TYPES:
        raise OdooError(
            f"--type debe ser uno de {VALID_TYPES}, no {type_!r}."
        )
    if len(code) > 5:
        raise OdooError(
            f"El codigo de diario {code!r} excede los 5 caracteres permitidos."
        )
    domain = [("code", "=", code), ("company_id", "=", company_id)]
    existing = client.call("account.journal", "search", [domain], {"limit": 1})
    vals = {
        "name": name,
        "type": type_,
        "code": code,
        "company_id": company_id,
        "restrict_mode_hash_table": restrict_mode_hash_table,
    }
    if sequence_id:
        vals["sequence_id"] = sequence_id
    if existing:
        client.call("account.journal", "write", [[existing[0]], vals])
        return existing[0], "updated"
    rec_id = client.call("account.journal", "create", [vals])
    return rec_id, "created"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--type", required=True, choices=VALID_TYPES)
    parser.add_argument("--code", required=True, help="Maximo 5 caracteres")
    parser.add_argument("--name", required=True)
    parser.add_argument("--company", type=int, required=True)
    parser.add_argument(
        "--auto-sequence",
        action="store_true",
        help="Crea/asigna ir.sequence con prefix CODE/%(range_year)s/.",
    )
    parser.add_argument(
        "--no-gap",
        action="store_true",
        help="Usar implementation=no_gap (obligatorio para facturas ES).",
    )
    parser.add_argument(
        "--hash-chain",
        action="store_true",
        help="Activar restrict_mode_hash_table (irreversible).",
    )
    ns = parser.parse_args()

    client = OdooClient()

    seq_id = None
    if ns.auto_sequence and ns.type in ("sale", "purchase"):
        no_gap_default = ns.type == "sale" or ns.no_gap
        seq_id = upsert_sequence_for_journal(
            client, ns.code, ns.company, no_gap_default
        )

    rec_id, action = upsert_journal(
        client,
        type_=ns.type,
        code=ns.code,
        name=ns.name,
        company_id=ns.company,
        sequence_id=seq_id,
        restrict_mode_hash_table=ns.hash_chain,
    )
    json.dump(
        {
            "id": rec_id,
            "action": action,
            "code": ns.code,
            "type": ns.type,
            "company_id": ns.company,
            "sequence_id": seq_id,
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
