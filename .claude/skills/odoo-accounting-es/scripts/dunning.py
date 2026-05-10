#!/usr/bin/env python3
"""Envia recordatorios de cobro a clientes con facturas vencidas.

Niveles configurables (1=amistoso, 2=insistente, 3=formal). Usa
mail.template para el cuerpo. Evita reenviar el mismo nivel en menos de
`--cooldown` dias.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from typing import Any

from _common import OdooError
from odoo_client import OdooClient


LEVEL_DAYS = {1: 7, 2: 30, 3: 60}


def _last_followup_date(client: OdooClient, partner_id: int, level: int) -> str | None:
    msgs = client.search_read(
        "mail.message",
        [("model", "=", "res.partner"),
         ("res_id", "=", partner_id),
         ("subject", "ilike", f"Recordatorio cobro nivel {level}")],
        ["date"], order="date desc", limit=1,
    )
    return msgs[0]["date"][:10] if msgs else None


def candidates(
    client: OdooClient,
    *,
    level: int,
    today: date | None = None,
    company_id: int = 1,
    cooldown_days: int = 7,
) -> list[dict]:
    if level not in LEVEL_DAYS:
        raise OdooError(f"Nivel invalido: {level}")
    today = today or date.today()
    threshold = (today - timedelta(days=LEVEL_DAYS[level])).isoformat()

    invs = client.search_read(
        "account.move",
        [("move_type", "=", "out_invoice"),
         ("state", "=", "posted"),
         ("payment_state", "in", ["not_paid", "partial"]),
         ("invoice_date_due", "<=", threshold),
         ("company_id", "=", company_id)],
        ["id", "name", "partner_id", "amount_residual", "invoice_date_due"],
        order="invoice_date_due asc", limit=10000,
    )
    by_partner: dict[int, dict] = {}
    for inv in invs:
        if not inv.get("partner_id"):
            continue
        pid = inv["partner_id"][0]
        bp = by_partner.setdefault(pid, {
            "partner_id": pid,
            "partner_name": inv["partner_id"][1],
            "invoices": [],
            "total_due": 0.0,
        })
        bp["invoices"].append({
            "id": inv["id"], "name": inv["name"],
            "due": inv["invoice_date_due"],
            "amount_residual": inv["amount_residual"],
        })
        bp["total_due"] += inv["amount_residual"]

    cooldown_threshold = (today - timedelta(days=cooldown_days)).isoformat()
    filtered: list[dict] = []
    for bp in by_partner.values():
        last = _last_followup_date(client, bp["partner_id"], level)
        if last and last >= cooldown_threshold:
            bp["skipped"] = f"ultimo nivel {level} envio el {last}"
            continue
        filtered.append(bp)
    return filtered


def send(
    client: OdooClient,
    candidates_list: list[dict],
    *,
    template_id: int | None = None,
    level: int = 1,
    dry_run: bool = False,
) -> list[dict]:
    if not template_id:
        # buscar plantilla por nombre
        templates = client.search_read(
            "mail.template",
            [("model", "=", "res.partner"),
             ("name", "ilike", f"Recordatorio cobro nivel {level}")],
            ["id"], limit=1,
        )
        if not templates:
            raise OdooError(
                f"No se encontro mail.template para nivel {level}. "
                "Cree una plantilla 'Recordatorio cobro nivel N' o pase --template-id."
            )
        template_id = templates[0]["id"]

    sent: list[dict] = []
    for c in candidates_list:
        rec = {
            "partner_id": c["partner_id"],
            "partner_name": c["partner_name"],
            "invoice_count": len(c["invoices"]),
            "total_due": c["total_due"],
            "level": level,
        }
        if dry_run:
            rec["status"] = "would_send"
            sent.append(rec)
            continue
        try:
            client.action(
                "res.partner", [c["partner_id"]],
                "message_post_with_template",
                ctx={"template_id": template_id},
            )
            rec["status"] = "sent"
        except OdooError as e:
            rec["status"] = "error"
            rec["error"] = str(e)
        sent.append(rec)
    return sent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", type=int, choices=[1, 2, 3], default=1)
    parser.add_argument("--company-id", type=int, default=1)
    parser.add_argument("--template-id", type=int)
    parser.add_argument("--cooldown", type=int, default=7,
                        help="Dias minimos entre envios del mismo nivel")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0,
                        help="Maximo de partners a procesar (0 = sin limite)")
    ns = parser.parse_args()

    client = OdooClient()
    cands = candidates(
        client,
        level=ns.level,
        company_id=ns.company_id,
        cooldown_days=ns.cooldown,
    )
    skipped = [c for c in cands if "skipped" in c]
    actionable = [c for c in cands if "skipped" not in c]
    if ns.limit > 0:
        actionable = actionable[: ns.limit]

    sent = send(
        client, actionable,
        template_id=ns.template_id,
        level=ns.level,
        dry_run=ns.dry_run,
    )

    json.dump(
        {
            "level": ns.level,
            "candidates": len(cands),
            "actionable": len(actionable),
            "skipped_cooldown": len(skipped),
            "results": sent,
        },
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
