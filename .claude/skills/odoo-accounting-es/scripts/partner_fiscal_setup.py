#!/usr/bin/env python3
"""Asigna posicion fiscal y termino de pago a partners por criterio.

Uso:
    # Todos los clientes EU (excluyendo ES) con VAT -> FP intra-UE
    python3 partner_fiscal_setup.py \\
        --criteria eu_with_vat \\
        --fiscal-position "Regimen intracomunitario" \\
        --company 2 --confirm

    # Clientes minoristas espanoles -> RecEq (manual marcado de partners)
    python3 partner_fiscal_setup.py \\
        --criteria match_partner_ids \\
        --partner-ids 234,567,891 \\
        --fiscal-position "Recargo de Equivalencia" \\
        --payment-term "30 Days" \\
        --company 2 --confirm

    # Clientes fuera de UE con VAT -> FP exportacion
    python3 partner_fiscal_setup.py \\
        --criteria non_eu_with_vat \\
        --fiscal-position "Exportacion fuera UE" \\
        --company 2 --confirm

Sin --confirm, dry-run (lista los partners afectados sin escribir).
"""
from __future__ import annotations

import argparse
import json
import sys

from _common import OdooError
from odoo_client import OdooClient


VALID_CRITERIA = ("eu_with_vat", "non_eu_with_vat", "spain_only",
                  "match_partner_ids")


def build_domain(
    client: OdooClient,
    criteria: str,
    company_id: int,
    partner_ids: list[int] | None,
) -> list:
    """Construye el dominio para search() segun el criterio elegido."""
    base: list = [
        ("is_company", "=", True),
        ("active", "=", True),
        "|", ("customer_rank", ">", 0), ("supplier_rank", ">", 0),
    ]

    if criteria == "match_partner_ids":
        if not partner_ids:
            raise OdooError(
                "criteria=match_partner_ids requiere --partner-ids."
            )
        return [("id", "in", list(partner_ids))]

    es_id = _country_id(client, "ES")

    if criteria == "spain_only":
        return base + [("country_id", "=", es_id)]

    eu_group_id = _country_group_id(client, "base.europe")
    if criteria == "eu_with_vat":
        return base + [
            ("country_id.country_group_ids", "in", [eu_group_id]),
            ("country_id", "!=", es_id),
            ("vat", "!=", False),
            ("vat", "!=", ""),
        ]
    if criteria == "non_eu_with_vat":
        return base + [
            "!", ("country_id.country_group_ids", "in", [eu_group_id]),
            ("vat", "!=", False),
            ("vat", "!=", ""),
        ]
    raise OdooError(f"Criterio desconocido: {criteria!r}.")


def _country_id(client: OdooClient, code: str) -> int:
    rec = client.call(
        "res.country", "search",
        [[("code", "=", code.upper())]],
        {"limit": 1},
    )
    if not rec:
        raise OdooError(f"Pais {code!r} no encontrado.")
    return rec[0]


def _country_group_id(client: OdooClient, xmlid: str) -> int:
    module, name = xmlid.split(".", 1)
    rec = client.call(
        "ir.model.data", "search_read",
        [
            [
                ("module", "=", module),
                ("name", "=", name),
                ("model", "=", "res.country.group"),
            ]
        ],
        {"fields": ["res_id"], "limit": 1},
    )
    if not rec:
        raise OdooError(f"res.country.group {xmlid!r} no encontrado.")
    return rec[0]["res_id"]


def resolve_fp(client: OdooClient, name: str, company_id: int) -> int:
    rec = client.call(
        "account.fiscal.position", "search",
        [[("name", "=", name), ("company_id", "=", company_id)]],
        {"limit": 1},
    )
    if not rec:
        raise OdooError(
            f"Posicion fiscal {name!r} no existe en company {company_id}. "
            "Crea la primero con `odoo-functional-admin` "
            "(`fiscal_position_setup.py`)."
        )
    return rec[0]


