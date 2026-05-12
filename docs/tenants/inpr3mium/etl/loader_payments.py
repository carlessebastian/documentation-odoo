#!/usr/bin/env python3
"""Paso 7: carga `payments.jsonl` -> `account.payment` (filtrado).

708 payments Holded en el dump. Filtrados (MVP):
- documentType in {'invoice', 'creditnote'} = 113 docs
- 'purchase' (24) bloqueado hasta loader 4 (use --include-purchases tras)
- 'trans' (440), 'payroll' (105), 'entry' (26) = 571 docs son asientos
  manuales/transferencias internas, NO account.payment. Out of scope.

Salida: account.payment draft (NO postear, NO reconciliar).
Reconciliacion → Fase 5.5 cutover.

Ext_id `__holded__.payment_<id>`.

Uso:
    HOLDED_DUMP_DIR=... python3 loader_payments.py --dry-run
    HOLDED_DUMP_DIR=... python3 loader_payments.py
    # Tras loader 4 (purchases):
    HOLDED_DUMP_DIR=... python3 loader_payments.py --include-purchases

PYTHONPATH: `.claude/skills/odoo-functional-admin/scripts`.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from _payments_lib import load_payments, print_summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump-dir", type=Path,
                        default=Path(os.environ.get("HOLDED_DUMP_DIR", "")))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--include-purchases", action="store_true",
                        help="Incluye documentType=purchase (requiere loader 4 ejecutado).")
    args = parser.parse_args()

    if not args.dump_dir or not args.dump_dir.exists():
        print(f"ERROR: --dump-dir invalido: {args.dump_dir!r}", file=sys.stderr)
        return 2

    from odoo_client import OdooClient
    client = OdooClient()

    stats = load_payments(
        client, dump_dir=args.dump_dir,
        dry_run=args.dry_run, limit=args.limit,
        include_purchases=args.include_purchases,
    )
    print_summary(stats, args.dry_run)
    return 0 if stats.errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
