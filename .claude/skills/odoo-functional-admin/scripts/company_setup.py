#!/usr/bin/env python3
"""Crea o actualiza una `res.company`. Idempotente sobre `vat`.

Uso:
    python3 company_setup.py --name "Acme Iberia S.L." --vat ESB99999999 \\
        --parent-vat ESB12345678 --country ES --currency EUR
    python3 company_setup.py --name "Acme Iberia S.L." --vat ESB99999999 \\
        --parent-id 1
"""
from __future__ import annotations

import argparse
import json
import re
import sys

from _common import OdooError
from odoo_client import OdooClient


VAT_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]+$")


def normalize_vat(vat: str) -> str:
    """Normaliza VAT a mayusculas, sin espacios. No valida digito de control."""
    cleaned = vat.replace(" ", "").replace("-", "").upper()
    if not VAT_RE.match(cleaned):
        raise OdooError(
            f"VAT {vat!r} no parece valido. Formato esperado: codigo de pais "
            "(2 letras) + identificador (p.ej. ESB12345678)."
        )
    return cleaned


def detect_parent_cycle(
    client: OdooClient, target_id: int, candidate_parent_id: int
) -> bool:
    """True si poner `candidate_parent_id` como parent de `target_id` causa ciclo."""
    if target_id == candidate_parent_id:
        return True
    visited: set[int] = {target_id}
    cur = candidate_parent_id
    while cur:
        if cur in visited:
            return True
        visited.add(cur)
        rec = client.call(
            "res.company", "read", [[cur], ["parent_id"]]
        )
        if not rec or not rec[0]["parent_id"]:
            return False
        cur = rec[0]["parent_id"][0]
    return False


def resolve_country(client: OdooClient, code: str) -> int:
    res = client.call(
        "res.country",
        "search",
        [[("code", "=", code.upper())]],
        {"limit": 1},
    )
    if not res:
        raise OdooError(f"Pais {code!r} no encontrado en res.country.")
    return res[0]


def resolve_currency(client: OdooClient, name: str) -> int:
    res = client.call(
        "res.currency",
        "search",
        [[("name", "=", name.upper())]],
        {"limit": 1},
    )
    if not res:
        raise OdooError(f"Moneda {name!r} no encontrada en res.currency.")
    return res[0]


def resolve_parent(
    client: OdooClient,
    parent_id: int | None,
    parent_vat: str | None,
) -> int | None:
    if parent_id:
        return parent_id
    if parent_vat:
        vat = normalize_vat(parent_vat)
        res = client.call(
            "res.company",
            "search",
            [[("vat", "=", vat)]],
            {"limit": 1},
        )
        if not res:
            raise OdooError(
                f"No existe res.company con VAT {vat}. Crea primero el padre."
            )
        return res[0]
    return None


def upsert_company(
    client: OdooClient,
    *,
    name: str,
    vat: str,
    country_id: int,
    currency_id: int,
    parent_id: int | None = None,
) -> tuple[int, str]:
    vat = normalize_vat(vat)
    existing = client.call(
        "res.company",
        "search",
        [[("vat", "=", vat)]],
        {"limit": 1},
    )
    vals = {
        "name": name,
        "vat": vat,
        "country_id": country_id,
        "currency_id": currency_id,
    }
    if parent_id:
        vals["parent_id"] = parent_id

    if existing:
        rec_id = existing[0]
        if parent_id and detect_parent_cycle(client, rec_id, parent_id):
            raise OdooError(
                f"Asignar parent_id={parent_id} a la compania {rec_id} "
                "crearia un ciclo en la jerarquia."
            )
        client.call("res.company", "write", [[rec_id], vals])
        return rec_id, "updated"
    rec_id = client.call("res.company", "create", [vals])
    return rec_id, "created"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--vat", required=True, help="VAT/NIF, p.ej. ESB99999999")
    parser.add_argument("--country", default="ES", help="Codigo ISO (default ES)")
    parser.add_argument("--currency", default="EUR")
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--parent-id", type=int, help="ID numerico de la matriz")
    grp.add_argument("--parent-vat", help="VAT de la matriz (alternativa a --parent-id)")
    ns = parser.parse_args()

    client = OdooClient()
    country_id = resolve_country(client, ns.country)
    currency_id = resolve_currency(client, ns.currency)
    parent_id = resolve_parent(client, ns.parent_id, ns.parent_vat)

    rec_id, action = upsert_company(
        client,
        name=ns.name,
        vat=ns.vat,
        country_id=country_id,
        currency_id=currency_id,
        parent_id=parent_id,
    )
    json.dump(
        {"id": rec_id, "action": action, "name": ns.name,
         "parent_id": parent_id},
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