def resolve_payment_term(client: OdooClient, name: str) -> int:
    rec = client.call(
        "account.payment.term", "search",
        [[("name", "=", name)]],
        {"limit": 1},
    )
    if not rec:
        raise OdooError(
            f"Termino de pago {name!r} no encontrado. Crealo en "
            "Accounting > Configuration > Payment Terms o via "
            "`odoo-functional-admin`."
        )
    return rec[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--criteria",
        required=True,
        choices=VALID_CRITERIA,
        help="Criterio de seleccion de partners.",
    )
    parser.add_argument(
        "--partner-ids",
        default="",
        help="CSV de IDs (solo con --criteria match_partner_ids).",
    )
    parser.add_argument(
        "--fiscal-position",
        help="Nombre exacto de la account.fiscal.position a asignar.",
    )
    parser.add_argument(
        "--clear-fiscal-position",
        action="store_true",
        help="Vacia la posicion fiscal (la elimina del partner).",
    )
    parser.add_argument(
        "--payment-term",
        help="Nombre exacto del account.payment.term a asignar (opcional).",
    )
    parser.add_argument(
        "--company", type=int, required=True,
        help="company_id en cuyo contexto se aplica el cambio.",
    )
    parser.add_argument(
        "--limit", type=int, default=500,
        help="Limite de partners a procesar (proteccion). Default 500.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Sin esto, dry-run (solo lista partners afectados).",
    )
    ns = parser.parse_args()

    if not ns.fiscal_position and not ns.clear_fiscal_position and not ns.payment_term:
        raise OdooError(
            "Indica al menos --fiscal-position, --clear-fiscal-position o "
            "--payment-term."
        )
    if ns.fiscal_position and ns.clear_fiscal_position:
        raise OdooError(
            "--fiscal-position y --clear-fiscal-position son mutuamente "
            "exclusivos."
        )

    client = OdooClient()

    partner_ids = [
        int(p.strip()) for p in ns.partner_ids.split(",") if p.strip()
    ] or None
    domain = build_domain(client, ns.criteria, ns.company, partner_ids)

    matched = client.call(
        "res.partner",
        "search_read",
        [domain],
        {
            "fields": ["id", "name", "vat", "country_id",
                       "property_account_position_id",
                       "property_payment_term_id"],
            "limit": ns.limit,
            "order": "name",
        },
    )

    vals: dict = {}
    if ns.fiscal_position:
        vals["property_account_position_id"] = resolve_fp(
            client, ns.fiscal_position, ns.company
        )
    elif ns.clear_fiscal_position:
        vals["property_account_position_id"] = False
    if ns.payment_term:
        vals["property_payment_term_id"] = resolve_payment_term(
            client, ns.payment_term
        )

    if not matched:
        json.dump(
            {"action": "noop", "reason": "no partners matched", "domain": domain},
            sys.stdout, indent=2, ensure_ascii=False, default=str,
        )
        print()
        return 0

    if not ns.confirm:
        json.dump(
            {
                "action": "dry_run",
                "criteria": ns.criteria,
                "company_id": ns.company,
                "matched_count": len(matched),
                "matched_sample": matched[:20],
                "would_apply": vals,
                "next_step": "Re-ejecutar con --confirm para aplicar.",
            },
            sys.stdout, indent=2, ensure_ascii=False, default=str,
        )
        print()
        return 0

    ids = [r["id"] for r in matched]
    # Aplicar en el contexto de la company para que las property_*_id
    # se escriban correctamente como overrides per-company.
    client.call(
        "res.partner", "with_context",
        [ids],
        {"context": {"force_company": ns.company,
                     "allowed_company_ids": [ns.company]}},
    ) if False else None  # noqa: B018 - documenta el patron, pero write soporta context
    client.call(
        "res.partner",
        "write",
        [ids, vals],
        {"context": {"allowed_company_ids": [ns.company]}},
    )

    json.dump(
        {
            "action": "applied",
            "criteria": ns.criteria,
            "company_id": ns.company,
            "applied_to_count": len(ids),
            "applied_vals": vals,
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
