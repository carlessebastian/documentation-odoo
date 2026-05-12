#!/usr/bin/env python3
"""Paso 1: carga `contacts.jsonl` -> `res.partner`.

3.363 contacts Holded mergeados por `code` (CIF/NIF) en ~3.175 partners
Odoo. Dedup por `(countryCode, code)`; ranks customer/supplier OR'd
entre dups. Ext_id `__holded__.contact_<id>` para CADA contact (los
dups apuntan al mismo `res_id` que el canonical).

Tambien crea el placeholder `__holded__.contact__unknown` ("Cliente
historico no identificado") al que apuntan los ~1.149 docs con
contactId no resoluble.

Uso:
    # dry-run primero
    python3 loader_partners.py --dry-run

    # real
    python3 loader_partners.py

PYTHONPATH debe incluir `.claude/skills/odoo-functional-admin/scripts`
para que `OdooClient` y `ext_id_upsert.upsert` sean importables.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from _partners_lib import load_partners, print_summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dump-dir",
        type=Path,
        default=Path(os.environ.get("HOLDED_DUMP_DIR", "")),
        help="Path a holded-export/<YYYY-MM-DD>/ (default: $HOLDED_DUMP_DIR)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Valida resolucion sin escribir; emite CSV report.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Procesa solo los primeros N contacts (debug).",
    )
    args = parser.parse_args()

    if not args.dump_dir or not args.dump_dir.exists():
        print(
            f"ERROR: --dump-dir invalido o ausente: {args.dump_dir!r}. "
            "Pasalo via flag o seteando HOLDED_DUMP_DIR.",
            file=sys.stderr,
        )
        return 2

    from odoo_client import OdooClient
    client = OdooClient()

    stats = load_partners(
        client,
        dump_dir=args.dump_dir,
        dry_run=args.dry_run,
        limit=args.limit,
    )
    print_summary(stats, args.dry_run)
    return 0 if stats.errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
