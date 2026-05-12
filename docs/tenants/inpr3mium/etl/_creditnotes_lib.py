"""Helpers + orquestacion para `loader_creditnotes.py` (paso 5 del ETL).

Carga `documents/creditnote.jsonl` (678 docs Holded, todos prefix `AC-`)
-> `account.move` con `move_type='out_refund'`. Ext_id
`__holded__.creditnote_<id>`.

Diferencias con loader 3 (invoices):
- `move_type = 'out_refund'` (no 'out_invoice').
- `journal_id` = AC- siempre (Fase 4.3 lo creo como journal separado;
  NO usa refund_sequence de A-).
- Si `doc.from.docType == 'invoice'` y `from.id` resoluble como ext_id
  `__holded__.invoice_<id>`, setear `reversed_entry_id = move_id`.
  Si no, refund standalone (Odoo lo permite).
- status=3 (5 docs en dump): "en revision" segun analisis manual.
  Cargados pero NUNCA posteados (politica conservadora — operador
  decide despues caso por caso).
- Lo demas (resolvers, line building, dup detection, date handling,
  name preservation) idéntico al loader 3 -> reusamos importando
  desde _invoices_lib.

Politica de numeracion (operador 2026-05-12): `name = docNumber`
literal. Las creditnotes preservan AC-001133, AC-001842, etc.
"""
from __future__ import annotations

import csv
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Reuso masivo: helpers puros + indices + line builder.
from _invoices_lib import (
    ACC_JOURNAL_CODE,
    STATUS_CANCELLED,
    STATUS_DRAFT,
    STATUS_POSTED,
    _build_line,
    build_index_by_id,
    build_invoice_line_vals,  # alias, sirve para line
    extract_item_tax_key,
    iter_jsonl,
    lookup_journals_by_code,
    lookup_partners_by_holded_ids,
    lookup_product_template_to_variant,
    parse_doc_prefix,
    search_ext_id,
)
from holded_resolvers import EXT_MODULE, HoldedResolvers, iso_from_unix


# status Holded "en revision" — visto en 5 docs del dump inpr3mium.
# Probable: aprobacion pendiente del responsable contable. Cargamos
# en draft Odoo y NUNCA posteamos automaticamente.
STATUS_REVIEW = 3

# Solo AC- mapea a `out_refund` en el plan de cuentas inpr3mium.
# Fase 4.3 documento la decision: AC- es journal separado, no usa
# refund_sequence de A- porque Holded mezcla creditnote real +
# rectificativas de aumento bajo el mismo prefijo. PR- (in_refund)
# va por reversal en loader 4.b, no aqui.
REFUND_PREFIXES: set[str] = {"AC-"}


