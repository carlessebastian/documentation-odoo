#!/usr/bin/env python3
"""Paso 5: carga `documents/creditnote.jsonl` -> `account.move` out_refund.

678 docs AC- Holded (Abonos Ventas) -> Odoo. Ext_id
`__holded__.creditnote_<id>`. Idempotente.

Reusa indices y resolvers de loader 3. Si `doc.from.docType='invoice'`
y `from.id` resoluble (loader 3 cargó la factura origen), setea
`reversed_entry_id` para enlace UI Odoo.

Uso:
    HOLDED_DUMP_DIR=... python3 loader_creditnotes.py --dry-run
    HOLDED_DUMP_DIR=... python3 loader_creditnotes.py
    HOLDED_DUMP_DIR=... python3 loader_creditnotes.py --post

PYTHONPATH: `.claude/skills/odoo-functional-admin/scripts`.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from _creditnotes_lib import load_creditnotes, print_summary
from holded_resolvers import HoldedResolvers


def _load_tax_rules(etl_dir: Path) -> dict:
    yaml_path = etl_dir / "tax_reclassification.yaml"
    if not yaml_path.exists():
        return {}
    try:
        import yaml
        with yaml_path.open() as f:
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        print(f"WARN: no pude leer {yaml_path}: {exc}", file=sys.stderr)
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump-dir", type=Path,
                        default=Path(os.environ.get("HOLDED_DUMP_DIR", "")))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--post", action="store_true",
                        help="Postea solo status=1 (NUNCA status=3=review).")
    args = parser.parse_args()

    if not args.dump_dir or not args.dump_dir.exists():
        print(f"ERROR: --dump-dir invalido: {args.dump_dir!r}", file=sys.stderr)
        return 2

    from odoo_client import OdooClient
    client = OdooClient()

    etl_dir = Path(__file__).resolve().parent
    tax_rules = _load_tax_rules(etl_dir)
    resolvers = HoldedResolvers(client=client, tax_rules=tax_rules)

    stats = load_creditnotes(
        client, resolvers, dump_dir=args.dump_dir,
        dry_run=args.dry_run, limit=args.limit, post=args.post,
    )
    print_summary(stats, args.dry_run, args.post)
    return 0 if stats.errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
