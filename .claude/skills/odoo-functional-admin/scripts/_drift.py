"""Helpers puros para drift detection (config-as-code).

Compara un YAML deseado contra un snapshot actual y reporta diff.

YAML schema (lo que se compara hoy):

    companies:
      - vat: ESB99999999        # clave natural
        name: "Acme Holdings S.L."
        currency: EUR
        country: ES
        parent_vat: null
      - vat: ESB88888888
        name: "Acme Iberia S.L."
        parent_vat: ESB99999999

    users:
      - login: bot.contable@...
        name: "Bot Contable"
        lang: es_ES
        active: true
        groups:                 # XML-IDs (orden no importa)
          - base.group_user
          - account.group_account_manager
        company_vats:
          - ESB12345678
          - ESB22222222

    journals:
      - company_vat: ESB22222222
        code: VENT              # clave natural per company
        type: sale
        name: "Customer Invoices"

Cada seccion es opcional; lo que no aparezca no se compara.
"""
from __future__ import annotations

from typing import Any


def normalize_companies(rows: list[dict]) -> dict[str, dict]:
    """Snapshot de res.company -> dict por VAT (clave natural)."""
    out: dict[str, dict] = {}
    parent_vat_by_id: dict[int, str | None] = {}
    # Pre-pasada para resolver parent_id -> parent_vat
    by_id = {r["id"]: r for r in rows if r.get("vat")}
    for rid, r in by_id.items():
        parent_vat_by_id[rid] = None
        if r.get("parent_id"):
            pid = r["parent_id"][0] if isinstance(r["parent_id"], list) else r["parent_id"]
            parent = by_id.get(pid)
            parent_vat_by_id[rid] = parent.get("vat") if parent else None
    for r in rows:
        vat = (r.get("vat") or "").strip().upper()
        if not vat:
            continue
        out[vat] = {
            "vat": vat,
            "name": r.get("name"),
            "currency": (r.get("currency_id") or [None, None])[1],
            "country": (r.get("country_id") or [None, None])[1],
            "parent_vat": parent_vat_by_id.get(r["id"]),
        }
    return out


def normalize_companies_yaml(items: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for it in items or []:
        vat = (it.get("vat") or "").strip().upper()
        if not vat:
            continue
        out[vat] = {
            "vat": vat,
            "name": it.get("name"),
            "currency": (it.get("currency") or "").upper() or None,
            "country": (it.get("country") or "").upper() or None,
            "parent_vat": (it.get("parent_vat") or "").upper() or None,
        }
    return out


def normalize_users(rows: list[dict], group_id_to_xmlid: dict[int, str],
                    company_id_to_vat: dict[int, str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in rows:
        login = (r.get("login") or "").strip().lower()
        if not login or login in ("admin", "__system__"):
            continue
        groups = sorted(
            group_id_to_xmlid[g] for g in (r.get("group_ids") or [])
            if g in group_id_to_xmlid
        )
        company_vats = sorted(
            company_id_to_vat[c] for c in (r.get("company_ids") or [])
            if c in company_id_to_vat
        )
        out[login] = {
            "login": login,
            "name": r.get("name"),
            "lang": r.get("lang"),
            "active": bool(r.get("active", True)),
            "groups": groups,
            "company_vats": company_vats,
        }
    return out


def normalize_users_yaml(items: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for it in items or []:
        login = (it.get("login") or "").strip().lower()
        if not login:
            continue
        out[login] = {
            "login": login,
            "name": it.get("name"),
            "lang": it.get("lang") or "es_ES",
            "active": bool(it.get("active", True)),
            "groups": sorted(it.get("groups") or []),
            "company_vats": sorted(
                (v or "").upper() for v in (it.get("company_vats") or [])
            ),
        }
    return out


def normalize_journals(rows: list[dict],
                       company_id_to_vat: dict[int, str]) -> dict[tuple[str, str], dict]:
    """Clave: (company_vat, code) — es la unica natural."""
    out: dict[tuple[str, str], dict] = {}
    for r in rows:
        company = r.get("company_id")
        cid = company[0] if isinstance(company, list) else company
        vat = company_id_to_vat.get(cid)
        code = (r.get("code") or "").strip().upper()
        if not vat or not code:
            continue
        out[(vat, code)] = {
            "company_vat": vat,
            "code": code,
            "type": r.get("type"),
            "name": r.get("name"),
        }
    return out


def normalize_journals_yaml(items: list[dict]) -> dict[tuple[str, str], dict]:
    out: dict[tuple[str, str], dict] = {}
    for it in items or []:
        vat = (it.get("company_vat") or "").strip().upper()
        code = (it.get("code") or "").strip().upper()
        if not vat or not code:
            continue
        out[(vat, code)] = {
            "company_vat": vat,
            "code": code,
            "type": it.get("type"),
            "name": it.get("name"),
        }
    return out


def diff_section(desired: dict, actual: dict, fields: list[str]) -> dict[str, Any]:
    """Compara dos dicts {key: record} y devuelve missing/extra/changed."""
    missing = []   # esta en desired pero no en actual
    extra = []     # esta en actual pero no en desired
    changed: list[dict] = []

    for k, want in desired.items():
        if k not in actual:
            missing.append(want)
            continue
        have = actual[k]
        diffs = {}
        for f in fields:
            w, h = want.get(f), have.get(f)
            # Comparacion sensible: listas como sets
            if isinstance(w, list) and isinstance(h, list):
                if sorted(w) != sorted(h):
                    diffs[f] = {"want": w, "have": h}
            elif w is not None and w != h:
                diffs[f] = {"want": w, "have": h}
        if diffs:
            changed.append({"key": k, "fields": diffs})

    for k, have in actual.items():
        if k not in desired:
            extra.append(have)

    return {
        "missing": missing,
        "extra": extra,
        "changed": changed,
        "ok": not missing and not changed,
    }
