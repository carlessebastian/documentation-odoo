#!/usr/bin/env python3
"""Lee/escribe `ir.config_parameter` (parametros del sistema).

Uso:
    python3 settings_param.py get web.base.url
    python3 settings_param.py set web.base.url https://erp.example.com
    python3 settings_param.py list --prefix mail.
    python3 settings_param.py delete legacy.unused.key
"""
from __future__ import annotations

import argparse
import json
import re
import sys

from _common import OdooError
from odoo_client import OdooClient


KEY_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_.\-]*$")
PROTECTED_KEYS = {
    "database.uuid",
    "database.create_date",
    "database.expiration_date",
    "database.expiration_reason",
    "database.secret",
    "database.enterprise_code",
}


def validate_key(key: str) -> str:
    if not KEY_RE.match(key):
        raise OdooError(
            f"Clave invalida: {key!r}. Solo letras, digitos, '.', '_', '-'."
        )
    if key in PROTECTED_KEYS:
        raise OdooError(
            f"La clave {key!r} esta protegida; no se puede modificar via "
            "este script."
        )
    return key


def get_param(client: OdooClient, key: str) -> str | None:
    rec = client.call(
        "ir.config_parameter",
        "search_read",
        [[("key", "=", key)]],
        {"fields": ["key", "value"], "limit": 1},
    )
    return rec[0]["value"] if rec else None


def set_param(client: OdooClient, key: str, value: str) -> tuple[int, str]:
    existing = client.call(
        "ir.config_parameter",
        "search",
        [[("key", "=", key)]],
        {"limit": 1},
    )
    if existing:
        client.call(
            "ir.config_parameter", "write", [[existing[0]], {"value": value}]
        )
        return existing[0], "updated"
    rec_id = client.call(
        "ir.config_parameter", "create", [{"key": key, "value": value}]
    )
    return rec_id, "created"


def delete_param(client: OdooClient, key: str) -> bool:
    existing = client.call(
        "ir.config_parameter",
        "search",
        [[("key", "=", key)]],
        {"limit": 1},
    )
    if not existing:
        return False
    client.call("ir.config_parameter", "unlink", [existing])
    return True


def list_params(client: OdooClient, prefix: str | None) -> list[dict]:
    domain = []
    if prefix:
        domain.append(("key", "=like", f"{prefix}%"))
    return client.call(
        "ir.config_parameter",
        "search_read",
        [domain],
        {"fields": ["id", "key", "value"], "order": "key"},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)

    g = sub.add_parser("get")
    g.add_argument("key")

    s = sub.add_parser("set")
    s.add_argument("key")
    s.add_argument("value")

    d = sub.add_parser("delete")
    d.add_argument("key")
    d.add_argument(
        "--confirm",
        action="store_true",
        help="Confirma la eliminacion (sin esto, dry-run).",
    )

    li = sub.add_parser("list")
    li.add_argument("--prefix", help="Filtra por prefijo (ej. 'mail.').")

    ns = parser.parse_args()
    client = OdooClient()

    if ns.action == "get":
        validate_key(ns.key)
        v = get_param(client, ns.key)
        json.dump({"key": ns.key, "value": v}, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return 0 if v is not None else 4

    if ns.action == "set":
        validate_key(ns.key)
        rec_id, action = set_param(client, ns.key, ns.value)
        json.dump(
            {"id": rec_id, "action": action, "key": ns.key, "value": ns.value},
            sys.stdout,
            indent=2,
            ensure_ascii=False,
        )
        print()
        return 0

    if ns.action == "delete":
        validate_key(ns.key)
        if not ns.confirm:
            existing = get_param(client, ns.key)
            json.dump(
                {
                    "key": ns.key,
                    "current_value": existing,
                    "would_delete": existing is not None,
                    "next_step": "Pasar --confirm para borrar.",
                },
                sys.stdout,
                indent=2,
                ensure_ascii=False,
            )
            print()
            return 0
        ok = delete_param(client, ns.key)
        json.dump(
            {"key": ns.key, "deleted": ok},
            sys.stdout,
            indent=2,
            ensure_ascii=False,
        )
        print()
        return 0 if ok else 4

    # list
    rows = list_params(client, ns.prefix)
    json.dump(rows, sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0 if rows else 4


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
