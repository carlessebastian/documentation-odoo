#!/usr/bin/env python3
"""Snapshot read-only del estado administrativo de Odoo.

Imprime JSON a stdout con companies, users, groups, journals, crons.
No modifica nada. Util para diff/backup antes de cambios sensibles.

Uso:
    python3 audit_admin_state.py
    python3 audit_admin_state.py --section companies
    python3 audit_admin_state.py --section users --company 2
"""
from __future__ import annotations

import argparse
import json
import sys

from _common import OdooError
from odoo_client import OdooClient


SECTIONS = ("companies", "users", "groups", "journals", "crons", "rules")


def companies(client: OdooClient) -> list[dict]:
    return client.call(
        "res.company",
        "search_read",
        [[]],
        {
            "fields": [
                "id",
                "name",
                "parent_id",
                "child_ids",
                "vat",
                "country_id",
                "currency_id",
                "fiscalyear_lock_date",
                "tax_lock_date",
            ],
            "order": "parent_id, id",
        },
    )


def users(client: OdooClient, company_id: int | None) -> list[dict]:
    domain: list = [("share", "=", False)]
    if company_id:
        domain.append(("company_ids", "in", [company_id]))
    return client.call(
        "res.users",
        "search_read",
        [domain],
        {
            "fields": [
                "id",
                "name",
                "login",
                "active",
                "lang",
                "tz",
                "company_id",
                "company_ids",
                "groups_id",
            ],
            "order": "login",
        },
    )


def groups(client: OdooClient) -> list[dict]:
    return client.call(
        "res.groups",
        "search_read",
        [[]],
        {
            "fields": ["id", "name", "category_id", "implied_ids"],
            "order": "category_id, name",
        },
    )


def journals(client: OdooClient, company_id: int | None) -> list[dict]:
    domain: list = []
    if company_id:
        domain.append(("company_id", "=", company_id))
    return client.call(
        "account.journal",
        "search_read",
        [domain],
        {
            "fields": [
                "id",
                "name",
                "code",
                "type",
                "company_id",
                "sequence_id",
                "default_account_id",
                "currency_id",
                "active",
            ],
            "order": "company_id, type, code",
        },
    )


def crons(client: OdooClient) -> list[dict]:
    return client.call(
        "ir.cron",
        "search_read",
        [[]],
        {
            "fields": [
                "id",
                "cron_name",
                "model_id",
                "interval_number",
                "interval_type",
                "nextcall",
                "lastcall",
                "active",
                "numbercall",
                "user_id",
            ],
            "order": "active desc, cron_name",
        },
    )


def rules(client: OdooClient, model: str | None) -> list[dict]:
    domain: list = [("active", "=", True)]
    if model:
        domain.append(("model_id.model", "=", model))
    return client.call(
        "ir.rule",
        "search_read",
        [domain],
        {
            "fields": [
                "id",
                "name",
                "model_id",
                "groups",
                "domain_force",
                "perm_read",
                "perm_write",
                "perm_create",
                "perm_unlink",
            ],
            "order": "model_id, id",
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--section",
        choices=SECTIONS,
        help="Si se omite, devuelve todas las secciones en un solo JSON.",
    )
    parser.add_argument(
        "--company",
        type=int,
        help="Filtra users/journals por company_id.",
    )
    parser.add_argument(
        "--model",
        help="Filtra rules por modelo (p.ej. res.partner). Solo --section rules.",
    )
    ns = parser.parse_args()

    client = OdooClient()
    out: dict = {}
    targets = (ns.section,) if ns.section else SECTIONS
    for s in targets:
        if s == "companies":
            out[s] = companies(client)
        elif s == "users":
            out[s] = users(client, ns.company)
        elif s == "groups":
            out[s] = groups(client)
        elif s == "journals":
            out[s] = journals(client, ns.company)
        elif s == "crons":
            out[s] = crons(client)
        elif s == "rules":
            out[s] = rules(client, ns.model)

    json.dump(out, sys.stdout, indent=2, ensure_ascii=False, default=str)
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
