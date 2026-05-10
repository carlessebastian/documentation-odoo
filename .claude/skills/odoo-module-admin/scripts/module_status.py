#!/usr/bin/env python3
"""Inspecciona `ir.module.module` via RPC. Sin escrituras, sin SSH.

Uso:
    python3 module_status.py --names l10n_es,l10n_es_aeat_mod303
    python3 module_status.py --names X --include-rdepends
    python3 module_status.py --names X --models
"""
from __future__ import annotations

import argparse
import json
import sys

from _common import OdooError
from odoo_client import OdooClient


def status(client: OdooClient, names: list[str]) -> list[dict]:
    fields = [
        "id",
        "name",
        "shortdesc",
        "state",
        "latest_version",
        "installed_version",
        "author",
        "license",
        "summary",
        "category_id",
        "application",
        "auto_install",
        "dependencies_id",
    ]
    return client.call(
        "ir.module.module",
        "search_read",
        [[("name", "in", names)]],
        {"fields": fields, "order": "name"},
    )


def reverse_dependencies(client: OdooClient, names: list[str]) -> dict[str, list[str]]:
    """Devuelve {modulo: [modulos_que_dependen_de_el_e_instalados]}."""
    deps = client.call(
        "ir.module.module.dependency",
        "search_read",
        [[("name", "in", names)]],
        {"fields": ["name", "module_id"]},
    )
    rdeps: dict[str, list[int]] = {n: [] for n in names}
    for d in deps:
        rdeps[d["name"]].append(d["module_id"][0])
    if not any(rdeps.values()):
        return {n: [] for n in names}
    all_module_ids = sorted({i for ids in rdeps.values() for i in ids})
    modules = client.call(
        "ir.module.module",
        "read",
        [all_module_ids, ["name", "state"]],
    )
    by_id = {m["id"]: m for m in modules}
    return {
        n: [
            by_id[i]["name"]
            for i in ids
            if by_id.get(i) and by_id[i]["state"] == "installed"
        ]
        for n, ids in rdeps.items()
    }


def list_models_defined_by(client: OdooClient, names: list[str]) -> dict[str, list[str]]:
    """Devuelve {modulo: [modelos_definidos_o_extendidos]}.

    Implementacion: ir.model.data filtra por module y model='ir.model'.
    """
    rows = client.call(
        "ir.model.data",
        "search_read",
        [[("module", "in", names), ("model", "=", "ir.model")]],
        {"fields": ["module", "name", "res_id"]},
    )
    out: dict[str, list[str]] = {n: [] for n in names}
    if not rows:
        return out
    model_ids = sorted({r["res_id"] for r in rows})
    models = client.call("ir.model", "read", [model_ids, ["model"]])
    by_id = {m["id"]: m["model"] for m in models}
    for r in rows:
        m = by_id.get(r["res_id"])
        if m:
            out[r["module"]].append(m)
    return {k: sorted(v) for k, v in out.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--names",
        required=True,
        help="CSV de nombres tecnicos de modulo.",
    )
    parser.add_argument("--include-rdepends", action="store_true",
                        help="Incluye modulos que dependen de cada uno.")
    parser.add_argument("--models", action="store_true",
                        help="Incluye modelos definidos por cada modulo.")
    ns = parser.parse_args()

    names = [n.strip() for n in ns.names.split(",") if n.strip()]
    if not names:
        raise OdooError("--names vacio")

    client = OdooClient()
    info = status(client, names)
    found_names = {row["name"] for row in info}
    missing = [n for n in names if n not in found_names]

    out: dict = {"modules": info, "missing": missing}
    if ns.include_rdepends:
        out["reverse_dependencies"] = reverse_dependencies(client, names)
    if ns.models:
        out["models_defined"] = list_models_defined_by(client, names)

    json.dump(out, sys.stdout, indent=2, ensure_ascii=False, default=str)
    print()
    return 0 if info else 4


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
