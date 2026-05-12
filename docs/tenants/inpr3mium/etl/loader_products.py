#!/usr/bin/env python3
"""Paso 2: carga `products.jsonl` + `services.jsonl` -> `product.template`.

1.569 products + 440 services Holded -> Odoo. Ext_id por record:
`__holded__.product_<id>` o `__holded__.service_<id>`. Idempotente
via `ext_id_upsert.upsert`.

Resuelve por record:
- tax key (`s_iva_21`, `s_iva_10`, ...) -> `account.tax.id` via
  `HoldedResolvers.resolve_tax` (lookup `[holded: <key>]` en
  description, hecho por Fase 4.5b).
- `salesChannelId` -> `accountNum` -> `account.account.id` via
  `HoldedResolvers.resolve_account` (NO autocreate; las 38
  saleschannels las precargo paso 0b).
- `expAccountId` -> `accountNum` -> `account.account.id` igual via
  resolve_account (paso 0a precargo las 148 expense accounts).

Uso:
    # dry-run primero (recomendado: revisa CSV antes de escribir)
    HOLDED_DUMP_DIR=docs/tenants/inpr3mium/holded-export/2026-05-11 \
        python3 loader_products.py --dry-run

    # real
    HOLDED_DUMP_DIR=docs/tenants/inpr3mium/holded-export/2026-05-11 \
        python3 loader_products.py

PYTHONPATH debe incluir:
- `.claude/skills/odoo-functional-admin/scripts` (para `OdooClient`,
  `ext_id_upsert.upsert`).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml  # noqa: F401  -- usado solo si tax_reclassification existe

from _products_lib import load_products_and_services, print_summary
from holded_resolvers import HoldedResolvers


def _load_tax_rules(etl_dir: Path) -> dict:
    """Carga `tax_reclassification.yaml` si existe; si no, devuelve `{}`."""
    yaml_path = etl_dir / "tax_reclassification.yaml"
    if not yaml_path.exists():
        return {}
    try:
        import yaml as _yaml
        with yaml_path.open() as f:
            data = _yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        print(f"WARN: no pude leer {yaml_path}: {exc}", file=sys.stderr)
        return {}


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
        help="Procesa solo los primeros N records de CADA archivo (debug).",
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

    etl_dir = Path(__file__).resolve().parent
    tax_rules = _load_tax_rules(etl_dir)
    resolvers = HoldedResolvers(client=client, tax_rules=tax_rules)

    stats = load_products_and_services(
        client,
        resolvers,
        dump_dir=args.dump_dir,
        dry_run=args.dry_run,
        limit=args.limit,
    )
    print_summary(stats, args.dry_run)
    return 0 if stats.errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
