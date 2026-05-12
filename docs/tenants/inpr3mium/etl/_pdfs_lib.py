"""Helpers + orquestacion para `loader_pdfs.py` (paso 9 del ETL).

Itera `holded-export/<date>/pdfs/<doctype>/<holded_id>.pdf` y crea
`ir.attachment` enlazado al `account.move` correspondiente via ext_id
`__holded__.<doctype>_<holded_id>` (loader 3/4/5 anterior). Idempotente:
si ya existe attachment con (res_model, res_id, name) iguales, skip.

Cumple requisito de auditoria AEAT: preservar el documento original
emitido/recibido (la "factura original entregada al cliente"). Las
facturas re-numeradas Odoo son representaciones contables; el PDF
Holded es el documento legal.

Decisiones (politica operador inpr3mium 2026-05-12):
- **Un PDF por move**: name = `<docNumber>.pdf` (no Holded id), mas
  legible en la UI ("AC-001842.pdf" en lugar de "6213fe..pdf").
- **Mimetype**: application/pdf. Odoo lo previsualizara inline.
- **Type**: 'binary' (no 'url'). Para 7.489 PDFs ~950 MB, el filestore
  Odoo absorbe sin problema.
- **Politica de tamanyo**: skip + warning si pdf > 50 MB (proteccion;
  no hay PDFs tan grandes en inpr3mium pero defensivo).
- **Doctypes soportados**: invoice (out_invoice), purchase (in_invoice),
  creditnote (out_refund), purchaserefund (in_refund). Cada uno
  con su ext_id prefix correspondiente.
- **No reintenta**: si attachment falla al crear, log y siguiente.
  No abortamos: prefiero cargar el 99% bueno que perder todo.
"""
from __future__ import annotations

import base64
import csv
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# ext_id prefix por doctype Holded
DOCTYPE_TO_EXTID_PREFIX = {
    "invoice": "invoice",
    "purchase": "purchase",
    "creditnote": "creditnote",
    "purchaserefund": "purchaserefund",
}

EXT_MODULE = "__holded__"
MAX_PDF_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


@dataclass
class PdfStats:
    total_pdfs: int = 0
    created: int = 0
    skipped_existing: int = 0
    skipped_no_move: int = 0       # no hay account.move con ese ext_id
    skipped_too_large: int = 0
    skipped_not_found: int = 0     # archivo PDF no existe
    errors: int = 0
    error_details: list[tuple[str, str]] = field(default_factory=list)


def find_move_by_holded_id(
    client: Any, holded_id: str, doctype: str,
) -> tuple[int, str] | None:
    """Devuelve (res_id, ref_docNumber) o None."""
    name = f"{DOCTYPE_TO_EXTID_PREFIX[doctype]}_{holded_id}"
    hits = client.call(
        "ir.model.data", "search_read",
        [[("module", "=", EXT_MODULE), ("name", "=", name)]],
        {"fields": ["res_id", "model"], "limit": 1},
    )
    if not hits:
        return None
    if hits[0]["model"] != "account.move":
        return None
    res_id = hits[0]["res_id"]
    # Lookup ref/name del move para nombrar el attachment de forma legible
    moves = client.call("account.move", "read", [[res_id], ["ref", "name"]])
    if not moves:
        return None
    docnum = moves[0].get("name") or moves[0].get("ref") or f"holded_{holded_id}"
    if docnum == "/":
        docnum = moves[0].get("ref") or f"holded_{holded_id}"
    return (res_id, str(docnum))


def attachment_exists(
    client: Any, move_id: int, attachment_name: str,
) -> bool:
    """True si ya existe ir.attachment con (account.move, move_id, name)."""
    hits = client.call(
        "ir.attachment", "search_count",
        [[
            ("res_model", "=", "account.move"),
            ("res_id", "=", move_id),
            ("name", "=", attachment_name),
        ]],
    )
    return hits > 0


def build_attachment_vals(
    pdf_bytes: bytes, *, move_id: int, attachment_name: str,
) -> dict:
    return {
        "name": attachment_name,
        "type": "binary",
        "datas": base64.b64encode(pdf_bytes).decode("ascii"),
        "res_model": "account.move",
        "res_id": move_id,
        "mimetype": "application/pdf",
    }


