#!/usr/bin/env python3
"""Bootstrap completo de una filial: company + chart_template + diarios + FPs.

Orquesta company_setup + journal_setup + sequence_setup + fiscal_position_setup
para montar una filial nueva en una sola llamada. Idempotente.

Uso:
    python3 subsidiary_bootstrap.py \\
        --name "Kura Terra S.L." \\
        --vat ESB99999999 \\
        --parent-vat ESB12345678 \\
        --chart-template es_pymes
"""
from __future__ import annotations

import argparse
import json
import sys

import company_setup
import journal_setup
import sequence_setup
import fiscal_position_setup
from _common import OdooError
from odoo_client import OdooClient


STANDARD_JOURNALS = [
    # (type, code, name, no_gap)
    ("sale", "VENT", "Customer Invoices", True),
    ("sale", "RECT", "Customer Refunds", True),
    ("purchase", "COMP", "Vendor Bills", False),
    ("purchase", "ABRC", "Vendor Refunds", False),
    ("general", "MISC", "Miscelaneos", False),
]


def install_chart_template(
    client: OdooClient, company_id: int, template_xmlid: str | None
) -> str:
    """Instala el chart_template si la company no lo tiene aun."""
    if not template_xmlid:
        return "skipped"
    company = client.call(
        "res.company",
        "read",
        [[company_id], ["chart_template"]],
    )[0]
    if company.get("chart_template"):
        return "already_installed"
    # Resolver template a su codigo (chart_template es Selection en v19)
    short = template_xmlid.split(".")[-1]
    try:
        client.call(
            "account.chart.template",
            "try_loading",
            [short, {"company": company_id}],
            {},
        )
        return "installed"
    except Exception as exc:
        raise OdooError(
            f"Fallo al instalar chart_template {template_xmlid!r}: {exc}. "
            "Comprueba que `l10n_es` esta instalado (use el skill "
            "odoo-module-admin si no lo esta)."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--vat", required=True)
    parser.add_argument("--country", default="ES")
    parser.add_argument("--currency", default="EUR")
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--parent-id", type=int)
    grp.add_argument("--parent-vat")
    parser.add_argument(
        "--chart-template",
        default="l10n_es.l10n_es_pymes",
        help="Plantilla de plan contable (XML-ID, default es_pymes).",
    )
    parser.add_argument(
        "--skip-fp",
        action="store_true",
        help="Saltar creacion de posiciones fiscales (intra_eu, export, rec_eq).",
    )
    parser.add_argument(
        "--ensure-years",
        default="",
        help="CSV de anyos para crear date_ranges, p.ej. 2026,2027.",
    )
    ns = parser.parse_args()

    client = OdooClient()

    # 1. Crear o actualizar la company
    country_id = company_setup.resolve_country(client, ns.country)
    currency_id = company_setup.resolve_currency(client, ns.currency)
    parent_id = company_setup.resolve_parent(client, ns.parent_id, ns.parent_vat)
    company_id, company_action = company_setup.upsert_company(
        client,
        name=ns.name,
        vat=ns.vat,
        country_id=country_id,
        currency_id=currency_id,
        parent_id=parent_id,
    )

    # 2. Chart template
    chart_action = install_chart_template(client, company_id, ns.chart_template)

    # 3. Diarios estandar + secuencias para sale/purchase
    journals_created = []
    for jtype, jcode, jname, no_gap in STANDARD_JOURNALS:
        seq_id = None
        if jtype in ("sale", "purchase"):
            seq_id = journal_setup.upsert_sequence_for_journal(
                client, jcode, company_id, no_gap
            )
            if ns.ensure_years:
                years = [int(y.strip()) for y in ns.ensure_years.split(",") if y.strip()]
                if years:
                    sequence_setup.ensure_date_ranges(client, seq_id, years)
        rec_id, action = journal_setup.upsert_journal(
            client,
            type_=jtype,
            code=jcode,
            name=jname,
            company_id=company_id,
            sequence_id=seq_id,
            restrict_mode_hash_table=False,
        )
        journals_created.append(
            {"type": jtype, "code": jcode, "id": rec_id,
             "action": action, "sequence_id": seq_id}
        )

    # 4. Posiciones fiscales
    fps_created = []
    if not ns.skip_fp and ns.country.upper() == "ES":
        for preset in ("intra_eu", "export", "rec_eq"):
            try:
                rec_id, action = fiscal_position_setup.upsert_fiscal_position(
                    client, preset=preset, company_id=company_id
                )
                fps_created.append({"preset": preset, "id": rec_id, "action": action})
            except OdooError as exc:
                fps_created.append({"preset": preset, "error": str(exc)})

    # 5. Anyadir la company a admin para que la vea
    admin_id = client.call(
        "res.users", "search", [[("login", "=", "admin")]], {"limit": 1}
    )
    if admin_id:
        client.call(
            "res.users",
            "write",
            [admin_id, {"company_ids": [(4, company_id)]}],
        )

    json.dump(
        {
            "company": {
                "id": company_id,
                "action": company_action,
                "name": ns.name,
                "vat": ns.vat,
                "parent_id": parent_id,
            },
            "chart_template_action": chart_action,
            "journals": journals_created,
            "fiscal_positions": fps_created,
            "admin_company_added": bool(admin_id),
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
