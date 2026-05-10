#!/usr/bin/env python3
"""Instala/activa idiomas en Odoo (`res.lang` via base.language.install).

Uso:
    python3 language_install.py --langs es_ES,ca_ES,it_IT
    python3 language_install.py --langs ca_ES --activate
"""
from __future__ import annotations

import argparse
import json
import re
import sys

from _common import OdooError
from odoo_client import OdooClient


LANG_CODE_RE = re.compile(r"^[a-z]{2,3}(_[A-Z]{2})?$")


def validate_lang_code(code: str) -> str:
    if not LANG_CODE_RE.match(code):
        raise OdooError(
            f"Codigo de idioma invalido: {code!r}. Formato esperado "
            "ISO tipo 'es_ES', 'ca_ES', 'it_IT', 'pt_BR'."
        )
    return code


def already_installed(client: OdooClient, code: str) -> dict | None:
    rec = client.call(
        "res.lang",
        "search_read",
        [[("code", "=", code)]],
        {"fields": ["id", "code", "name", "active"], "limit": 1},
    )
    return rec[0] if rec else None


def install_language(
    client: OdooClient, code: str, activate: bool
) -> tuple[int, str]:
    """Devuelve (lang_id, action)."""
    existing = already_installed(client, code)
    if existing and existing["active"]:
        return existing["id"], "already_active"
    if existing and not existing["active"]:
        if activate:
            client.call("res.lang", "write", [[existing["id"]], {"active": True}])
            return existing["id"], "reactivated"
        return existing["id"], "exists_but_inactive"

    # No existe -> wizard base.language.install
    wizard_id = client.call(
        "base.language.install",
        "create",
        [{"lang_ids": [(6, 0, [])], "overwrite": False}],
    )
    # En Odoo 19, el wizard tiene un campo Many2many `lang_ids` que apunta
    # a `res.lang`. Necesitamos primero el id de `res.lang` aunque este
    # inactivo. Si no existe en absoluto, usamos el metodo legacy con
    # `lang` (Char) como fallback.
    try:
        # Intento moderno: rellenar lang_ids
        lang_id = client.call(
            "res.lang",
            "search",
            [[("code", "=", code), ("active", "in", [True, False])]],
            {"limit": 1},
        )
        if lang_id:
            client.call(
                "base.language.install",
                "write",
                [[wizard_id], {"lang_ids": [(6, 0, lang_id)]}],
            )
            client.call("base.language.install", "lang_install", [[wizard_id]])
        else:
            # Fallback: campo `lang` como Char (versiones <16) — improbable en 19
            client.call(
                "base.language.install",
                "write",
                [[wizard_id], {"lang": code}],
            )
            client.call("base.language.install", "lang_install", [[wizard_id]])
    except Exception as exc:
        raise OdooError(
            f"Wizard base.language.install fallo para {code!r}: {exc}. "
            "Posiblemente el codigo no es uno de los soportados por Odoo "
            "(ver `res.lang` template list)."
        )

    rec = already_installed(client, code)
    if not rec:
        raise OdooError(f"Tras el wizard, {code!r} sigue sin aparecer en res.lang.")
    return rec["id"], "installed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--langs",
        required=True,
        help="CSV de codigos ISO de idioma.",
    )
    parser.add_argument(
        "--activate",
        action="store_true",
        help="Si el idioma existe pero esta inactivo, reactivarlo.",
    )
    ns = parser.parse_args()

    codes = [validate_lang_code(c.strip()) for c in ns.langs.split(",") if c.strip()]
    if not codes:
        raise OdooError("--langs vacio.")

    client = OdooClient()
    results = []
    for code in codes:
        lang_id, action = install_language(client, code, ns.activate)
        results.append({"code": code, "id": lang_id, "action": action})

    json.dump(results, sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
