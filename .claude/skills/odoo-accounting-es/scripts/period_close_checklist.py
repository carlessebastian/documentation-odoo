#!/usr/bin/env python3
"""Checklist pre-cierre periodico: valida que todo este listo para cerrar.

Comprueba: facturas en draft, asientos sin postear, conciliacion bancaria
incompleta, errores SII/Verifactu pendientes, lock dates configurados.

Devuelve JSON con `ready` (bool) + lista detallada de bloqueos.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from typing import Any

from _common import OdooError
from odoo_client import OdooClient


def _module_installed(client: OdooClient, name: str) -> bool:
    rows = client.search_read(
        "ir.module.module",
        [("name", "=", name), ("state", "=", "installed")],
        ["id"], limit=1,
    )
    return bool(rows)


def check_drafts(client: OdooClient, *, date_to: str,
                 company_id: int) -> dict[str, Any]:
    domain = [
        ("state", "=", "draft"),
        ("date", "<=", date_to),
        ("company_id", "=", company_id),
    ]
    rg = client.call(
        "account.move", "read_group",
        [domain, ["id:count"], ["move_type"]],
    )
    by_type = {r["move_type"]: r["move_type_count"] for r in rg}
    return {
        "name": "Borradores pendientes",
        "ok": sum(by_type.values()) == 0,
        "by_move_type": by_type,
        "detail": "Postear o cancelar antes del cierre",
    }


def check_unreconciled_bank(client: OdooClient, *, date_to: str,
                            company_id: int) -> dict[str, Any]:
    count = client.search_count(
        "account.bank.statement.line",
        [("date", "<=", date_to),
         ("is_reconciled", "=", False),
         ("company_id", "=", company_id)],
    )
    return {
        "name": "Lineas extracto sin conciliar",
        "ok": count == 0,
        "count": count,
        "detail": "Conciliar via UI o bank_statement_reconcile.py",
    }


def check_sii_errors(client: OdooClient, *, date_from: str,
                     date_to: str, company_id: int) -> dict[str, Any]:
    if not _module_installed(client, "l10n_es_edi_sii") and \
       not _module_installed(client, "l10n_es_aeat_sii_oca"):
        return {"name": "SII", "ok": True, "skipped": "no instalado"}

    field = (
        "l10n_es_edi_sii_state"
        if _module_installed(client, "l10n_es_edi_sii")
        else "sii_state"
    )
    rows = client.search_read(
        "account.move",
        [("move_type", "in", ["out_invoice", "out_refund",
                              "in_invoice", "in_refund"]),
         ("state", "=", "posted"),
         ("date", ">=", date_from),
         ("date", "<=", date_to),
         (field, "in", [False, "rejected", "error", "fail"]),
         ("company_id", "=", company_id)],
        ["id", "name", field], limit=200,
    )
    return {
        "name": "Facturas con error SII",
        "ok": len(rows) == 0,
        "count": len(rows),
        "examples": [{"id": r["id"], "name": r["name"], "state": r.get(field)}
                     for r in rows[:5]],
    }


def check_verifactu_errors(client: OdooClient, *, date_from: str,
                           date_to: str, company_id: int) -> dict[str, Any]:
    if not _module_installed(client, "l10n_es_edi_verifactu") and \
       not _module_installed(client, "l10n_es_verifactu_oca"):
        return {"name": "Verifactu", "ok": True, "skipped": "no instalado"}

    field = (
        "l10n_es_edi_verifactu_state"
        if _module_installed(client, "l10n_es_edi_verifactu")
        else "verifactu_state"
    )
    rows = client.search_read(
        "account.move",
        [("move_type", "in", ["out_invoice", "out_refund"]),
         ("state", "=", "posted"),
         ("date", ">=", date_from),
         ("date", "<=", date_to),
         (field, "in", [False, "rejected", "error"]),
         ("company_id", "=", company_id)],
        ["id", "name", field], limit=200,
    )
    return {
        "name": "Facturas con error Verifactu",
        "ok": len(rows) == 0,
        "count": len(rows),
        "examples": [{"id": r["id"], "name": r["name"], "state": r.get(field)}
                     for r in rows[:5]],
    }


def check_lock_dates(client: OdooClient, *, date_to: str,
                     company_id: int, expected_locked: bool) -> dict[str, Any]:
    company = client.search_read(
        "res.company", [("id", "=", company_id)],
        ["fiscalyear_lock_date", "tax_lock_date",
         "sale_lock_date", "purchase_lock_date"],
        limit=1,
    )[0]
    locks = {k: company.get(k) for k in
             ("fiscalyear_lock_date", "tax_lock_date",
              "sale_lock_date", "purchase_lock_date")}
    if not expected_locked:
        return {
            "name": "Lock dates",
            "ok": True,
            "current": locks,
            "detail": "Pre-cierre: sin requisito",
        }
    locked_at_least = any(
        locks.get(k) and locks[k] >= date_to
        for k in ("tax_lock_date", "fiscalyear_lock_date")
    )
    return {
        "name": "Lock dates",
        "ok": locked_at_least,
        "current": locks,
        "detail": "Configurar al menos tax_lock_date >= fin de periodo",
    }


def check_unbalanced_partners(client: OdooClient, *, threshold: float,
                              company_id: int) -> dict[str, Any]:
    domain = [
        ("account_id.account_type", "in",
         ["asset_receivable", "liability_payable"]),
        ("parent_state", "=", "posted"),
        ("reconciled", "=", False),
        ("company_id", "=", company_id),
    ]
    rg = client.call(
        "account.move.line", "read_group",
        [domain, ["amount_residual:sum"], ["partner_id"]],
        {"orderby": "amount_residual desc", "limit": 50},
    )
    suspicious = [
        r for r in rg
        if abs(r.get("amount_residual") or 0) > threshold
    ]
    return {
        "name": "Partners con saldo > umbral",
        "ok": True,
        "count": len(suspicious),
        "threshold": threshold,
        "preview": [
            {"partner": r["partner_id"], "balance": r["amount_residual"]}
            for r in suspicious[:10]
        ],
        "detail": "Revisar manualmente; saldos altos pueden indicar conciliacion pendiente",
    }


def run_checklist(
    client: OdooClient,
    *,
    date_from: str,
    date_to: str,
    company_id: int = 1,
    annual: bool = False,
) -> dict[str, Any]:
    checks: list[dict] = [
        check_drafts(client, date_to=date_to, company_id=company_id),
        check_unreconciled_bank(client, date_to=date_to, company_id=company_id),
        check_sii_errors(client, date_from=date_from, date_to=date_to,
                         company_id=company_id),
        check_verifactu_errors(client, date_from=date_from, date_to=date_to,
                               company_id=company_id),
        check_unbalanced_partners(client, threshold=10000.0,
                                  company_id=company_id),
        check_lock_dates(client, date_to=date_to, company_id=company_id,
                         expected_locked=False),
    ]

    blocking = [c for c in checks if not c.get("ok")]
    return {
        "period": {"from": date_from, "to": date_to, "annual": annual},
        "ready": len(blocking) == 0,
        "blocking_count": len(blocking),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="date_from", required=True,
                        help="YYYY-MM-DD inicio del periodo")
    parser.add_argument("--to", dest="date_to", required=True,
                        help="YYYY-MM-DD fin del periodo")
    parser.add_argument("--company-id", type=int, default=1)
    parser.add_argument("--annual", action="store_true",
                        help="Cierre anual (validaciones adicionales)")
    ns = parser.parse_args()

    client = OdooClient()
    result = run_checklist(
        client,
        date_from=ns.date_from,
        date_to=ns.date_to,
        company_id=ns.company_id,
        annual=ns.annual,
    )
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False, default=str)
    print()
    return 0 if result["ready"] else 7


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