@dataclass
class CreditNoteStats:
    total: int = 0
    created: int = 0
    updated: int = 0
    would_create: int = 0
    would_update: int = 0
    posted: int = 0
    post_failed: int = 0
    skip_cancelled: int = 0
    skip_review: int = 0          # status=3 cargados como draft, no post
    skip_unmapped_prefix: int = 0
    skip_no_contact: int = 0
    skip_existing_posted: int = 0
    skip_other: int = 0
    partner_unresolved: int = 0
    journal_unresolved: int = 0
    tax_unresolved_lines: int = 0
    multi_tax_lines: int = 0
    items_total: int = 0
    items_no_product: int = 0
    items_no_account: int = 0
    items_orphan_channel: int = 0
    reversed_entry_linked: int = 0   # `from.id` resoluble -> reversed_entry_id set
    reversed_entry_orphan: int = 0    # `from.id` informado pero no resoluble
    standalone_refunds: int = 0       # sin doc.from
    duplicate_docnumber_name_dropped: int = 0
    converted_negative_to_invoice: int = 0  # total<0 → reasignado a out_invoice + journal ACC-
    errors: int = 0
    error_details: list[tuple[str, str]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def should_skip_refund(doc: dict) -> tuple[bool, str]:
    """Decide si un doc creditnote se salta. Devuelve (skip, reason).

    - 'cancelled': status=2.
    - 'no_contact': contact vacio (no esperado en dump inpr3mium).
    - 'unmapped_prefix': prefijo no AC-.

    NB: status=3 (review) NO se salta. Se carga como draft y nunca
    se postea (el flag --post solo postea status=1).
    """
    if doc.get("status") == STATUS_CANCELLED:
        return (True, "cancelled")
    if not doc.get("contact"):
        return (True, "no_contact")
    prefix = parse_doc_prefix(doc.get("docNumber"))
    if not prefix or prefix not in REFUND_PREFIXES:
        return (True, "unmapped_prefix")
    return (False, "")


def build_refund_header_vals(
    doc: dict,
    *,
    partner_id: int,
    journal_id: int,
    company_id: int | None = None,
    reversed_entry_id: int | None = None,
    duplicate_alt_id: str | None = None,
    converted_to_invoice: bool = False,
) -> dict:
    """Mapea un doc Holded creditnote a vals de account.move out_refund.

    Args:
        doc: dict JSONL.
        partner_id: res.partner.id.
        journal_id: account.journal.id (AC-).
        company_id: explicit company.
        reversed_entry_id: si el invoice original esta cargado en Odoo,
            su account.move.id. Odoo enlaza el refund visualmente y
            permite reconciliacion automatica.
        duplicate_alt_id: holded_id del doc "ganador" del par dup; si
            informado, `name` no se setea (queda '/') y se anyade nota.

    `name = doc.docNumber` literal (politica operador). `ref` tambien.
    `invoice_date` = doc.date; `date` = accountingDate or date.
    """
    invoice_date = iso_from_unix(doc.get("date"))
    accounting_date = iso_from_unix(doc.get("accountingDate")) or invoice_date
    due_date = iso_from_unix(doc.get("dueDate"))
    docnum = doc.get("docNumber") or ""

    final_move_type = "out_invoice" if converted_to_invoice else "out_refund"
    vals: dict[str, Any] = {
        "move_type": final_move_type,
        "partner_id": partner_id,
        "journal_id": journal_id,
        "ref": docnum,
    }
    # Solo setea name si NO es conversion (politica: ACC-NNNNNN desde sequence)
    if docnum and not duplicate_alt_id and not converted_to_invoice:
        vals["name"] = docnum
    if invoice_date:
        vals["invoice_date"] = invoice_date
    if accounting_date:
        vals["date"] = accounting_date
    if due_date:
        vals["invoice_date_due"] = due_date
    if reversed_entry_id:
        vals["reversed_entry_id"] = reversed_entry_id

    notes = (doc.get("notes") or "").strip()
    desc = (doc.get("desc") or "").strip()
    narration_parts = [p for p in (desc, notes) if p and p != docnum]
    if duplicate_alt_id:
        narration_parts.append(
            f"<strong>WARN duplicado Holded</strong>: docNumber <code>{docnum}</code> "
            f"compartido (otro holded_id: {duplicate_alt_id})."
        )
    if doc.get("status") == STATUS_REVIEW:
        narration_parts.append(
            "<strong>STATUS HOLDED=3 (review)</strong>: cargada en draft. "
            "Operador decide post manual tras revisar."
        )
    if converted_to_invoice:
        narration_parts.append(
            f"<strong>CONVERTIDO out_refund -> out_invoice</strong>: el doc Holded "
            f"<code>{docnum}</code> tenia total&lt;0 (rectificativa de aumento) pero "
            f"estaba almacenado en creditnote.jsonl. Reasignado a journal ACC- "
            f"(Conversiones carga histórica). Buscable por ref=<code>{docnum}</code>. "
            f"Decision operador 2026-05-12, ver runbook-migration-holded.md."
        )
    if narration_parts:
        vals["narration"] = "<br/>".join(narration_parts)
    if company_id:
        vals["company_id"] = company_id
    return vals


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def load_creditnotes(
    client: Any,
    resolvers: HoldedResolvers,
    dump_dir: Path,
    *,
    dry_run: bool = False,
    limit: int | None = None,
    post: bool = False,
    report_dir: Path | None = None,
) -> CreditNoteStats:
    """Carga `documents/creditnote.jsonl` -> account.move out_refund.

    Args:
        client, resolvers, dump_dir: idem loader 3.
        dry_run: simula sin escribir.
        limit: procesa solo los primeros N docs.
        post: si True, action_post() para docs con status=1 (NO status=3).
    """
    input_path = dump_dir / "documents" / "creditnote.jsonl"

    upsert = None
    if not dry_run:
        try:
            from ext_id_upsert import upsert as _upsert
            upsert = _upsert
        except ImportError as exc:
            raise RuntimeError(
                "ext_id_upsert no en PYTHONPATH."
            ) from exc

    docs = list(iter_jsonl(input_path))
    if limit:
        docs = docs[:limit]

    stats = CreditNoteStats(total=len(docs))

    # Duplicate detection (defensive; dump inpr3mium 2026-05-11 tiene 0).
    docs_by_num: dict[str, list[dict]] = {}
    for d in docs:
        dn = d.get("docNumber")
        if dn:
            docs_by_num.setdefault(dn, []).append(d)
    duplicate_losers: dict[str, str] = {}
    for dn, group in docs_by_num.items():
        if len(group) <= 1:
            continue
        ranked = sorted(group, key=lambda x: float(x.get("date") or 0), reverse=True)
        winner = ranked[0]
        for loser in ranked[1:]:
            duplicate_losers[loser["id"]] = winner["id"]

    # Pre-fetch indices
    saleschannels_idx = build_index_by_id(iter_jsonl(dump_dir / "saleschannels.jsonl"))

    # Journal ACC- para conversiones total<0 -> out_invoice
    acc_journal_id: int | None = None
    hits = client.call("account.journal", "search_read",
                       [[("code", "=", ACC_JOURNAL_CODE)]],
                       {"fields": ["id"], "limit": 1})
    if hits:
        acc_journal_id = hits[0]["id"]

    contact_ids: set[str] = set()
    product_holded_ids: set[str] = set()
    invoice_holded_ids: set[str] = set()  # para resolver reversed_entry_id
    journal_prefixes: set[str] = set()
    for d in docs:
        if d.get("contact"):
            contact_ids.add(d["contact"])
        prefix = parse_doc_prefix(d.get("docNumber"))
        if prefix:
            journal_prefixes.add(prefix)
        for it in d.get("products") or []:
            pid = it.get("productId")
            if pid:
                product_holded_ids.add(pid)
        fr = d.get("from")
        if fr and fr.get("docType") == "invoice" and fr.get("id"):
            invoice_holded_ids.add(fr["id"])

    partner_by_holded = lookup_partners_by_holded_ids(client, contact_ids)
    journal_by_code = lookup_journals_by_code(client, journal_prefixes)

    # Lookup invoices originales por ext_id `__holded__.invoice_<id>`
    invoice_move_by_holded = _lookup_invoice_moves(client, invoice_holded_ids)

    # Templates -> variant (lookup_product_template_to_variant pide el
    # set de template_ids ya resueltos; aqui resolvemos primero via ext_id)
    template_by_holded: dict[str, int] = {}
    if product_holded_ids:
        names = [f"product_{p}" for p in product_holded_ids] + \
                [f"service_{p}" for p in product_holded_ids]
        for i in range(0, len(names), 200):
            chunk = names[i:i+200]
            hits = client.call(
                "ir.model.data", "search_read",
                [[("module", "=", EXT_MODULE), ("name", "in", chunk),
                  ("model", "=", "product.template")]],
                {"fields": ["name", "res_id"]},
            )
            for h in hits:
                _, pid = h["name"].split("_", 1)
                template_by_holded[pid] = h["res_id"]
    variant_by_template = lookup_product_template_to_variant(
        client, set(template_by_holded.values())
    )

    unknown_partner_id = None
    unk = search_ext_id(client, f"{EXT_MODULE}.contact__unknown")
    if unk:
        unknown_partner_id, _ = unk

    default_income_id: int | None = None
    if not dry_run:
        hits = client.call(
            "account.account", "search_read",
            [[("code", "=", "705000")]],
            {"fields": ["id"], "limit": 1},
        )
        if hits:
            default_income_id = hits[0]["id"]

    rows: list[dict[str, Any]] = []
    for doc in docs:
        row = _process_doc(
            client, resolvers, doc,
            saleschannels_idx=saleschannels_idx,
            partner_by_holded=partner_by_holded,
            template_by_holded=template_by_holded,
            variant_by_template=variant_by_template,
            journal_by_code=journal_by_code,
            invoice_move_by_holded=invoice_move_by_holded,
            unknown_partner_id=unknown_partner_id,
            default_income_id=default_income_id,
            duplicate_losers=duplicate_losers,
            acc_journal_id=acc_journal_id,
            stats=stats, dry_run=dry_run, post=post, upsert=upsert,
        )
        rows.append(row)

    _write_report(rows, dump_dir, dry_run, report_dir)
    return stats


def _lookup_invoice_moves(client: Any, holded_invoice_ids: set[str]) -> dict[str, int]:
    """Devuelve `{holded_invoice_id: account.move.id}` via ext_id."""
    if not holded_invoice_ids:
        return {}
    out: dict[str, int] = {}
    names = [f"invoice_{i}" for i in holded_invoice_ids]
    for i in range(0, len(names), 200):
        chunk = names[i:i+200]
        hits = client.call(
            "ir.model.data", "search_read",
            [[("module", "=", EXT_MODULE), ("name", "in", chunk),
              ("model", "=", "account.move")]],
            {"fields": ["name", "res_id"]},
        )
        for h in hits:
            _, hid = h["name"].split("_", 1)
            out[hid] = h["res_id"]
    return out


def _process_doc(
    client: Any,
    resolvers: HoldedResolvers,
    doc: dict,
    *,
    saleschannels_idx: dict[str, str],
    partner_by_holded: dict[str, int],
    template_by_holded: dict[str, int],
    variant_by_template: dict[int, int],
    journal_by_code: dict[str, int],
    invoice_move_by_holded: dict[str, int],
    unknown_partner_id: int | None,
    default_income_id: int | None,
    duplicate_losers: dict[str, str],
    acc_journal_id: int | None,
    stats: CreditNoteStats,
    dry_run: bool,
    post: bool,
    upsert: Any,
) -> dict:
    hid = doc.get("id") or ""
    xmlid = f"{EXT_MODULE}.creditnote_{hid}"
    docnum = doc.get("docNumber") or ""

    row: dict[str, Any] = {
        "holded_id": hid,
        "docNumber": docnum,
        "contact": doc.get("contact") or "",
        "date": iso_from_unix(doc.get("date")) or "",
        "status": doc.get("status"),
        "from_invoice": (doc.get("from") or {}).get("id") if (doc.get("from") or {}).get("docType") == "invoice" else "",
        "n_items": len(doc.get("products") or []),
        "total_holded": doc.get("total"),
        "xmlid": xmlid,
        "reversed_entry_id": "",
        "result": "",
        "res_id": "",
        "error": "",
    }

    skip, reason = should_skip_refund(doc)
    if skip:
        row["result"] = f"skip_{reason}"
        if reason == "cancelled":
            stats.skip_cancelled += 1
        elif reason == "no_contact":
            stats.skip_no_contact += 1
        elif reason == "unmapped_prefix":
            stats.skip_unmapped_prefix += 1
        else:
            stats.skip_other += 1
        return row

    if doc.get("status") == STATUS_REVIEW:
        stats.skip_review += 1
        # NB: no se hace return — el doc SI se carga (con narration warn),
        # solo que no se postea.

    # partner
    partner_id = partner_by_holded.get(doc["contact"])
    if not partner_id and unknown_partner_id:
        partner_id = unknown_partner_id
        row["result"] = "partner_to_unknown"
    if not partner_id:
        stats.partner_unresolved += 1
        row["result"] = "error"
        row["error"] = f"partner {doc['contact']} sin ext_id"
        stats.errors += 1
        stats.error_details.append((hid, row["error"]))
        return row

    # journal
    prefix = parse_doc_prefix(docnum)
    journal_id = journal_by_code.get(prefix) if prefix else None
    if not journal_id:
        stats.journal_unresolved += 1
        row["result"] = "error"
        row["error"] = f"journal code {prefix!r} no existe"
        stats.errors += 1
        stats.error_details.append((hid, row["error"]))
        return row

    # reversed_entry_id (link al invoice original si cargado)
    reversed_entry_id: int | None = None
    fr = doc.get("from") or {}
    if fr.get("docType") == "invoice" and fr.get("id"):
        rid = invoice_move_by_holded.get(fr["id"])
        if rid:
            reversed_entry_id = rid
            row["reversed_entry_id"] = rid
            stats.reversed_entry_linked += 1
        else:
            stats.reversed_entry_orphan += 1
    else:
        stats.standalone_refunds += 1

    # Conversion: si total<0 reasignar a out_invoice + journal ACC-.
    convert_to_invoice = False
    total_holded = float(doc.get("total") or 0.0)
    if total_holded < 0 and acc_journal_id:
        convert_to_invoice = True
        journal_id = acc_journal_id
        stats.converted_negative_to_invoice += 1
        # NB: reversed_entry_id NO aplica a out_invoice; nulificar
        reversed_entry_id = None

    # Lines
    items = doc.get("products") or []
    stats.items_total += len(items)
    line_ids: list[tuple] = []
    has_err = False
    for it in items:
        line_vals = _build_line(
            it, resolvers,
            saleschannels_idx=saleschannels_idx,
            template_by_holded=template_by_holded,
            variant_by_template=variant_by_template,
            default_income_id=default_income_id,
            flip_signs=convert_to_invoice,
            stats=stats,
        )
        if line_vals is None:
            has_err = True
            break
        line_ids.append((0, 0, line_vals))

    if has_err:
        stats.errors += 1
        row["result"] = "error"
        row["error"] = "line aborta (ver tax_unresolved_lines / multi_tax_lines)"
        stats.error_details.append((hid, row["error"]))
        return row

    dup_winner = duplicate_losers.get(hid)
    if dup_winner:
        stats.duplicate_docnumber_name_dropped += 1
    header = build_refund_header_vals(
        doc, partner_id=partner_id, journal_id=journal_id,
        reversed_entry_id=reversed_entry_id, duplicate_alt_id=dup_winner,
        converted_to_invoice=convert_to_invoice,
    )
    header["invoice_line_ids"] = line_ids

    if dry_run:
        existing = search_ext_id(client, xmlid)
        if existing:
            row["result"] = "would_update"
            row["res_id"] = existing[0]
            stats.would_update += 1
        else:
            row["result"] = "would_create"
            stats.would_create += 1
        return row

    existing = search_ext_id(client, xmlid)
    if existing:
        res_id, model = existing
        state_data = client.call("account.move", "read", [[res_id], ["state"]])
        if state_data and state_data[0]["state"] != "draft":
            row["result"] = "skip_existing_posted"
            row["res_id"] = res_id
            stats.skip_existing_posted += 1
            return row
        write_vals = dict(header)
        write_vals["invoice_line_ids"] = [(5, 0, 0)] + line_ids
        try:
            client.call("account.move", "write", [[res_id], write_vals])
        except Exception as exc:
            row["result"] = "error"
            row["error"] = f"write: {exc}"
            stats.errors += 1
            stats.error_details.append((hid, row["error"]))
            return row
        stats.updated += 1
        row["result"] = "updated_draft"
        row["res_id"] = res_id
    else:
        try:
            res_id, _ = upsert(client, xmlid, "account.move", header, noupdate=True)
        except Exception as exc:
            row["result"] = "error"
            row["error"] = f"upsert: {exc}"
            stats.errors += 1
            stats.error_details.append((hid, row["error"]))
            return row
        stats.created += 1
        row["result"] = "created"
        row["res_id"] = res_id

    # Post solo status=1 (NUNCA status=3).
    if post and doc.get("status") == STATUS_POSTED:
        try:
            client.call("account.move", "action_post", [[row["res_id"]]])
            stats.posted += 1
            row["result"] += "+posted"
        except Exception as exc:
            stats.post_failed += 1
            row["error"] = f"action_post: {exc}"
            stats.errors += 1
            stats.error_details.append((hid, row["error"]))

    return row


def _write_report(rows, dump_dir, dry_run, report_dir):
    if report_dir is None:
        report_dir = dump_dir / ".etl_reports"
    report_dir.mkdir(exist_ok=True)
    mode_tag = "dryrun" if dry_run else "run"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = report_dir / f"creditnotes_{mode_tag}_{ts}.csv"
    if not rows:
        return
    fields_order = [
        "holded_id", "docNumber", "contact", "date", "status",
        "from_invoice", "reversed_entry_id", "n_items", "total_holded",
        "xmlid", "result", "res_id", "error",
    ]
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields_order, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"report: {out}", file=sys.stderr)


