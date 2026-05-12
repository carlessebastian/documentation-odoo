#!/usr/bin/env python3
"""Paso 9: PDFs Holded -> `ir.attachment` enlazado a `account.move`.

Itera `holded-export/<date>/pdfs/<doctype>/*.pdf` y adjunta cada PDF
al account.move correspondiente (lookup via ext_id
`__holded__.<doctype>_<holded_id>` creado por loaders 3/4/5).

Doctypes soportados: invoice, purchase, creditnote, purchaserefund.
Por defecto procesa los 4; pasar --doctype para limitar a uno.

Uso:
    # Solo invoices, dry-run primero
    HOLDED_DUMP_DIR=... python3 loader_pdfs.py --doctype invoice --dry-run

    # Real, todos los doctypes con PDFs en el dump
    HOLDED_DUMP_DIR=... python3 loader_pdfs.py

PYTHONPATH: `.claude/skills/odoo-functional-admin/scripts`.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from _pdfs_lib import DOCTYPE_TO_EXTID_PREFIX, load_pdfs_for_doctype, print_summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dump-dir", type=Path,
        default=Path(os.environ.get("HOLDED_DUMP_DIR", "")),
    )
    parser.add_argument(
        "--doctype",
        choices=list(DOCTYPE_TO_EXTID_PREFIX),
        default=None,
        help="Procesa solo el doctype especificado. Default: todos.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None,
                        help="Procesa solo los primeros N PDFs por doctype.")
    args = parser.parse_args()

    if not args.dump_dir or not args.dump_dir.exists():
        print(f"ERROR: --dump-dir invalido: {args.dump_dir!r}", file=sys.stderr)
        return 2

    from odoo_client import OdooClient
    client = OdooClient()

    doctypes = [args.doctype] if args.doctype else list(DOCTYPE_TO_EXTID_PREFIX)
    total_errors = 0
    for dt in doctypes:
        pdf_dir = args.dump_dir / "pdfs" / dt
        if not pdf_dir.exists():
            print(f"skip {dt}: no existe {pdf_dir}", file=sys.stderr)
            continue
        stats = load_pdfs_for_doctype(
            client, args.dump_dir, doctype=dt,
            dry_run=args.dry_run, limit=args.limit,
        )
        print_summary(stats, dt, args.dry_run)
        total_errors += stats.errors

    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
