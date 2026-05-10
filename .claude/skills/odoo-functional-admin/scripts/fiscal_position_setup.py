#!/usr/bin/env python3
"""Crea o actualiza una `account.fiscal.position` desde un preset.

Presets: intra_eu, export, rec_eq.

Uso:
    python3 fiscal_position_setup.py --preset intra_eu --company 2
    python3 fiscal_position_setup.py --preset rec_eq --company 2
"""
from __future__ import annotations

import argparse
import json
import sys

from _common import OdooError
from odoo_client import OdooClient


PRESETS = {
    "intra_eu": {
        "name": "Regimen intracomunitario",
        "auto_apply": True,
        "vat_required": True,
        "country_group_xmlid": "base.europe",
        "tax_pairs": [
            # (src_name, dst_name, type_tax_use)
            ("S_IVA21B", "S_IVA0_IC", "sale"),
            ("S_IVA10B", "S_IVA0_IC", "sale"),
            ("S_IVA4B", "S_IVA0_IC", "sale"),
            ("P_IVA21_IC_BC", "P_IVA21_IC_BI", "purchase"),
        ],
    },
    "export": {
        "name": "Exportacion fuera UE",
        "auto_apply": True,
        "vat_required": False,
        "country_group_xmlid": None,
        "tax_pairs": [
            ("S_IVA21B", "S_IVA0_E", "sale"),
            ("S_IVA10B", "S_IVA0_E", "sale"),
            ("S_IVA4B", "S_IVA0_E", "sale"),
        ],
    },
    "rec_eq": {
        "name": "Recargo de Equivalencia",
        "auto_apply": False,
        "vat_required": False,
        "country_group_xmlid": None,
        "tax_pairs": [
            ("S_IVA21B", "S_IVA21S_RE", "sale"),
            ("S_IVA10B", "S_IVA10S_RE", "sale"),
            ("S_IVA4B", "S_IVA4S_RE", "sale"),
        ],
    },
}


def resolve_country_group(client: OdooClient, xmlid: str | None) -> int | None:
    if not xmlid:
        return None
    module, name = xmlid.split(".", 1)
    rec = client.call(
        "ir.model.data",
        "search_read",
        [
            [
                ("module", "=", module),
                ("name", "=", name),
                ("model", "=", "res.country.group"),
            ]
        ],
        {"fields": ["res_id"], "limit": 1},
    )
    if not rec:
        raise OdooError(f"res.country.group {xmlid!r} no encontrado.")
    return rec[0]["res_id"]


def resolve_tax(
    client: OdooClient, name_tag: str, type_tax_use: str, company_id: int
) -> int | None:
    rec = client.call(
        "account.tax",
        "search",
        [
            [
                ("name", "ilike", name_tag),
                ("type_tax_use", "=", type_tax_use),
                ("company_id", "=", company_id),
            ]
        ],
        {"limit": 1},
    )
    return rec[0] if rec else None


def upsert_fiscal_position(
    client: OdooClient, *, preset: str, company_id: int
) -> tuple[int, str]:
    if preset not in PRESETS:
        raise OdooError(f"Preset desconocido: {preset!r}. Use {list(PRESETS)}.")
    spec = PRESETS[preset]

    country_group_id = resolve_country_group(client, spec["country_group_xmlid"])
    tax_lines: list[tuple] = []
    missing: list[str] = []
    for src, dst, type_use in spec["tax_pairs"]:
        src_id = resolve_tax(client, src, type_use, company_id)
        dst_id = resolve_tax(client, dst, type_use, company_id)
        if not src_id or not dst_id:
            missing.append(f"{src}/{dst} ({type_use})")
            continue
        tax_lines.append((0, 0, {"tax_src_id": src_id, "tax_dest_id": dst_id}))

    if missing:
        raise OdooError(
            "Impuestos no encontrados (probablemente l10n_es no instalado o "
            "preset no aplicable a esta company): " + ", ".join(missing)
        )

    domain = [
        ("name", "=", spec["name"]),
        ("company_id", "=", company_id),
    ]
    existing = client.call("account.fiscal.position", "search", [domain], {"limit": 1})
    vals = {
        "name": spec["name"],
        "company_id": company_id,
        "auto_apply": spec["auto_apply"],
        "vat_required": spec["vat_required"],
        "tax_ids": [(5,)] + tax_lines,  # reset + recreate
    }
    if country_group_id:
        vals["country_group_id"] = country_group_id

    if existing:
        client.call("account.fiscal.position", "write", [[existing[0]], vals])
        return existing[0], "updated"
    rec_id = client.call("account.fiscal.position", "create", [vals])
    return rec_id, "created"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preset",
        required=True,
        choices=tuple(PRESETS),
    )
    parser.add_argument("--company", type=int, required=True)
    ns = parser.parse_args()

    client = OdooClient()
    rec_id, action = upsert_fiscal_position(
        client, preset=ns.preset, company_id=ns.company
    )
    json.dump(
        {
            "id": rec_id,
            "action": action,
            "preset": ns.preset,
            "company_id": ns.company,
        },
        sys.stdout,
        indent=2,
        ensure_ascii=False,
    )
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
