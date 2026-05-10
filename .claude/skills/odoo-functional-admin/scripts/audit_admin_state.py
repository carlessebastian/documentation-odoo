#!/usr/bin/env python3
"""Snapshot read-only del estado administrativo de Odoo.

Imprime JSON a stdout con companies, users, groups, journals, crons.
No modifica nada. Util para diff/backup antes de cambios sensibles.

Uso:
    python3 audit_admin_state.py
    python3 audit_admin_state.py --section companies
    python3 audit_admin_state.py --section users --company 2
    python3 audit_admin_state.py --diff desired_state.yaml
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import _drift
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


def _resolve_group_xmlid_map(client: OdooClient, group_ids: list[int]) -> dict[int, str]:
    """Resuelve {group_id: 'module.name'} via ir.model.data (mejor esfuerzo)."""
    if not group_ids:
        return {}
    rows = client.call(
        "ir.model.data",
        "search_read",
        [
            [
                ("model", "=", "res.groups"),
                ("res_id", "in", group_ids),
            ]
        ],
        {"fields": ["module", "name", "res_id"]},
    )
    return {r["res_id"]: f"{r['module']}.{r['name']}" for r in rows}


def _company_id_to_vat(company_rows: list[dict]) -> dict[int, str]:
    return {
        r["id"]: (r.get("vat") or "").strip().upper()
        for r in company_rows
        if r.get("vat")
    }


def diff_against_yaml(client: OdooClient, yaml_path: Path) -> dict:
    """Compara YAML deseado vs estado actual. Devuelve diff por seccion."""
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError as exc:
        raise OdooError(
            "PyYAML no esta instalado. `pip install pyyaml` o "
            "`uv tool install pyyaml`."
        ) from exc

    if not yaml_path.exists():
        raise OdooError(f"YAML no existe: {yaml_path}")
    desired = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    if not isinstance(desired, dict):
        raise OdooError("El YAML debe tener un mapping en el top level.")

    # Snapshot actual
    company_rows = companies(client)
    user_rows = users(client, None)
    journal_rows = journals(client, None)

    # Mappings auxiliares para normalizar
    cid_to_vat = _company_id_to_vat(company_rows)
    all_group_ids = sorted({g for u in user_rows for g in (u.get("groups_id") or [])})
    gid_to_xmlid = _resolve_group_xmlid_map(client, all_group_ids)

    out: dict = {"sections": {}, "yaml_path": str(yaml_path)}

    if "companies" in desired:
        actual = _drift.normalize_companies(company_rows)
        want = _drift.normalize_companies_yaml(desired["companies"])
        out["sections"]["companies"] = _drift.diff_section(
            want, actual, fields=["name", "currency", "country", "parent_vat"]
        )

    if "users" in desired:
        actual = _drift.normalize_users(user_rows, gid_to_xmlid, cid_to_vat)
        want = _drift.normalize_users_yaml(desired["users"])
        out["sections"]["users"] = _drift.diff_section(
            want, actual,
            fields=["name", "lang", "active", "groups", "company_vats"],
        )

    if "journals" in desired:
        actual = _drift.normalize_journals(journal_rows, cid_to_vat)
        want = _drift.normalize_journals_yaml(desired["journals"])
        out["sections"]["journals"] = _drift.diff_section(
            want, actual, fields=["type", "name"]
        )

    out["ok"] = all(s["ok"] for s in out["sections"].values())
    return out


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
    parser.add_argument(
        "--diff",
        type=Path,
        metavar="YAML",
        help=(
            "Compara el estado actual contra el YAML deseado y devuelve "
            "missing/extra/changed por seccion. Solo lectura; nunca aplica."
        ),
    )
    ns = parser.parse_args()

    client = OdooClient()

    if ns.diff:
        result = diff_against_yaml(client, ns.diff)
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False, default=str)
        print()
        return 0 if result["ok"] else 6

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
