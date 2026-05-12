#!/usr/bin/env python3
"""Paso 3: carga `documents/invoice.jsonl` -> `account.move` out_invoice.

3.430 invoices Holded -> Odoo. Ext_id `__holded__.invoice_<id>`.
Idempotente: existing draft -> rewrite; existing posted -> skip.

Skip filters (no aborta el run, anotados en CSV):
- status=2 (cancelado en Holded, 2 docs en el dump).
- docNumber sin prefijo en {A-, AC-, AF-, KD-, FVU-, L-} (R- 6 docs).
- contact vacio (0 en el dump pero defensivo).

Resolvers usados:
- partner: lookup ir.model.data `__holded__.contact_<id>` (loader 1).
- journal: lookup por code (Fase 4.3 creo los 6 codes sale).
- account de linea: saleschannel id -> accountNum (saleschannels.jsonl)
  -> resolve_account (loaders 0a/0b precargaron 186 cuentas).
- tax: resolve_tax via [holded: <key>] (Fase 4.5b mapeo 16 taxes).
- product: lookup ir.model.data `__holded__.{product|service}_<id>`
  (loader 2) y luego template -> variant.

Uso:
    # dry-run primero (no escribe, emite CSV)
    HOLDED_DUMP_DIR=docs/tenants/inpr3mium/holded-export/2026-05-11 \
        python3 loader_invoices.py --dry-run --limit 10

    # real, sin postear (default: revisar visualmente en Odoo antes de post)
    HOLDED_DUMP_DIR=... python3 loader_invoices.py --limit 10

    # real + post (action_post automatica para docs con status=1 Holded)
    HOLDED_DUMP_DIR=... python3 loader_invoices.py --post

PYTHONPATH: `.claude/skills/odoo-functional-admin/scripts`.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from _invoices_lib import load_invoices, print_summary
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
    parser.add_argument(
        "--dump-dir", type=Path,
        default=Path(os.environ.get("HOLDED_DUMP_DIR", "")),
        help="Path a holded-export/<YYYY-MM-DD>/ (default: $HOLDED_DUMP_DIR)",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Valida sin escribir; emite CSV.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Procesa solo los primeros N docs.")
    parser.add_argument("--post", action="store_true",
                        help="Tras crear, llama action_post() en docs con status=1 Holded.")
    args = parser.parse_args()

    if not args.dump_dir or not args.dump_dir.exists():
        print(f"ERROR: --dump-dir invalido: {args.dump_dir!r}", file=sys.stderr)
        return 2

    from odoo_client import OdooClient
    client = OdooClient()

    etl_dir = Path(__file__).resolve().parent
    tax_rules = _load_tax_rules(etl_dir)
    resolvers = HoldedResolvers(client=client, tax_rules=tax_rules)

    stats = load_invoices(
        client, resolvers,
        dump_dir=args.dump_dir,
        dry_run=args.dry_run,
        limit=args.limit,
        post=args.post,
    )
    print_summary(stats, args.dry_run, args.post)
    return 0 if stats.errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
