#!/usr/bin/env python3
"""Genera el PDF de una factura via ir.actions.report._render_qweb_pdf.

Permite escoger una variante del reporte (estandar, con pagos, Veri*Factu,
TicketBAI). Devuelve PDF binario al stdout o lo guarda con --output.
"""
from __future__ import annotations

import argparse
import base64
import sys

from _common import OdooError
from odoo_client import OdooClient


REPORT_VARIANTS = {
    "standard": "account.report_invoice",
    "with_payments": "account.report_invoice_with_payments",
    "verifactu": "l10n_es_edi_verifactu.report_invoice_verifactu",
    "tbai": "l10n_es_edi_TBAI.report_invoice_tbai",
}


def render_pdf(
    client: OdooClient, invoice_id: int, *, variant: str = "standard"
) -> bytes:
    if variant not in REPORT_VARIANTS:
        raise OdooError(f"Variante desconocida: {variant}")
    report_name = REPORT_VARIANTS[variant]

    reports = client.search_read(
        "ir.actions.report",
        [("report_name", "=", report_name)],
        ["id"],
        limit=1,
    )
    if not reports:
        raise OdooError(f"Reporte '{report_name}' no encontrado en la instancia")
    report_id = reports[0]["id"]

    result = client.call(
        "ir.actions.report",
        "_render_qweb_pdf",
        [report_id, [invoice_id]],
    )
    # _render_qweb_pdf devuelve (bytes, mimetype). Sobre RPC el primer
    # elemento llega como base64 string.
    pdf_data = result[0] if isinstance(result, (list, tuple)) else result
    if isinstance(pdf_data, str):
        return base64.b64decode(pdf_data)
    return bytes(pdf_data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--invoice-id", type=int, required=True)
    parser.add_argument(
        "--variant",
        choices=list(REPORT_VARIANTS),
        default="standard",
    )
    parser.add_argument(
        "--output",
        help="Ruta destino. Si se omite, se imprime base64 al stdout.",
    )
    ns = parser.parse_args()

    client = OdooClient()
    pdf = render_pdf(client, ns.invoice_id, variant=ns.variant)
    if ns.output:
        with open(ns.output, "wb") as fh:
            fh.write(pdf)
        print(f"escrito {len(pdf)} bytes en {ns.output}", file=sys.stderr)
    else:
        sys.stdout.buffer.write(base64.b64encode(pdf))
        sys.stdout.buffer.write(b"\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
