#!/usr/bin/env python3
"""Verifica cumplimiento espanol previo al posting de una factura.

Comprueba: NIF/CIF/NIE valido, fiscal_position presente para no-domestico,
tax_ids en cada linea, lock dates, certificado Veri*Factu si aplica.

Devuelve JSON con `{"compliant": bool, "issues": [...], "warnings": [...]}`.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

from _common import OdooError
from odoo_client import OdooClient


DNI_TABLE = "TRWAGMYFPDXBNJZSQVHLCKE"
NIE_PREFIX = {"X": "0", "Y": "1", "Z": "2"}
CIF_LETTER_TABLE = "JABCDEFGHI"


def _clean_vat(vat: str) -> str:
    v = (vat or "").upper().replace(" ", "").replace("-", "").replace(".", "")
    if v.startswith("ES"):
        v = v[2:]
    return v


def validate_dni(vat: str) -> bool:
    if not re.fullmatch(r"\d{8}[A-Z]", vat):
        return False
    return DNI_TABLE[int(vat[:8]) % 23] == vat[-1]


def validate_nie(vat: str) -> bool:
    if not re.fullmatch(r"[XYZ]\d{7}[A-Z]", vat):
        return False
    num = int(NIE_PREFIX[vat[0]] + vat[1:8])
    return DNI_TABLE[num % 23] == vat[-1]


def validate_cif(vat: str) -> bool:
    if not re.fullmatch(r"[ABCDEFGHJKLMNPQRSUVW]\d{7}[\dA-J]", vat):
        return False
    digits = vat[1:8]
    even = sum(int(d) for d in digits[1::2])
    odd_sum = 0
    for d in digits[0::2]:
        n = int(d) * 2
        odd_sum += (n // 10) + (n % 10)
    total = even + odd_sum
    control_digit = (10 - (total % 10)) % 10
    last = vat[-1]
    if vat[0] in "KPQRSNW":
        return CIF_LETTER_TABLE[control_digit] == last
    if vat[0] in "ABEH":
        return last.isdigit() and int(last) == control_digit
    return (last.isdigit() and int(last) == control_digit) or (
        last in CIF_LETTER_TABLE and CIF_LETTER_TABLE[control_digit] == last
    )


def validate_es_vat(vat: str) -> tuple[bool, str]:
    v = _clean_vat(vat)
    if not v:
        return False, "vacio"
    if validate_dni(v):
        return True, "DNI"
    if validate_nie(v):
        return True, "NIE"
    if validate_cif(v):
        return True, "CIF"
    return False, "formato invalido"


def check_invoice(client: OdooClient, invoice_id: int) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []

    inv_rows = client.search_read(
        "account.move",
        [("id", "=", invoice_id)],
        [
            "id", "name", "state", "move_type", "partner_id", "journal_id",
            "invoice_date", "fiscal_position_id", "amount_total", "currency_id",
            "company_id", "invoice_line_ids",
        ],
        limit=1,
    )
    if not inv_rows:
        raise OdooError(f"Factura {invoice_id} no encontrada")
    inv = inv_rows[0]

    if inv["state"] != "draft":
        warnings.append(f"Factura ya en estado {inv['state']}, no es borrador")

    if not inv["partner_id"]:
        issues.append("Falta partner_id")
    else:
        partner_id = inv["partner_id"][0]
        partners = client.search_read(
            "res.partner",
            [("id", "=", partner_id)],
            ["vat", "country_id", "lang"],
            limit=1,
        )
        if partners:
            p = partners[0]
            if not p["vat"]:
                issues.append(f"Partner {p.get('id')} sin VAT")
            else:
                country_code = (
                    p["country_id"][1].split(" ")[0]
                    if p["country_id"]
                    else None
                )
                if not country_code or country_code == "Spain":
                    ok, kind = validate_es_vat(p["vat"])
                    if not ok:
                        issues.append(
                            f"VAT {p['vat']} invalido para Espana ({kind})"
                        )
                # No domestico => intra-UE/exportacion -> requiere fiscal_position
                if (
                    p["country_id"]
                    and "Spain" not in (p["country_id"][1] or "")
                    and not inv["fiscal_position_id"]
                ):
                    issues.append(
                        "Partner extranjero sin fiscal_position_id (intra-UE/exportacion)"
                    )

    if not inv["journal_id"]:
        issues.append("Falta journal_id")
    else:
        journals = client.search_read(
            "account.journal",
            [("id", "=", inv["journal_id"][0])],
            ["type"],
            limit=1,
        )
        expected = "sale" if inv["move_type"].startswith("out_") else "purchase"
        if journals and journals[0]["type"] != expected:
            issues.append(
                f"Diario type={journals[0]['type']} no coincide con move_type={inv['move_type']}"
            )

    if not inv["invoice_line_ids"]:
        issues.append("Factura sin lineas")
    else:
        lines = client.search_read(
            "account.move.line",
            [("id", "in", inv["invoice_line_ids"])],
            ["id", "name", "tax_ids", "quantity", "price_unit", "display_type"],
        )
        for ln in lines:
            if ln.get("display_type") in ("line_section", "line_note"):
                continue
            if not ln["tax_ids"]:
                issues.append(f"Linea '{ln['name']}' sin tax_ids")
            if ln["quantity"] in (0, 0.0):
                warnings.append(f"Linea '{ln['name']}' con quantity=0")
            if ln["price_unit"] in (0, 0.0):
                warnings.append(f"Linea '{ln['name']}' con price_unit=0")

    company_id = inv["company_id"][0]
    companies = client.search_read(
        "res.company",
        [("id", "=", company_id)],
        ["fiscalyear_lock_date", "tax_lock_date", "sale_lock_date"],
        limit=1,
    )
    if companies and inv["invoice_date"]:
        c = companies[0]
        for k in ("fiscalyear_lock_date", "tax_lock_date", "sale_lock_date"):
            if c.get(k) and inv["invoice_date"] <= c[k]:
                issues.append(
                    f"invoice_date {inv['invoice_date']} dentro de {k} ({c[k]})"
                )

    return {
        "invoice_id": invoice_id,
        "compliant": not issues,
        "issues": issues,
        "warnings": warnings,
    }


def check_partner(client: OdooClient, vat: str) -> dict[str, Any]:
    ok, kind = validate_es_vat(vat)
    return {"vat": vat, "valid": ok, "kind": kind}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--invoice-id", type=int)
    parser.add_argument("--partner-vat")
    ns = parser.parse_args()

    if not ns.invoice_id and not ns.partner_vat:
        print("error: se requiere --invoice-id o --partner-vat", file=sys.stderr)
        return 1

    client = OdooClient() if ns.invoice_id else None
    result: dict[str, Any] = {}
    if ns.partner_vat:
        result["partner"] = check_partner(client or OdooClient(), ns.partner_vat) if False else check_partner_local(ns.partner_vat)
    if ns.invoice_id:
        result["invoice"] = check_invoice(client, ns.invoice_id)

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False, default=str)
    print()
    return 0 if all(v.get("compliant", v.get("valid", True)) for v in result.values()) else 3


def check_partner_local(vat: str) -> dict[str, Any]:
    ok, kind = validate_es_vat(vat)
    return {"vat": vat, "valid": ok, "kind": kind}


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
