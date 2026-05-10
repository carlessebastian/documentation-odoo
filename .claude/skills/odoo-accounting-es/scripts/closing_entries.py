#!/usr/bin/env python3
"""Genera el asiento de cierre (cuentas 6xx y 7xx -> 129) para fin de ejercicio.

NO genera el asiento de apertura del ejercicio siguiente (en Odoo no es
necesario para el motor de reportes). Permite --dry-run para revisar
saldos antes de crear.

Importante: este asiento es opcional en Odoo (el motor account.report
calcula PyG automaticamente), pero algunos auditores lo exigen para
cumplir con el PGCE espanol formal.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from _common import OdooError
from odoo_client import OdooClient


def _account_balance(
    client: OdooClient, account_id: int, *, date_to: str, company_id: int
) -> float:
    rg = client.call(
        "account.move.line", "read_group",
        [[("account_id", "=", account_id),
          ("parent_state", "=", "posted"),
          ("date", "<=", date_to),
          ("company_id", "=", company_id)],
         ["balance:sum"], []],
    )
    return rg[0]["balance"] if rg else 0.0


def build_closing_entry(
    client: OdooClient,
    *,
    year: int,
    company_id: int = 1,
    target_account_code: str = "129",
    journal_code: str = "MISC",
) -> dict[str, Any]:
    date_to = f"{year}-12-31"

    journals = client.search_read(
        "account.journal",
        [("type", "=", "general"), ("code", "=", journal_code),
         ("company_id", "=", company_id)],
        ["id"], limit=1,
    )
    if not journals:
        journals = client.search_read(
            "account.journal",
            [("type", "=", "general"), ("company_id", "=", company_id)],
            ["id"], limit=1,
        )
    if not journals:
        raise OdooError("Diario miscelaneo no encontrado")
    journal_id = journals[0]["id"]

    target_acc = client.search_read(
        "account.account",
        [("code", "=like", f"{target_account_code}%"),
         ("company_id", "=", company_id)],
        ["id", "code", "name"], limit=1,
    )
    if not target_acc:
        raise OdooError(
            f"Cuenta destino {target_account_code} no encontrada"
        )
    target_acc_id = target_acc[0]["id"]

    # Cuentas 6xx y 7xx con saldo
    accs = client.search_read(
        "account.account",
        [("code", "=like", "6%"), ("company_id", "=", company_id)],
        ["id", "code", "name"], limit=10000,
    )
    accs += client.search_read(
        "account.account",
        [("code", "=like", "7%"), ("company_id", "=", company_id)],
        ["id", "code", "name"], limit=10000,
    )

    lines: list[dict] = []
    total_debit = 0.0
    total_credit = 0.0
    for a in accs:
        bal = _account_balance(client, a["id"],
                               date_to=date_to, company_id=company_id)
        if abs(bal) < 0.005:
            continue
        if bal > 0:
            lines.append({
                "account_id": a["id"],
                "account_code": a["code"],
                "name": f"Cierre {a['code']} {a['name']}",
                "credit": bal,
                "debit": 0,
            })
            total_credit += bal
        else:
            lines.append({
                "account_id": a["id"],
                "account_code": a["code"],
                "name": f"Cierre {a['code']} {a['name']}",
                "debit": -bal,
                "credit": 0,
            })
            total_debit += -bal

    diff = total_credit - total_debit  # positive = ingresos > gastos = beneficio
    if abs(diff) > 0.005:
        if diff > 0:
            lines.append({
                "account_id": target_acc_id,
                "account_code": target_acc[0]["code"],
                "name": f"Resultado del ejercicio {year}",
                "debit": diff,
                "credit": 0,
            })
            total_debit += diff
        else:
            lines.append({
                "account_id": target_acc_id,
                "account_code": target_acc[0]["code"],
                "name": f"Resultado del ejercicio {year}",
                "credit": -diff,
                "debit": 0,
            })
            total_credit += -diff

    return {
        "year": year,
        "company_id": company_id,
        "journal_id": journal_id,
        "target_account": target_acc[0],
        "lines_count": len(lines),
        "total_debit": round(total_debit, 2),
        "total_credit": round(total_credit, 2),
        "result": round(diff, 2),
        "result_sign": "beneficio" if diff > 0 else "perdida",
        "lines": lines,
    }


def post_closing_entry(
    client: OdooClient, payload: dict, *, post: bool = False
) -> dict[str, Any]:
    move_lines = []
    for ln in payload["lines"]:
        move_lines.append((0, 0, {
            "account_id": ln["account_id"],
            "name": ln["name"],
            "debit": ln.get("debit", 0),
            "credit": ln.get("credit", 0),
        }))
    move_id = client.create("account.move", {
        "move_type": "entry",
        "journal_id": payload["journal_id"],
        "date": f"{payload['year']}-12-31",
        "ref": f"Asiento de cierre {payload['year']}",
        "line_ids": move_lines,
    })
    if post:
        client.action("account.move", [move_id], "action_post")
    return {"move_id": move_id, "posted": post}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--company-id", type=int, default=1)
    parser.add_argument("--target-account", default="129",
                        help="Codigo cuenta destino (default 129)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--post", action="store_true",
                        help="Postea automaticamente tras crear")
    ns = parser.parse_args()

    client = OdooClient()
    payload = build_closing_entry(
        client,
        year=ns.year,
        company_id=ns.company_id,
        target_account_code=ns.target_account,
    )

    if ns.dry_run:
        json.dump(payload, sys.stdout, indent=2, ensure_ascii=False, default=str)
        print()
        return 0

    created = post_closing_entry(client, payload, post=ns.post)
    json.dump(
        {"summary": {k: payload[k] for k in
                     ["year", "lines_count", "total_debit", "total_credit",
                      "result", "result_sign"]},
         **created},
        sys.stdout, indent=2, ensure_ascii=False, default=str,
    )
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
