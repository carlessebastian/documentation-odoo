#!/usr/bin/env python3
"""Inspecciona la cuenta Holded SIN volcar nada a disco.

Cuenta resources, dimensiona el dump previsto, detecta inconsistencias
basicas (auth, conectividad, dominios). Util como preflight antes de
`holded_export.py`.

Uso:
    HOLDED_API_KEY=... python3 scripts/holded_inspect.py
    HOLDED_API_KEY=... python3 scripts/holded_inspect.py --json
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from typing import Any

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from _common import OdooEnvError, require_env  # type: ignore
from holded_client import (  # type: ignore
    DOC_TYPES,
    HoldedClient,
    HoldedError,
    iter_contacts,
    iter_dailyledger,
    iter_documents,
    iter_payments,
    iter_products,
    iter_remittances,
    iter_saleschannels,
    iter_services,
    iter_taxes,
    iter_treasuries,
    iter_warehouses,
    iter_expensesaccount,
    get_contact_groups,
    get_numbering_series,
)


def count(it) -> int:
    n = 0
    for _ in it:
        n += 1
    return n


def safe(label: str, fn, *args, **kwargs) -> dict[str, Any]:
    t0 = time.time()
    try:
        value = fn(*args, **kwargs)
        if hasattr(value, "__iter__") and not isinstance(value, (dict, list, str, bytes)):
            value = count(value)
        return {"label": label, "value": value, "elapsed_s": round(time.time() - t0, 3)}
    except HoldedError as e:
        return {"label": label, "error": str(e), "elapsed_s": round(time.time() - t0, 3)}
    except Exception as e:  # red, parsing, etc.
        return {"label": label, "error": f"{type(e).__name__}: {e}", "elapsed_s": round(time.time() - t0, 3)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect a Holded account without dumping.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")
    parser.add_argument("--skip-documents", action="store_true",
                        help="Skip per-docType document counts (faster).")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    try:
        require_env("HOLDED_API_KEY")
    except OdooEnvError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    client = HoldedClient()

    results: list[dict[str, Any]] = []
    results.append(safe("contacts", iter_contacts, client))
    results.append(safe("contact_groups (raw)", get_contact_groups, client))
    results.append(safe("products", iter_products, client))
    results.append(safe("services", iter_services, client))
    results.append(safe("warehouses", iter_warehouses, client))
    results.append(safe("treasuries", iter_treasuries, client))
    results.append(safe("expensesaccount", iter_expensesaccount, client))
    results.append(safe("taxes", iter_taxes, client))
    results.append(safe("saleschannels", iter_saleschannels, client))
    results.append(safe("payments", iter_payments, client))
    results.append(safe("remittances", iter_remittances, client))
    # Numbering series: 1 GET por docType.
    for t in DOC_TYPES:
        results.append(safe(f"numbering_series.{t}", get_numbering_series, client, t))
    # Documents por docType
    if not args.skip_documents:
        for t in DOC_TYPES:
            results.append(safe(f"documents.{t}", iter_documents, client, t))
    # Daily ledger: usar limites razonables para inspect (1 pagina muestra).
    results.append(safe("dailyledger (sample, 1 page)",
                        lambda c: count(iter_dailyledger(c)),  # ojo: sin filtros => puede tardar
                        client))

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0

    print(f"{'resource':<35} {'count/value':>18}   {'time':>6}  status")
    print("-" * 80)
    errors = 0
    for r in results:
        if "error" in r:
            errors += 1
            value_str = "ERROR"
            status = r["error"][:30]
        else:
            v = r["value"]
            if isinstance(v, int):
                value_str = f"{v:,}"
            elif isinstance(v, list):
                value_str = f"list({len(v)})"
            elif isinstance(v, dict):
                value_str = f"dict({len(v)})"
            else:
                value_str = str(v)[:20]
            status = "ok"
        print(f"{r['label']:<35} {value_str:>18}   {r['elapsed_s']:>6}s  {status}")
    print("-" * 80)
    print(f"{len(results)} checks, {errors} errors")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