def load_pdfs_for_doctype(
    client: Any,
    dump_dir: Path,
    *,
    doctype: str,
    dry_run: bool = False,
    limit: int | None = None,
    report_dir: Path | None = None,
) -> PdfStats:
    """Itera `dump_dir/pdfs/<doctype>/*.pdf` y crea ir.attachment por archivo.

    Args:
        client: OdooClient con sesion activa.
        dump_dir: `holded-export/<YYYY-MM-DD>/`.
        doctype: uno de DOCTYPE_TO_EXTID_PREFIX.
        dry_run: si True, no escribe; solo simula y reporta.
        limit: procesa solo los primeros N PDFs.

    Returns:
        PdfStats.
    """
    pdf_dir = dump_dir / "pdfs" / doctype
    if not pdf_dir.exists():
        raise FileNotFoundError(f"No existe: {pdf_dir}")

    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if limit:
        pdfs = pdfs[:limit]

    stats = PdfStats(total_pdfs=len(pdfs))
    rows: list[dict[str, Any]] = []

    for pdf_path in pdfs:
        row = _process_pdf(
            client, pdf_path, doctype=doctype,
            stats=stats, dry_run=dry_run,
        )
        rows.append(row)

    _write_report(rows, dump_dir, doctype, dry_run, report_dir)
    return stats


def _process_pdf(
    client: Any, pdf_path: Path, *,
    doctype: str, stats: PdfStats, dry_run: bool,
) -> dict:
    holded_id = pdf_path.stem
    row = {
        "holded_id": holded_id,
        "doctype": doctype,
        "pdf_size_bytes": "",
        "move_id": "",
        "docnum": "",
        "attachment_name": "",
        "result": "",
        "error": "",
    }

    # Resolver move
    info = find_move_by_holded_id(client, holded_id, doctype)
    if not info:
        stats.skipped_no_move += 1
        row["result"] = "skip_no_move"
        return row
    move_id, docnum = info
    row["move_id"] = move_id
    row["docnum"] = docnum
    attachment_name = f"{docnum}.pdf"
    row["attachment_name"] = attachment_name

    # Tamanyo
    try:
        size = pdf_path.stat().st_size
    except OSError as exc:
        stats.skipped_not_found += 1
        row["result"] = "skip_not_found"
        row["error"] = str(exc)
        return row
    row["pdf_size_bytes"] = size
    if size > MAX_PDF_SIZE_BYTES:
        stats.skipped_too_large += 1
        row["result"] = "skip_too_large"
        return row

    # Idempotencia
    if attachment_exists(client, move_id, attachment_name):
        stats.skipped_existing += 1
        row["result"] = "skip_existing"
        return row

    if dry_run:
        row["result"] = "would_create"
        return row

    # Read + create
    try:
        with pdf_path.open("rb") as f:
            pdf_bytes = f.read()
        vals = build_attachment_vals(pdf_bytes, move_id=move_id, attachment_name=attachment_name)
        att_id = client.call("ir.attachment", "create", [vals])
    except Exception as exc:
        stats.errors += 1
        row["result"] = "error"
        row["error"] = f"create attachment: {exc}"
        stats.error_details.append((holded_id, row["error"]))
        return row

    stats.created += 1
    row["result"] = "created"
    row["attachment_id"] = att_id
    return row


def _write_report(
    rows: list[dict], dump_dir: Path, doctype: str,
    dry_run: bool, report_dir: Path | None,
) -> None:
    if report_dir is None:
        report_dir = dump_dir / ".etl_reports"
    report_dir.mkdir(exist_ok=True)
    mode_tag = "dryrun" if dry_run else "run"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = report_dir / f"pdfs_{doctype}_{mode_tag}_{ts}.csv"
    if not rows:
        return
    fields_order = [
        "holded_id", "doctype", "pdf_size_bytes", "move_id", "docnum",
        "attachment_name", "result", "error",
    ]
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields_order, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"report: {out}", file=sys.stderr)


def print_summary(stats: PdfStats, doctype: str, dry_run: bool) -> None:
    mode = "DRY-RUN" if dry_run else "REAL"
    print(f"\n[pdfs {doctype} {mode}]")
    print(f"  total PDFs:        {stats.total_pdfs}")
    if dry_run:
        print(f"  would_create:      {stats.total_pdfs - stats.skipped_existing - stats.skipped_no_move - stats.skipped_not_found - stats.skipped_too_large}")
    else:
        print(f"  created:           {stats.created}")
    print(f"  skip_existing:     {stats.skipped_existing}")
    print(f"  skip_no_move:      {stats.skipped_no_move}")
    print(f"  skip_not_found:    {stats.skipped_not_found}")
    print(f"  skip_too_large:    {stats.skipped_too_large}")
    print(f"  errors:            {stats.errors}")
    if stats.error_details:
        print("  primeros 10 errores:")
        for hid, reason in stats.error_details[:10]:
            print(f"    - {hid}: {reason}")
