"""Helpers + orquestacion para `loader_payments.py` (paso 7 del ETL).

Carga `payments.jsonl` (708 docs Holded) -> `account.payment` Odoo.
Filtrado: solo `documentType in {'invoice', 'creditnote'}` (113 docs)
que enlazan a moves ya cargados por loaders 3/5.

**Out of scope MVP**:
- `documentType='purchase'` (24 docs): bloqueado hasta loader 4.
- `documentType in {'trans','payroll','entry'}` (571 docs): son
  asientos contables manuales, no payments cliente/proveedor. Se
  cubrirán como `account.move` tipo 'entry' en loader 8 dailyledger
  o como ad-hoc post-cutover.
- payments sin contactId (~222): mayoría son transferencias internas
  (documentType=trans) — ya filtradas arriba. Si algún invoice/
  creditnote payment no tiene contactId, se reporta + skip.
- payments con bankId no mapeable a journal (cards, BBVA1, TRASHOLDED,
  cuenta 555 PGCE): skip + report. Operador decide reasignar manualmente.

**Politica de carga**:
- State `draft` (NO `action_post` por defecto).
- NO reconciliar con el move target — se hará en Fase 5.5 cutover
  cuando sequences pre-loaded. Hoy solo cargamos el dato.
- `ref = doc.id` Holded (auditoría).
- `memo` (Odoo `communication`) = `doc.desc` o `'Pago <docNumber>'`.

**Mapeo bankId → journal_id**: tabla hardcoded basada en snapshot
Fase 5.0 (`2026-05-11_fase-5.0.json -> bank_journals[]`). Si se
añaden journals nuevos, actualizar `BANK_TO_JOURNAL`.
"""
from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from holded_resolvers import EXT_MODULE, HoldedResolvers, iso_from_unix


# Holded bankId -> Odoo journal_id. Snapshot Fase 5.0 + lookup en
# treasuries.jsonl 2026-05-11. Solo bancos productivos (type=bank con
# IBAN); las tarjetas (type=card), TRASHOLDED, BBVA1, "55500000007"
# (cuenta PGCE 555), Linea descuento Sabadell quedan sin mapear -> skip.
#
# IMPORTANTE: si se carga un dump de otro tenant o de fecha distinta
# con bankIds nuevos, este mapa debe actualizarse. La tabla canónica
# está en `snapshots/<date>_fase-5.0.json -> bank_journals[]`.
BANK_TO_JOURNAL: dict[str, int] = {
    "61013fa838b60f17a33fb389": 19,   # Santander
    "636a8dfd2ccbf2c8b10c7e44": 22,   # Qonto
    "61014aff2eb1195d0b646fe0": 21,   # Banco Sabadell
    "61014a7f6b2623537c10ba58": 20,   # BBVA
}

# documentTypes que mapean a account.payment con move target en Odoo.
# 'purchase' añadido cuando loader 4 esté ejecutado.
SUPPORTED_DOC_TYPES_MVP: set[str] = {"invoice", "creditnote"}
SUPPORTED_DOC_TYPES_FULL: set[str] = {"invoice", "creditnote", "purchase"}


