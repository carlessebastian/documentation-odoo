#!/usr/bin/env python3
"""Importa un extracto bancario (CAMT.053, OFX, QIF, CSV, Norma43) a Odoo.

Detecta el formato por extension del archivo y delega al wizard
account.statement.import. Devuelve los IDs de los account.bank.statement
creados.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from typing import Any

from _common import OdooError
from odoo_client import OdooClient


EXTENSION_MAP = {
    ".xml": "camt",
    ".camt": "camt",
    ".camt053": "camt",
    ".ofx": "ofx",
    ".qfx": "ofx",
    ".qif": "qif",
    ".csv": "csv",
    ".n43": "n43",
    ".aeb43": "n43",
}


def import_statement(
    client: OdooClient,
    *,
    file_path: str,
    journal_id: int,
) -> dict[str, Any]:
    if not os.path.isfile(file_path):
        raise OdooError(f"Archivo no encontrado: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    fmt = EXTENSION_MAP.get(ext)
    if not fmt:
        raise OdooError(
            f"Extension {ext} no reconocida. Soportadas: {sorted(EXTENSION_MAP)}"
        )

    with open(file_path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("ascii")

    ctx = {"journal_id": journal_id}
    attachment_vals = {
        "name": os.path.basename(file_path),
        "datas": b64,
    }

    # account.statement.import existe en Enterprise (17+) y como wizard
    # en OCA. El nombre exacto del modelo puede variar segun version.
    wiz_model = _detect_wizard_model(client)

    wiz_id = client.call(
        wiz_model,
        "create",
        [{"attachment_ids": [(0, 0, attachment_vals)]}],
        {"context": ctx},
    )

    action = client.call(
        wiz_model, "import_file_button", [[wiz_id]], {"context": ctx}
    )

    statement_ids: list[int] = []
    if isinstance(action, dict):
        domain = action.get("domain") or []
        res_id = action.get("res_id")
        if res_id:
            statement_ids = [res_id]
        elif domain:
            stmts = client.search_read(
                "account.bank.statement", domain, ["id"], limit=50
            )
            statement_ids = [s["id"] for s in stmts]

    return {
        "wizard_id": wiz_id,
        "wizard_model": wiz_model,
        "format": fmt,
        "statement_ids": statement_ids,
    }


def _detect_wizard_model(client: OdooClient) -> str:
    candidates = ["account.statement.import", "account.bank.statement.import"]
    rows = client.search_read(
        "ir.model",
        [("model", "in", candidates)],
        ["model"],
    )
    if not rows:
        raise OdooError(
            "No hay wizard de importacion bancaria instalado "
            "(esperado account.statement.import o account.bank.statement.import)"
        )
    available = {r["model"] for r in rows}
    for c in candidates:
        if c in available:
            return c
    raise OdooError(f"Wizard no disponible. Encontrados: {available}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, help="Path del archivo de extracto")
    parser.add_argument("--journal-id", type=int, required=True,
                        help="ID del diario bancario destino")
    ns = parser.parse_args()

    client = OdooClient()
    result = import_statement(client, file_path=ns.file, journal_id=ns.journal_id)
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False, default=str)
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
