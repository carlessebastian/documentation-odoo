#!/usr/bin/env python3
"""Retro-fix: inyecta nota Holded en `res.partner.comment` para partners
ya cargados por `loader_partners.py` antes de que la nota fuera parte
del flujo.

Selecciona partners con:
  - ext_id que arranque por `__holded__.contact_` (excluye baseline + manual)
  - `ref` poblado (= code Holded original)
  - `vat` vacio (= code no se promovio a VAT field)

Idempotente: si el `comment` ya contiene el marker, salta el partner.

Uso:
    # dry-run primero
    python3 retrofit_holded_code_note.py --dry-run

    # real
    python3 retrofit_holded_code_note.py

PYTHONPATH debe incluir `.claude/skills/odoo-functional-admin/scripts`.
"""
from __future__ import annotations

import argparse
import sys

from _partners_lib import (
    _holded_code_note,
    has_holded_note,
)


EXT_MODULE = "__holded__"
BATCH_SIZE = 200


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Reporta partners afectados sin escribir.",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Procesa solo los primeros N partners (debug).",
    )
    args = parser.parse_args()

    from odoo_client import OdooClient
    client = OdooClient()

    # 1. Buscar ext_ids `__holded__.contact_*` -> mapear a res_id
    ext_ids = client.call(
        "ir.model.data", "search_read",
        [[
            ("module", "=", EXT_MODULE),
            ("name", "=like", "contact_%"),
            ("model", "=", "res.partner"),
        ]],
        {"fields": ["res_id", "name"]},
    )
    res_ids = sorted({r["res_id"] for r in ext_ids})
    print(f"[retrofit] {len(ext_ids)} ext_ids -> {len(res_ids)} partners únicos")

    # 2. Para cada partner, leer ref / vat / comment
    fields = ["id", "ref", "vat", "comment", "name", "country_id"]
    partners: list[dict] = []
    for i in range(0, len(res_ids), BATCH_SIZE):
        chunk = res_ids[i : i + BATCH_SIZE]
        partners.extend(client.call("res.partner", "read", [chunk, fields]))

    # 3. Filtrar candidatos: ref truthy, vat falsy
    candidates = [p for p in partners if p.get("ref") and not p.get("vat")]
    print(f"[retrofit] {len(candidates)} candidatos con ref + sin vat")

    if args.limit:
        candidates = candidates[: args.limit]

    stats = {
        "total": len(candidates),
        "would_update": 0,
        "updated": 0,
        "skipped_already_noted": 0,
        "errors": 0,
    }

    for p in candidates:
        if has_holded_note(p.get("comment")):
            stats["skipped_already_noted"] += 1
            continue
        note = _holded_code_note(p["ref"])
        if args.dry_run:
            stats["would_update"] += 1
            if stats["would_update"] <= 5:
                cc = p["country_id"][1] if p.get("country_id") else "?"
                print(
                    f"  - id={p['id']} ref={p['ref']!r} country={cc} "
                    f"name={p['name'][:50]!r}"
                )
            continue
        try:
            client.call("res.partner", "write", [[p["id"]], {"comment": note}])
            stats["updated"] += 1
        except Exception as exc:
            stats["errors"] += 1
            print(f"  ERROR id={p['id']}: {exc}", file=sys.stderr)

    print()
    print(f"[retrofit {'DRY-RUN' if args.dry_run else 'REAL'}]")
    for k, v in stats.items():
        print(f"  {k:30s}: {v}")
    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
