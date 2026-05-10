#!/usr/bin/env python3
"""Crea una API key para un usuario via wizard `res.users.apikeys.description`.

Limitaciones de Odoo:
- Una API key se devuelve UNA SOLA VEZ en clear text al crearla; despues
  solo se ve el hash. Este script imprime la key recien creada a stdout.
- Solo el propio usuario o admin puede crear keys para si mismo. Si el bot
  no es admin ni el propio usuario, la operacion fallara.
- Las keys NO se pueden recuperar; si el usuario la pierde, hay que crear
  una nueva.

Uso:
    python3 apikey_provision.py --login bot.contable@... --label automation
"""
from __future__ import annotations

import argparse
import json
import sys

from _common import OdooError
from odoo_client import OdooClient


def find_user(client: OdooClient, login: str | None, user_id: int | None) -> int:
    if user_id:
        return user_id
    if not login:
        raise OdooError("Indica --login o --user-id.")
    rec = client.call(
        "res.users",
        "search",
        [[("login", "=", login)]],
        {"limit": 1},
    )
    if not rec:
        raise OdooError(f"Usuario {login!r} no encontrado.")
    return rec[0]


def create_key(client: OdooClient, user_id: int, label: str) -> dict:
    """Devuelve {'key': str, 'apikey_id': int} si exito.

    Implementacion: usa res.users.apikeys._generate(scope, name).
    """
    try:
        result = client.call(
            "res.users.apikeys",
            "_generate",
            ["rpc", label],
            {},
        )
    except Exception as exc:
        raise OdooError(
            f"No se pudo crear la API key (probablemente el bot no tiene "
            f"permisos para hacerlo en nombre del user {user_id}): {exc}. "
            "Crea la key desde la UI: Preferences > Account Security > New API Key."
        )
    if isinstance(result, dict):
        return result
    if isinstance(result, str):
        return {"key": result}
    raise OdooError(f"Respuesta inesperada del wizard: {result!r}")


def list_keys(client: OdooClient, user_id: int) -> list[dict]:
    return client.call(
        "res.users.apikeys",
        "search_read",
        [[("user_id", "=", user_id)]],
        {"fields": ["id", "name", "create_date", "scope"], "order": "create_date desc"},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--login")
    parser.add_argument("--user-id", type=int)
    parser.add_argument(
        "--label",
        default="automation",
        help="Etiqueta humana (sin secretos).",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Solo listar keys existentes (no crea ninguna).",
    )
    ns = parser.parse_args()

    client = OdooClient()
    user_id = find_user(client, ns.login, ns.user_id)

    if ns.list_only:
        rows = list_keys(client, user_id)
        json.dump(
            {"user_id": user_id, "keys": rows},
            sys.stdout,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
        print()
        return 0

    info = create_key(client, user_id, ns.label)
    json.dump(
        {
            "user_id": user_id,
            "label": ns.label,
            "key_present_only_now": True,
            **info,
        },
        sys.stdout,
        indent=2,
        ensure_ascii=False,
    )
    print()
    print(
        "WARNING: la API key solo se muestra UNA VEZ. Guardala "
        "ahora en el gestor de secretos del usuario.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