def print_summary(stats: CreditNoteStats, dry_run: bool, post: bool) -> None:
    mode = "DRY-RUN" if dry_run else ("REAL+POST" if post else "REAL")
    print(f"\n[creditnotes {mode}]")
    print(f"  total docs:                {stats.total}")
    if dry_run:
        print(f"  would_create:              {stats.would_create}")
        print(f"  would_update:              {stats.would_update}")
    else:
        print(f"  created:                   {stats.created}")
        print(f"  updated:                   {stats.updated}")
        if post:
            print(f"  posted (only status=1):    {stats.posted}")
            print(f"  post_failed:               {stats.post_failed}")
    print(f"  skip_cancelled (status=2):    {stats.skip_cancelled}")
    print(f"  skip_review (status=3, loaded draft only): {stats.skip_review}")
    print(f"  skip_unmapped_prefix:          {stats.skip_unmapped_prefix}")
    print(f"  skip_existing_posted:          {stats.skip_existing_posted}")
    print(f"  partner_unresolved:            {stats.partner_unresolved}")
    print(f"  journal_unresolved:            {stats.journal_unresolved}")
    print(f"  reversed_entry_linked:         {stats.reversed_entry_linked}")
    print(f"  reversed_entry_orphan:         {stats.reversed_entry_orphan}")
    print(f"  standalone_refunds:            {stats.standalone_refunds}")
    print(f"  items_total:                   {stats.items_total}")
    print(f"  items_no_product:              {stats.items_no_product}")
    print(f"  items_orphan_channel:          {stats.items_orphan_channel}")
    print(f"  tax_unresolved_lines:          {stats.tax_unresolved_lines}")
    print(f"  multi_tax_lines:               {stats.multi_tax_lines}")
    print(f"  dup_docNumber_name_dropped:    {stats.duplicate_docnumber_name_dropped}")
    print(f"  errors:                        {stats.errors}")
    if stats.error_details:
        print("  primeros 10 errores:")
        for hid, reason in stats.error_details[:10]:
            print(f"    - {hid}: {reason}")
