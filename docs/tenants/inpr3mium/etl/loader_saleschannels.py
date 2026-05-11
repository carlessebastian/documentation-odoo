#!/usr/bin/env python3
"""Paso 0b: carga subcuentas 70X desde Holded `saleschannels.jsonl`.

38 sales channels -> `account.account` hijas del PGCE Pymes
correspondiente (700/705/708/709 via fallback de
`derive_pgce_parent`). Ext_id `__holded__.account_<accountNum>` para
idempotencia.

Uso:
    # dry-run primero
    python3 loader_saleschannels.py --dry-run

    # real
    python3 loader_saleschannels.py

PYTHONPATH debe incluir `.claude/skills/odoo-functional-admin/scripts`.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from _loader_common import load_accounts, print_summary

SOURCE = "saleschannels"


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
        help="Procesa solo los primeros N records (debug).",
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

    stats = load_accounts(
        client,
        dump_dir=args.dump_dir,
        source=SOURCE,
        dry_run=args.dry_run,
        limit=args.limit,
    )
    print_summary(SOURCE, stats, args.dry_run)
    return 0 if stats.errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
