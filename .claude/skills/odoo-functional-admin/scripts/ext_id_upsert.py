#!/usr/bin/env python3
"""Upsert idempotente por `ir.model.data` XML-ID.

Si el XML-ID existe -> write() con los nuevos vals.
Si no existe       -> create() + registro en ir.model.data.

Uso:
    python3 ext_id_upsert.py --xmlid __custom__.user_maria \\
        --model res.users \\
        --vals '{"name": "Maria Pons", "login": "[email protected]"}'
"""
from __future__ import annotations

import argparse
import json
import re
import sys

from _common import OdooError
from odoo_client import OdooClient


XMLID_RE = re.compile(r"^[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*$", re.IGNORECASE)


def parse_xmlid(xmlid: str) -> tuple[str, str]:
    """Devuelve (modulo, name) o lanza OdooError si invalido."""
    if not XMLID_RE.match(xmlid):
        raise OdooError(
            f"XML-ID invalido: {xmlid!r}. Formato esperado: 'modulo.nombre' "
            "(letras, digitos, guion bajo)."
        )
    module, name = xmlid.split(".", 1)
    return module, name


def upsert(
    client: OdooClient,
    xmlid: str,
    model: str,
    vals: dict,
    noupdate: bool = False,
) -> tuple[int, str]:
    """Upsert. Devuelve (res_id, action) con action en {'created', 'updated'}."""
    module, name = parse_xmlid(xmlid)
    existing = client.call(
        "ir.model.data",
        "search_read",
        [[("module", "=", module), ("name", "=", name)]],
        {"fields": ["res_id", "model"], "limit": 1},
    )
    if existing:
        rec = existing[0]
        if rec["model"] != model:
            raise OdooError(
                f"XML-ID {xmlid} ya existe pero apunta al modelo "
                f"{rec['model']!r}, no a {model!r}."
            )
        client.call(model, "write", [[rec["res_id"]], vals])
        return rec["res_id"], "updated"
    rec_id = client.call(model, "create", [vals])
    client.call(
        "ir.model.data",
        "create",
        [
            {
                "module": module,
                "name": name,
                "model": model,
                "res_id": rec_id,
                "noupdate": noupdate,
            }
        ],
    )
    return rec_id, "created"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xmlid", required=True, help="modulo.nombre")
    parser.add_argument("--model", required=True, help="p.ej. res.users")
    parser.add_argument(
        "--vals",
        required=True,
        help="JSON con los campos a escribir/crear",
    )
    parser.add_argument(
        "--noupdate",
        action="store_true",
        help="Marcar el XML-ID como noupdate (no se sobrescribe en upgrade).",
    )
    ns = parser.parse_args()

    try:
        vals = json.loads(ns.vals)
    except json.JSONDecodeError as exc:
        raise OdooError(f"--vals no es JSON valido: {exc}") from exc
    if not isinstance(vals, dict):
        raise OdooError("--vals debe ser un objeto JSON (dict).")

    client = OdooClient()
    rec_id, action = upsert(client, ns.xmlid, ns.model, vals, ns.noupdate)
    json.dump(
        {"id": rec_id, "action": action, "xmlid": ns.xmlid, "model": ns.model},
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
