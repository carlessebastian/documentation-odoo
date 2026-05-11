#!/usr/bin/env python3
"""Crea o actualiza un `account.journal`. Idempotente sobre `(company_id, code)`.

En Odoo 19, account.journal ya no tiene `sequence_id` Many2one a
`ir.sequence`: el campo `code` (max 5 chars) es directamente el prefijo
de la numeración, y `refund_sequence` (bool) habilita numeración
dedicada para abonos en el mismo diario.

Uso:
    python3 journal_setup.py --type sale --code A- --company 1 \\
        --name "Facturas Ventas" --refund-sequence
"""
from __future__ import annotations

import argparse
import json
import sys

from _common import OdooError
from odoo_client import OdooClient


VALID_TYPES = ("sale", "purchase", "bank", "cash", "general")


def upsert_journal(
    client: OdooClient,
    *,
    type_: str,
    code: str,
    name: str,
    company_id: int,
    refund_sequence: bool,
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
        "refund_sequence": refund_sequence,
        "restrict_mode_hash_table": restrict_mode_hash_table,
    }
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
        "--refund-sequence",
        action="store_true",
        help="Numeracion dedicada para out_refund / in_refund en este diario.",
    )
    parser.add_argument(
        "--hash-chain",
        action="store_true",
        help="Activar restrict_mode_hash_table (irreversible, sellar moves).",
    )
    ns = parser.parse_args()

    client = OdooClient()

    rec_id, action = upsert_journal(
        client,
        type_=ns.type,
        code=ns.code,
        name=ns.name,
        company_id=ns.company,
        refund_sequence=ns.refund_sequence,
        restrict_mode_hash_table=ns.hash_chain,
    )
    json.dump(
        {
            "id": rec_id,
            "action": action,
            "code": ns.code,
            "type": ns.type,
            "company_id": ns.company,
            "refund_sequence": ns.refund_sequence,
            "restrict_mode_hash_table": ns.hash_chain,
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
