#!/usr/bin/env python3
"""Crea o actualiza un `res.users`. Idempotente sobre `login`.

Uso:
    python3 user_provision.py --login [email protected] \\
        --name "Maria Pons" \\
        --groups base.group_user,account.group_account_invoice \\
        --company-vats ESB12345678,ESB99999999 \\
        --lang ca_ES --tz Europe/Madrid
"""
from __future__ import annotations

import argparse
import json
import re
import sys

from _common import OdooError
from odoo_client import OdooClient


LOGIN_RE = re.compile(r"^[A-Za-z0-9._+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
XMLID_RE = re.compile(r"^[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*$", re.IGNORECASE)


def normalize_login(login: str) -> str:
    cleaned = login.strip().lower()
    if not LOGIN_RE.match(cleaned):
        raise OdooError(
            f"Login {login!r} no parece un email valido. Usa formato "
            "user@dominio.tld."
        )
    return cleaned


def validate_group_xmlid(xmlid: str) -> str:
    if not XMLID_RE.match(xmlid):
        raise OdooError(
            f"XML-ID de grupo invalido: {xmlid!r}. Formato esperado "
            "'modulo.grupo' (p.ej. base.group_user)."
        )
    return xmlid


def resolve_group_xmlids(client: OdooClient, xmlids: list[str]) -> list[int]:
    ids: list[int] = []
    for xmlid in xmlids:
        validate_group_xmlid(xmlid)
        module, name = xmlid.split(".", 1)
        rec = client.call(
            "ir.model.data",
            "search_read",
            [
                [
                    ("module", "=", module),
                    ("name", "=", name),
                    ("model", "=", "res.groups"),
                ]
            ],
            {"fields": ["res_id"], "limit": 1},
        )
        if not rec:
            raise OdooError(f"Grupo {xmlid!r} no encontrado en ir.model.data.")
        ids.append(rec[0]["res_id"])
    return ids


def resolve_company_vats(client: OdooClient, vats: list[str]) -> list[int]:
    ids: list[int] = []
    for vat in vats:
        v = vat.strip().upper().replace(" ", "")
        rec = client.call(
            "res.company",
            "search",
            [[("vat", "=", v)]],
            {"limit": 1},
        )
        if not rec:
            raise OdooError(f"No existe res.company con VAT {v!r}.")
        ids.append(rec[0])
    return ids


def upsert_user(
    client: OdooClient,
    *,
    login: str,
    name: str,
    group_ids: list[int],
    company_ids: list[int],
    lang: str,
    tz: str,
    dry_run: bool = False,
) -> tuple[int | None, str]:
    login = normalize_login(login)
    existing = client.call(
        "res.users",
        "search",
        [[("login", "=", login)]],
        {"limit": 1},
    )
    default_company = company_ids[0] if company_ids else None
    vals = {
        "name": name,
        "lang": lang,
        "tz": tz,
        "group_ids": [(6, 0, group_ids)] if group_ids else False,
    }
    if default_company:
        vals["company_id"] = default_company
        vals["company_ids"] = [(6, 0, company_ids)]

    if existing:
        if dry_run:
            return existing[0], "would_update"
        client.call("res.users", "write", [[existing[0]], vals])
        return existing[0], "updated"
    if dry_run:
        return None, "would_create"
    create_vals = {**vals, "login": login}
    rec_id = client.call("res.users", "create", [create_vals])
    return rec_id, "created"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--login", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument(
        "--groups",
        default="base.group_user",
        help="Lista CSV de XML-IDs de grupo. Default: base.group_user.",
    )
    parser.add_argument(
        "--company-vats",
        default="",
        help="Lista CSV de VATs de companias permitidas.",
    )
    parser.add_argument("--lang", default="es_ES")
    parser.add_argument("--tz", default="Europe/Madrid")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Indica que haria sin tocar la base.",
    )
    ns = parser.parse_args()

    client = OdooClient()
    group_xmlids = [g.strip() for g in ns.groups.split(",") if g.strip()]
    company_vats = [v.strip() for v in ns.company_vats.split(",") if v.strip()]
    group_ids = resolve_group_xmlids(client, group_xmlids)
    company_ids = (
        resolve_company_vats(client, company_vats) if company_vats else []
    )

    rec_id, action = upsert_user(
        client,
        login=ns.login,
        name=ns.name,
        group_ids=group_ids,
        company_ids=company_ids,
        lang=ns.lang,
        tz=ns.tz,
        dry_run=ns.dry_run,
    )
    json.dump(
        {
            "id": rec_id,
            "action": action,
            "login": ns.login,
            "groups_resolved": list(zip(group_xmlids, group_ids)),
            "company_ids": company_ids,
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