@dataclass
class PaymentStats:
    total: int = 0
    created: int = 0
    updated: int = 0
    would_create: int = 0
    would_update: int = 0
    skip_doc_type_unsupported: int = 0  # trans/payroll/entry/purchase(MVP)
    skip_no_contact: int = 0
    skip_no_bank: int = 0
    skip_bank_unmapped: int = 0          # bankId no en BANK_TO_JOURNAL
    skip_partner_unresolved: int = 0
    skip_move_unresolved: int = 0        # documentId no resoluble como ext_id
    skip_zero_amount: int = 0
    skip_existing: int = 0
    errors: int = 0
    error_details: list[tuple[str, str]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def derive_payment_type(doc_type: str, amount: float) -> str:
    """Devuelve 'inbound' (cobro) o 'outbound' (pago).

    Convencion Holded:
    - invoice + amount > 0  -> inbound  (cliente paga)
    - invoice + amount < 0  -> outbound (reembolso al cliente, raro)
    - creditnote + amount > 0 -> outbound (devuelvo al cliente)
    - creditnote + amount < 0 -> inbound  (cliente devuelve, raro)
    - purchase + amount > 0 -> outbound (pago al proveedor)
    - purchase + amount < 0 -> inbound  (proveedor devuelve)

    Simplificacion: el signo del amount Holded indica si entra (+) o
    sale (-) del banco. Para 'creditnote' (out_refund Odoo), el flujo
    natural es lo opuesto a invoice. Aquí usamos el signo crudo.
    """
    # Holded: amount > 0 = entra al banco; amount < 0 = sale.
    if amount > 0:
        return "inbound"
    return "outbound"


def derive_partner_type(doc_type: str) -> str:
    """Devuelve 'customer' o 'supplier' segun doc_type."""
    if doc_type in ("invoice", "creditnote"):
        return "customer"
    if doc_type in ("purchase", "purchaserefund"):
        return "supplier"
    return "customer"  # default defensivo


def build_payment_vals(
    doc: dict,
    *,
    partner_id: int,
    journal_id: int,
    target_move_id: int | None = None,
) -> dict:
    """Mapea un doc Holded payment a vals de `account.payment.create()`.

    Args:
        doc: dict JSONL.
        partner_id: res.partner.id.
        journal_id: account.journal.id (bank).
        target_move_id: account.move.id del invoice/creditnote/purchase
            al que paga. Hoy NO se reconcilia automaticamente (Fase 5.5);
            queda en `ref` extendido para trazabilidad.
    """
    amount = float(doc.get("amount") or 0.0)
    doc_type = doc.get("documentType") or ""
    payment_date = iso_from_unix(doc.get("date"))

    vals: dict[str, Any] = {
        "partner_id": partner_id,
        "journal_id": journal_id,
        "amount": abs(amount),
        "payment_type": derive_payment_type(doc_type, amount),
        "partner_type": derive_partner_type(doc_type),
    }
    if payment_date:
        vals["date"] = payment_date
    # `account.payment` Odoo 19 NO tiene `ref` (es del move generado).
    # El holded_id queda en ext_id `__holded__.payment_<id>` (auditoría).
    # El memo es lo unico visible en UI -> consolidamos desc + link Holded.
    memo_parts = []
    desc = (doc.get("desc") or "").strip()
    if desc:
        memo_parts.append(desc)
    holded_id = doc.get("id") or ""
    if holded_id:
        memo_parts.append(f"[holded:{holded_id}]")
    if target_move_id:
        memo_parts.append(f"(doc_id={doc.get('documentId')})")
    if memo_parts:
        vals["memo"] = " ".join(memo_parts)
    return vals


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def iter_jsonl(path: Path):
    if not path.exists():
        return
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def search_ext_id(client: Any, xmlid: str) -> tuple[int, str] | None:
    module, name = xmlid.split(".", 1)
    hits = client.call(
        "ir.model.data", "search_read",
        [[("module", "=", module), ("name", "=", name)]],
        {"fields": ["res_id", "model"], "limit": 1},
    )
    if not hits:
        return None
    return (hits[0]["res_id"], hits[0]["model"])


def _xmlid_for_target(doc_type: str, doc_id: str) -> str | None:
    """Devuelve `__holded__.<prefix>_<doc_id>` segun doc_type."""
    if doc_type == "invoice":
        return f"{EXT_MODULE}.invoice_{doc_id}"
    if doc_type == "creditnote":
        return f"{EXT_MODULE}.creditnote_{doc_id}"
    if doc_type == "purchase":
        return f"{EXT_MODULE}.purchase_{doc_id}"
    if doc_type == "purchaserefund":
        return f"{EXT_MODULE}.purchaserefund_{doc_id}"
    return None


def lookup_partners_by_holded_ids(client: Any, contact_ids: set[str]) -> dict[str, int]:
    """Reusa logica de _invoices_lib pero local para evitar import circular."""
    if not contact_ids:
        return {}
    names = [f"contact_{cid}" for cid in contact_ids]
    out: dict[str, int] = {}
    for i in range(0, len(names), 200):
        chunk = names[i:i+200]
        hits = client.call(
            "ir.model.data", "search_read",
            [[("module", "=", EXT_MODULE), ("name", "in", chunk),
              ("model", "=", "res.partner")]],
            {"fields": ["name", "res_id"]},
        )
        for h in hits:
            cid = h["name"].split("_", 1)[1]
            out[cid] = h["res_id"]
    return out


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def load_payments(
    client: Any,
    dump_dir: Path,
    *,
    dry_run: bool = False,
    limit: int | None = None,
    include_purchases: bool = False,
    report_dir: Path | None = None,
) -> PaymentStats:
    """Carga `payments.jsonl` -> `account.payment` filtrando documentType.

    Args:
        client: OdooClient con sesion activa.
        dump_dir: `holded-export/<YYYY-MM-DD>/`.
        dry_run: simula sin escribir.
        limit: procesa solo los primeros N docs.
        include_purchases: si True, incluye documentType=purchase (requiere
            loader 4 ejecutado previamente). Default False (MVP).

    Returns:
        PaymentStats.
    """
    input_path = dump_dir / "payments.jsonl"

    docs = list(iter_jsonl(input_path))
    if limit:
        docs = docs[:limit]
    stats = PaymentStats(total=len(docs))

    supported = SUPPORTED_DOC_TYPES_FULL if include_purchases else SUPPORTED_DOC_TYPES_MVP

    # Pre-fetch indices
    contact_ids: set[str] = set()
    target_xmlids: list[str] = []
    target_xmlid_by_doc_id: dict[str, str] = {}
    for d in docs:
        dt = d.get("documentType")
        if dt not in supported:
            continue
        if d.get("contactId"):
            contact_ids.add(d["contactId"])
        target_xmlid = _xmlid_for_target(dt, d.get("documentId") or "")
        if target_xmlid:
            target_xmlids.append(target_xmlid)
            target_xmlid_by_doc_id[d.get("documentId") or ""] = target_xmlid

    partner_by_holded = lookup_partners_by_holded_ids(client, contact_ids)

    # Lookup target moves
    move_by_xmlid: dict[str, int] = {}
    if target_xmlids:
        names_set = {x.split(".", 1)[1] for x in target_xmlids}
        names = list(names_set)
        for i in range(0, len(names), 200):
            chunk = names[i:i+200]
            hits = client.call(
                "ir.model.data", "search_read",
                [[("module", "=", EXT_MODULE), ("name", "in", chunk),
                  ("model", "=", "account.move")]],
                {"fields": ["name", "res_id"]},
            )
            for h in hits:
                move_by_xmlid[f"{EXT_MODULE}.{h['name']}"] = h["res_id"]

    upsert = None
    if not dry_run:
        try:
            from ext_id_upsert import upsert as _upsert
            upsert = _upsert
        except ImportError as exc:
            raise RuntimeError("ext_id_upsert no en PYTHONPATH.") from exc

    rows: list[dict[str, Any]] = []
    for doc in docs:
        row = _process_payment(
            client, doc,
            partner_by_holded=partner_by_holded,
            move_by_xmlid=move_by_xmlid,
            supported_doc_types=supported,
            stats=stats, dry_run=dry_run, upsert=upsert,
        )
        rows.append(row)

    _write_report(rows, dump_dir, dry_run, report_dir)
    return stats


def _process_payment(
    client: Any,
    doc: dict,
    *,
    partner_by_holded: dict[str, int],
    move_by_xmlid: dict[str, int],
    supported_doc_types: set[str],
    stats: PaymentStats,
    dry_run: bool,
    upsert: Any,
) -> dict:
    hid = doc.get("id") or ""
    xmlid = f"{EXT_MODULE}.payment_{hid}"
    dt = doc.get("documentType") or ""

    row: dict[str, Any] = {
        "holded_id": hid,
        "documentType": dt,
        "documentId": doc.get("documentId") or "",
        "contact": doc.get("contactName", "")[:30] if doc.get("contactName") else "",
        "amount": doc.get("amount"),
        "bankId": doc.get("bankId") or "",
        "date": iso_from_unix(doc.get("date")) or "",
        "xmlid": xmlid,
        "result": "",
        "res_id": "",
        "target_move_id": "",
        "error": "",
    }

    # Filtro doc_type
    if dt not in supported_doc_types:
        stats.skip_doc_type_unsupported += 1
        row["result"] = f"skip_doctype_{dt}"
        return row

    # contact obligatorio
    contact_id = doc.get("contactId")
    if not contact_id:
        stats.skip_no_contact += 1
        row["result"] = "skip_no_contact"
        return row
    partner_id = partner_by_holded.get(contact_id)
    if not partner_id:
        stats.skip_partner_unresolved += 1
        row["result"] = "skip_partner_unresolved"
        return row

    # bank obligatorio
    bank_id = doc.get("bankId")
    if not bank_id:
        stats.skip_no_bank += 1
        row["result"] = "skip_no_bank"
        return row
    journal_id = BANK_TO_JOURNAL.get(bank_id)
    if not journal_id:
        stats.skip_bank_unmapped += 1
        row["result"] = "skip_bank_unmapped"
        return row

    # target move (no obligatorio para crear pago, pero indica si esta
    # cargado el doc destino; si no esta, el pago queda huerfano hasta
    # que cargemos el move)
    target_xmlid = _xmlid_for_target(dt, doc.get("documentId") or "")
    target_move_id: int | None = None
    if target_xmlid:
        target_move_id = move_by_xmlid.get(target_xmlid)
        row["target_move_id"] = target_move_id or ""
    if not target_move_id:
        stats.skip_move_unresolved += 1
        row["result"] = "skip_move_unresolved"
        return row

    amount = float(doc.get("amount") or 0.0)
    if amount == 0:
        stats.skip_zero_amount += 1
        row["result"] = "skip_zero_amount"
        return row

    vals = build_payment_vals(
        doc, partner_id=partner_id, journal_id=journal_id,
        target_move_id=target_move_id,
    )

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

    try:
        existing = search_ext_id(client, xmlid)
        if existing:
            stats.skip_existing += 1
            row["result"] = "skip_existing"
            row["res_id"] = existing[0]
            return row
        res_id, _ = upsert(client, xmlid, "account.payment", vals, noupdate=True)
    except Exception as exc:
        row["result"] = "error"
        row["error"] = f"upsert: {exc}"
        stats.errors += 1
        stats.error_details.append((hid, row["error"]))
        return row

    stats.created += 1
    row["result"] = "created"
    row["res_id"] = res_id
    return row


def _write_report(rows, dump_dir, dry_run, report_dir):
    if report_dir is None:
        report_dir = dump_dir / ".etl_reports"
    report_dir.mkdir(exist_ok=True)
    mode_tag = "dryrun" if dry_run else "run"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = report_dir / f"payments_{mode_tag}_{ts}.csv"
    if not rows:
        return
    fields_order = [
        "holded_id", "documentType", "documentId", "contact", "amount",
        "bankId", "date", "target_move_id", "xmlid", "result", "res_id", "error",
    ]
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields_order, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"report: {out}", file=sys.stderr)


def print_summary(stats: PaymentStats, dry_run: bool) -> None:
    mode = "DRY-RUN" if dry_run else "REAL"
    print(f"\n[payments {mode}]")
    print(f"  total docs:                    {stats.total}")
    if dry_run:
        print(f"  would_create:                  {stats.would_create}")
        print(f"  would_update:                  {stats.would_update}")
    else:
        print(f"  created:                       {stats.created}")
        print(f"  skip_existing:                 {stats.skip_existing}")
    print(f"  skip_doctype_unsupported:      {stats.skip_doc_type_unsupported}")
    print(f"  skip_no_contact:               {stats.skip_no_contact}")
    print(f"  skip_no_bank:                  {stats.skip_no_bank}")
    print(f"  skip_bank_unmapped:            {stats.skip_bank_unmapped}")
    print(f"  skip_partner_unresolved:       {stats.skip_partner_unresolved}")
    print(f"  skip_move_unresolved:          {stats.skip_move_unresolved}")
    print(f"  skip_zero_amount:              {stats.skip_zero_amount}")
    print(f"  errors:                        {stats.errors}")
    if stats.error_details:
        print("  primeros 10 errores:")
        for hid, reason in stats.error_details[:10]:
            print(f"    - {hid}: {reason}")
