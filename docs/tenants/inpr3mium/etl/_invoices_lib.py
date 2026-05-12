"""Helpers puros + orquestacion para `loader_invoices.py` (paso 3 del ETL).

Carga `documents/invoice.jsonl` (3.430 docs Holded) -> `account.move` con
`move_type='out_invoice'`. Ext_id `__holded__.invoice_<id>`. Cada linea
del doc Holded mapea a una linea de `account.move.line`.

Funciones puras (testables offline, sin red):
- `should_skip_doc`: decide skip + razon. Cubre R- (sin journal),
  status=2 (cancelado logico), contact vacio.
- `extract_item_tax_key`: extrae taxes[0] o None.
- `build_invoice_header_vals`: vals para `account.move.create()` sin
  invoice_line_ids.
- `build_invoice_line_vals`: dict para un `(0, 0, vals)` de
  invoice_line_ids.

`load_invoices` orquesta:
- Pre-fetch indices: saleschannels by id, partners by Holded id (via
  ir.model.data), products by Holded id, taxes (via resolvers cache).
- Por doc:
  - Skip si should_skip_doc.
  - Resolve partner, journal.
  - Build header + line_ids.
  - Upsert ext_id `__holded__.invoice_<doc.id>`.
  - Si `--post` y status==1: action_post(); abort si decimal mismatch >0.02.
- Report CSV + stats.

Decisiones (ver `migration-from-holded.md` -> Documentos / Invoices, y
dump-analysis):

- **`item.account` es un `salesChannelId` Holded**, no una cuenta
  contable directa. 85 ids unicos usados en items vs 38 en
  `saleschannels.jsonl` -> 47 huerfanos (sales channels borrados).
  Cuando huerfano: dejar `account_id=False` en la line; Odoo
  autocompleta con el del product, o cae al default empresa.
- **`item.tax` es numerico (21, 10, ...)**: se descarta. Usar
  `taxes[0]` (key del catalogo Holded). 0 multi-tax en este dump,
  asi que >1 elemento aborta el doc entero (defensivo).
- **165 items sin tax**: cargar la line sin `tax_ids`. Odoo aplica
  el default del product/empresa.
- **7.102 items con `units < 0`**: descuentos / abonos parciales.
  Mapeo verbatim: `quantity = item.units` (Odoo 19 acepta qty
  negativa en out_invoice; produce subtotal negativo).
- **`productId` ausente (11.5% items)**: line sin `product_id`,
  solo con `name = item.desc` + `account_id` + `tax_ids`. Odoo lo
  permite.
- **Status del doc**:
  - 0 (draft): crear pero NO postear.
  - 1 (posted en Holded): crear + postear si `--post`.
  - 2 (cancelado logico): skip + report.
- **Prefijos**: A-/L-/AC-/KD-/AF-/FVU- mapean a journal Odoo (Fase
  4.3 creo los journals con esos codes). **R- (6 docs)**: sin journal
  mapeado -> skip + report; el operador decide tras la carga si
  recrearlos manualmente.
- **Date / accountingDate**: `invoice_date = iso_from_unix(date)`;
  `date` (fecha contable) = `iso_from_unix(accountingDate or date)`.
  105/3.430 tienen accountingDate distinto a date (5.5%).
- **Idempotencia upsert**:
  - No existe: create + opcionalmente post.
  - Existe + draft: write (incluye invoice_line_ids con (5,0,0) +
    re-create).
  - Existe + posted: skip + status='exists_posted'. Para re-cargar,
    el operador hace `button_draft` manualmente.
- **`ref = docNumber`**: preserva el numero Holded para auditoria
  AEAT. Tras pre-loading de secuencias (Fase 5.5), `name == ref`.
- **Decimal mismatch IVA**: si `|doc.tax - move.amount_tax| > 0.02€`
  tras action_post(), registra warning pero no aborta. Si > 1€ aborta
  el batch entero — sintoma de bug serio.
"""
from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from holded_resolvers import EXT_MODULE, HoldedResolvers, iso_from_unix


# Status Holded -> accion Odoo
STATUS_DRAFT = 0
STATUS_POSTED = 1
STATUS_CANCELLED = 2

# Prefijos docNumber que se mapean a journals out_invoice.
# Validado contra Fase 4.3 (journals creados):
# A- (id=7), AC- (id=13), AF-, KD-, FVU-, L-, PB- (id=8) [purchase], PI-
SALES_PREFIXES: set[str] = {"A-", "AC-", "AF-", "KD-", "FVU-", "L-"}


# Journal ACC- para conversiones automaticas: out_invoice/out_refund con
# total<0 en Holded -> Odoo lo prohibe (Odoo 19), reasignar move_type
# opuesto, journal=ACC-, name=False (sequence Odoo asignara ACC-NNNNNN).
# Politica operador 2026-05-12: serie aislada para que estos docs
# convertidos sean trivialmente filtrables (`journal_id=ACC-`). Decision
# tomada tras encontrar 776 docs problematicos (705 AC- + 41 A- + 3 L-
# + 1 FVU- en invoice.jsonl y 26 en creditnote.jsonl).
ACC_JOURNAL_CODE = "ACC-"


@dataclass
class InvoiceStats:
    total: int = 0
    created: int = 0
    updated: int = 0          # draft existing -> rewrite vals
    would_create: int = 0
    would_update: int = 0
    posted: int = 0
    post_failed: int = 0
    skip_cancelled: int = 0   # status=2
    skip_unmapped_prefix: int = 0  # R- o similar
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
    decimal_mismatch_warnings: int = 0
    duplicate_docnumber_name_dropped: int = 0  # docs con docNumber dup donde name='/'
    converted_negative_to_refund: int = 0  # total<0 → reasignado a out_refund + journal ACC-
    errors: int = 0
    error_details: list[tuple[str, str]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def parse_doc_prefix(doc_number: Any) -> str | None:
    """Devuelve el prefijo `XX-` de `XX-NNNN`, o None si no hay guion.

    Reusa logica de `holded_resolvers.parse_journal_prefix` pero acepta
    forma corta para tests aqui sin importar la otra.
    """
    if not doc_number:
        return None
    s = str(doc_number).strip().upper()
    if "-" not in s:
        return None
    return s.split("-", 1)[0] + "-"


def should_skip_doc(doc: dict) -> tuple[bool, str]:
    """Decide si un doc invoice se salta. Devuelve (skip, reason).

    Reasons:
    - 'cancelled': status=2 (cancelado logico en Holded).
    - 'no_contact': sin partner Holded.
    - 'unmapped_prefix': docNumber con prefijo no mapeable a journal
      out_invoice (R-, sin guion, etc.).
    """
    if doc.get("status") == STATUS_CANCELLED:
        return (True, "cancelled")
    if not doc.get("contact"):
        return (True, "no_contact")
    prefix = parse_doc_prefix(doc.get("docNumber"))
    if not prefix or prefix not in SALES_PREFIXES:
        return (True, "unmapped_prefix")
    return (False, "")


def extract_item_tax_key(item: dict) -> tuple[str | None, int]:
    """Devuelve `(tax_key, n_keys)` del array `item.taxes`."""
    taxes = item.get("taxes") or []
    if not taxes:
        return (None, 0)
    if len(taxes) > 1:
        return (None, len(taxes))
    return (str(taxes[0]).strip(), 1)


def build_invoice_header_vals(
    doc: dict,
    *,
    partner_id: int,
    journal_id: int,
    company_id: int | None = None,
    use_holded_number: bool = True,
    duplicate_alt_id: str | None = None,
    converted_to_refund: bool = False,
) -> dict:
    """Mapea un doc Holded invoice a vals de `account.move` (sin line_ids).

    Args:
        doc: dict del JSONL.
        partner_id: `res.partner.id` resuelto.
        journal_id: `account.journal.id` resuelto.
        company_id: company explicito (multi-company); None usa default.
        use_holded_number: si True (default), setea `name = doc.docNumber`
            literal — preserva la correlatividad AEAT con Holded. Politica
            establecida por operador inpr3mium 2026-05-12: "Todo aquello
            que se importa no puede modificarse el numero de factura.
            Seguiremos una estrategia de subida una vez se cierre un
            trimestre". Si False, `name` queda sin setear y Odoo lo asignara
            desde sequence al action_post (modo legacy / facturas post-cutover).
        duplicate_alt_id: si el caller detecto duplicado en docNumber para
            este doc, pasa aqui el holded_id del doc "ganador" del par. NO
            se setea `name`; en su lugar se anyade nota en narration. Se
            preserva el dato pero sin romper constraint unique(name, journal).

    Notes:
        - `ref` = docNumber Holded SIEMPRE (auditoria, incluso si name='/').
        - `invoice_date` = doc.date; `date` (contable) = accountingDate
          si presente, si no = doc.date.
        - `narration` = doc.notes (las notas que el operador ponia en
          Holded en la factura) + warning si duplicado.
    """
    invoice_date = iso_from_unix(doc.get("date"))
    accounting_date = iso_from_unix(doc.get("accountingDate")) or invoice_date
    due_date = iso_from_unix(doc.get("dueDate"))
    docnum = doc.get("docNumber") or ""

    # Determinar move_type final: out_invoice por defecto, out_refund si
    # converted_to_refund=True (total<0 reasignado al journal ACC-).
    final_move_type = "out_refund" if converted_to_refund else "out_invoice"

    vals: dict[str, Any] = {
        "move_type": final_move_type,
        "partner_id": partner_id,
        "journal_id": journal_id,
        "ref": docnum,
    }
    # `name` literal solo si NO es conversion: para conversiones queremos
    # que Odoo asigne sequence ACC-NNNNNN al postear (aislamiento operativo
    # propuesta por operador 2026-05-12).
    if use_holded_number and docnum and not duplicate_alt_id and not converted_to_refund:
        # Preserva nombre Holded literal. Odoo respeta `name` explicito en
        # account.move; al action_post() NO lo sobrescribe desde sequence.
        vals["name"] = docnum
    if invoice_date:
        vals["invoice_date"] = invoice_date
    if accounting_date:
        vals["date"] = accounting_date
    if due_date:
        vals["invoice_date_due"] = due_date
    notes = (doc.get("notes") or "").strip()
    desc = (doc.get("desc") or "").strip()
    narration_parts = [p for p in (desc, notes) if p and p != docnum]
    if duplicate_alt_id:
        narration_parts.append(
            f"<strong>WARN duplicado Holded</strong>: docNumber <code>{docnum}</code> "
            f"compartido con otra factura del dump (id Holded: {duplicate_alt_id}). "
            f"Esta queda con name='/' (Odoo asignara sequence al postear) para no "
            f"violar unique(name, journal_id). Ref preserva el docNumber original. "
            f"Decision tomada en loader 3 (2026-05-12, ver runbook-migration-holded.md)."
        )
    if converted_to_refund:
        narration_parts.append(
            f"<strong>CONVERTIDO out_invoice -> out_refund</strong>: el doc Holded "
            f"<code>{docnum}</code> tenia total&lt;0 (rectificativa de abono) pero "
            f"estaba almacenado en invoice.jsonl. Reasignado a journal ACC- "
            f"(Conversiones carga histórica). Buscable por ref=<code>{docnum}</code>. "
            f"Decision operador 2026-05-12, ver runbook-migration-holded.md."
        )
    if narration_parts:
        vals["narration"] = "<br/>".join(narration_parts)
    if company_id:
        vals["company_id"] = company_id
    return vals


def build_invoice_line_vals(
    item: dict,
    *,
    product_id: int | None,
    account_id: int | None,
    tax_id: int | None,
) -> dict:
    """Mapea un item Holded a vals para `account.move.line` (campo invoice_line_ids).

    Args:
        item: dict del array `doc.products[i]`.
        product_id: `product.template.id` o None si Holded line sin productId.
            NB: en account.move.line se espera `product.product` (`product_id`
            apunta a variant); pero `product.template` tiene normalmente UNA
            variant. El orquestador pasa el primer `product_variant_id` del
            template; si no hay product_id en Holded, queda False.
        account_id: `account.account.id` resuelto. False -> Odoo autocompleta
            del product o cae al default.
        tax_id: `account.tax.id` para `tax_ids`. None -> sin tax (cae al
            default product/empresa).

    Notes:
        - `quantity = item.units` (Odoo 19 acepta negativos en out_invoice).
        - `price_unit = item.price`.
        - `discount = item.discount` (en Holded suele ser %, convertir si fuera €).
        - `name` = item.desc (mas descriptivo que item.name que es el header
          repetido).
    """
    name = (item.get("desc") or "").strip() or (item.get("name") or "").strip() or "/"
    units = item.get("units")
    price = item.get("price")
    discount = item.get("discount") or 0.0
    vals: dict[str, Any] = {
        "name": name,
        "quantity": float(units) if units is not None else 1.0,
        "price_unit": float(price) if price is not None else 0.0,
        "discount": float(discount) if discount else 0.0,
    }
    if product_id:
        vals["product_id"] = product_id
    if account_id:
        vals["account_id"] = account_id
    if tax_id:
        vals["tax_ids"] = [(6, 0, [tax_id])]
    else:
        # Anular el default del product/empresa: si tax_id es None pero el
        # item.taxes estaba vacio (intencional en Holded), no queremos que
        # Odoo meta el 21% por defecto. Para preservar el behavior de
        # Holded: tax_ids = []. Esto solo aplica si la line tenia taxes
        # explicitamente vacios en el dump (165 items).
        vals["tax_ids"] = [(6, 0, [])]
    return vals


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def iter_jsonl(path: Path) -> Iterator[dict]:
    if not path.exists():
        return
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def search_ext_id(client: Any, xmlid: str) -> tuple[int, str] | None:
    """Devuelve `(res_id, model)` o None."""
    module, name = xmlid.split(".", 1)
    hits = client.call(
        "ir.model.data",
        "search_read",
        [[("module", "=", module), ("name", "=", name)]],
        {"fields": ["res_id", "model"], "limit": 1},
    )
    if not hits:
        return None
    return (hits[0]["res_id"], hits[0]["model"])


def build_index_by_id(records: Iterator[dict]) -> dict[str, str]:
    """`{holded_id: accountNum}` desde saleschannels.jsonl."""
    out: dict[str, str] = {}
    for r in records:
        rid = r.get("id")
        acc = r.get("accountNum")
        if rid and acc:
            out[rid] = str(acc).strip()
    return out


def lookup_partners_by_holded_ids(client: Any, contact_ids: set[str]) -> dict[str, int]:
    """Batch lookup de `ir.model.data` `__holded__.contact_<id>` -> res.partner.id.

    Devuelve `{holded_contact_id: res_partner_id}`. Contact ids no
    encontrados quedan ausentes; el caller usa el placeholder unknown.
    """
    if not contact_ids:
        return {}
    names = [f"contact_{cid}" for cid in contact_ids]
    out: dict[str, int] = {}
    # Batch en chunks de 200 para evitar dominios infinitos
    for i in range(0, len(names), 200):
        chunk = names[i:i+200]
        hits = client.call(
            "ir.model.data",
            "search_read",
            [[("module", "=", EXT_MODULE), ("name", "in", chunk)]],
            {"fields": ["name", "res_id"]},
        )
        for h in hits:
            cid = h["name"].split("_", 1)[1]
            out[cid] = h["res_id"]
    return out


def lookup_product_template_to_variant(client: Any, template_ids: set[int]) -> dict[int, int]:
    """`{product.template.id: product.product.id}` para la variante por defecto.

    `account.move.line.product_id` apunta a `product.product`, no a
    `product.template`. Cada template tiene al menos una variant (en
    inpr3mium 2.009 templates plano sin variants -> 1:1).
    """
    if not template_ids:
        return {}
    out: dict[int, int] = {}
    for i in range(0, len(template_ids), 200):
        chunk = list(template_ids)[i:i+200]
        hits = client.call(
            "product.template",
            "read",
            [chunk, ["product_variant_id"]],
        )
        for h in hits:
            v = h.get("product_variant_id")
            if v:
                out[h["id"]] = v[0] if isinstance(v, list) else v
    return out


def lookup_journals_by_code(client: Any, codes: set[str]) -> dict[str, int]:
    if not codes:
        return {}
    hits = client.call(
        "account.journal",
        "search_read",
        [[("code", "in", sorted(codes))]],
        {"fields": ["code", "id"]},
    )
    return {h["code"]: h["id"] for h in hits}


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def load_invoices(
    client: Any,
    resolvers: HoldedResolvers,
    dump_dir: Path,
    *,
    dry_run: bool = False,
    limit: int | None = None,
    post: bool = False,
    report_dir: Path | None = None,
) -> InvoiceStats:
    """Carga `documents/invoice.jsonl` -> account.move out_invoice.

    Args:
        client: OdooClient con sesion activa.
        resolvers: HoldedResolvers para tax/account (partner via lookup
            directo en este loader; journal idem).
        dump_dir: `holded-export/<YYYY-MM-DD>/`.
        dry_run: si True, no escribe en Odoo; solo simula y reporta.
        limit: procesa solo los primeros N docs.
        post: si True, llama action_post() tras crear cada move con
            status=1 en Holded.
        report_dir: directorio CSV; default `dump_dir/.etl_reports/`.

    Returns:
        InvoiceStats.
    """
    input_path = dump_dir / "documents" / "invoice.jsonl"

    # Lazy import: solo modo real.
    upsert = None
    if not dry_run:
        try:
            from ext_id_upsert import upsert as _upsert
            upsert = _upsert
        except ImportError as exc:
            raise RuntimeError(
                "ext_id_upsert no en PYTHONPATH. Anade "
                "`.claude/skills/odoo-functional-admin/scripts` al PYTHONPATH."
            ) from exc

    # Cargar dump completo a memoria
    docs = list(iter_jsonl(input_path))
    if limit:
        docs = docs[:limit]

    stats = InvoiceStats(total=len(docs))

    # Detectar duplicados de docNumber: 2 pares L-000719 / L-000720 confirmados
    # en dump inpr3mium 2026-05-11. Estrategia: el doc con date MAS RECIENTE
    # mantiene name=docNumber; los demas del par quedan con name='/' + nota
    # narration. Constraint Odoo: unique(name, journal_id, company_id).
    docs_by_num: dict[str, list[dict]] = {}
    for d in docs:
        dn = d.get("docNumber")
        if dn:
            docs_by_num.setdefault(dn, []).append(d)
    # Set de holded_ids que NO deben recibir name (loosers del par)
    duplicate_losers: dict[str, str] = {}  # holded_id_loser -> holded_id_winner
    for dn, group in docs_by_num.items():
        if len(group) <= 1:
            continue
        # Winner: el de date mas reciente. Si empate, el primero del JSONL.
        ranked = sorted(group, key=lambda x: float(x.get("date") or 0), reverse=True)
        winner = ranked[0]
        for loser in ranked[1:]:
            duplicate_losers[loser["id"]] = winner["id"]

    # Pre-fetch indices
    saleschannels_idx = build_index_by_id(iter_jsonl(dump_dir / "saleschannels.jsonl"))

    # Journal ACC- (Conversiones carga historica) — para docs con total<0.
    acc_journal_id: int | None = None
    hits = client.call("account.journal", "search_read",
                       [[("code", "=", ACC_JOURNAL_CODE)]],
                       {"fields": ["id"], "limit": 1})
    if hits:
        acc_journal_id = hits[0]["id"]

    # Set de contacts y product templates (Holded ids) usados
    contact_ids: set[str] = set()
    product_holded_ids: set[str] = set()
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

    # Lookup batch: partners, journals, products
    partner_by_holded = lookup_partners_by_holded_ids(client, contact_ids) if not dry_run or True else {}
    # NOTE: incluso en dry-run hacemos lookup para reportar correctamente
    # (no escribe, solo read).
    journal_by_code = lookup_journals_by_code(client, journal_prefixes)

    # Lookup templates by Holded id via ir.model.data
    template_by_holded: dict[str, int] = {}
    if product_holded_ids:
        names = [f"product_{pid}" for pid in product_holded_ids] + \
                [f"service_{pid}" for pid in product_holded_ids]
        for i in range(0, len(names), 200):
            chunk = names[i:i+200]
            hits = client.call(
                "ir.model.data",
                "search_read",
                [[
                    ("module", "=", EXT_MODULE),
                    ("name", "in", chunk),
                    ("model", "=", "product.template"),
                ]],
                {"fields": ["name", "res_id"]},
            )
            for h in hits:
                # name = product_<id> o service_<id>
                _, pid = h["name"].split("_", 1)
                template_by_holded[pid] = h["res_id"]

    variant_by_template = lookup_product_template_to_variant(
        client, set(template_by_holded.values())
    )

    # Placeholder partner unknown (creado en loader 1)
    unknown_partner_id = None
    unk = search_ext_id(client, f"{EXT_MODULE}.contact__unknown")
    if unk:
        unknown_partner_id, _ = unk

    # Default income account (705000): fallback para lineas sin product_id
    # ni saleschannel resoluble. Sin este fallback, Odoo aborta el move con
    # "Missing required account on accountable line" (12/3430 docs en el dump
    # inpr3mium 2026-05-11). Set en Fase 5.0 como `income_account_id` de la
    # company. Hardcodeamos el code (no el id) para tolerar cambios.
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
            unknown_partner_id=unknown_partner_id,
            default_income_id=default_income_id,
            duplicate_losers=duplicate_losers,
            acc_journal_id=acc_journal_id,
            stats=stats,
            dry_run=dry_run,
            post=post,
            upsert=upsert,
        )
        rows.append(row)

    _write_report(rows, dump_dir, dry_run, report_dir)
    return stats


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
    unknown_partner_id: int | None,
    default_income_id: int | None,
    duplicate_losers: dict[str, str],
    acc_journal_id: int | None,
    stats: InvoiceStats,
    dry_run: bool,
    post: bool,
    upsert: Any,
) -> dict:
    hid = doc.get("id") or ""
    xmlid = f"{EXT_MODULE}.invoice_{hid}"
    docnum = doc.get("docNumber") or ""

    row: dict[str, Any] = {
        "holded_id": hid,
        "docNumber": docnum,
        "contact": doc.get("contact") or "",
        "date": iso_from_unix(doc.get("date")) or "",
        "status": doc.get("status"),
        "n_items": len(doc.get("products") or []),
        "total_holded": doc.get("total"),
        "xmlid": xmlid,
        "result": "",
        "res_id": "",
        "error": "",
    }

    skip, reason = should_skip_doc(doc)
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

    # Resolve partner
    contact_id = doc["contact"]
    partner_id = partner_by_holded.get(contact_id)
    if not partner_id and unknown_partner_id:
        partner_id = unknown_partner_id
        row["result"] = "partner_to_unknown"
    if not partner_id:
        stats.partner_unresolved += 1
        row["result"] = "error"
        row["error"] = f"partner {contact_id} sin ext_id y sin unknown placeholder"
        stats.errors += 1
        stats.error_details.append((hid, row["error"]))
        return row

    # Resolve journal
    prefix = parse_doc_prefix(docnum)
    journal_id = journal_by_code.get(prefix) if prefix else None
    if not journal_id:
        stats.journal_unresolved += 1
        row["result"] = "error"
        row["error"] = f"journal con code {prefix!r} no existe en Odoo"
        stats.errors += 1
        stats.error_details.append((hid, row["error"]))
        return row

    # Conversion: si total<0 reasignar journal_id=ACC- y move_type=out_refund.
    # Flipea signos en lineas para que subtotales queden positivos.
    convert_to_refund = False
    total_holded = float(doc.get("total") or 0.0)
    if total_holded < 0 and acc_journal_id:
        convert_to_refund = True
        journal_id = acc_journal_id
        stats.converted_negative_to_refund += 1

    # Build line_ids
    items = doc.get("products") or []
    stats.items_total += len(items)
    line_ids: list[tuple] = []
    has_line_error = False
    for it in items:
        line_vals = _build_line(
            it, resolvers,
            saleschannels_idx=saleschannels_idx,
            template_by_holded=template_by_holded,
            variant_by_template=variant_by_template,
            default_income_id=default_income_id,
            flip_signs=convert_to_refund,
            stats=stats,
        )
        if line_vals is None:
            has_line_error = True
            break
        line_ids.append((0, 0, line_vals))

    if has_line_error:
        stats.errors += 1
        row["result"] = "error"
        row["error"] = "line aborta el doc (ver stats.tax_unresolved_lines / multi_tax_lines)"
        stats.error_details.append((hid, row["error"]))
        return row

    dup_winner = duplicate_losers.get(hid)
    if dup_winner:
        stats.duplicate_docnumber_name_dropped += 1
    header = build_invoice_header_vals(
        doc, partner_id=partner_id, journal_id=journal_id,
        duplicate_alt_id=dup_winner,
        converted_to_refund=convert_to_refund,
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

    # Real: existencia / estado actual
    existing = search_ext_id(client, xmlid)
    if existing:
        res_id, model = existing
        if model != "account.move":
            row["result"] = "error"
            row["error"] = f"ext_id apunta a {model}, no a account.move"
            stats.errors += 1
            stats.error_details.append((hid, row["error"]))
            return row
        # Leer estado actual del move
        state_data = client.call("account.move", "read", [[res_id], ["state"]])
        if state_data and state_data[0]["state"] != "draft":
            row["result"] = "skip_existing_posted"
            row["res_id"] = res_id
            stats.skip_existing_posted += 1
            return row
        # Existing draft -> rewrite invoice_line_ids
        # (5, 0, 0) borra todas, luego (0, 0, ...) recrea.
        write_vals = dict(header)
        write_vals["invoice_line_ids"] = [(5, 0, 0)] + line_ids
        try:
            client.call("account.move", "write", [[res_id], write_vals])
        except Exception as exc:
            row["result"] = "error"
            row["error"] = f"write existing draft: {exc}"
            stats.errors += 1
            stats.error_details.append((hid, row["error"]))
            return row
        stats.updated += 1
        row["result"] = "updated_draft"
        row["res_id"] = res_id
    else:
        # No existe -> create + link ext_id
        try:
            res_id, action = upsert(client, xmlid, "account.move", header, noupdate=True)
        except Exception as exc:
            row["result"] = "error"
            row["error"] = f"upsert: {exc}"
            stats.errors += 1
            stats.error_details.append((hid, row["error"]))
            return row
        stats.created += 1
        row["result"] = "created"
        row["res_id"] = res_id

    # Post si aplica
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
        # Decimal check
        amts = client.call("account.move", "read", [[row["res_id"]], ["amount_tax", "amount_total"]])
        if amts:
            ax = amts[0].get("amount_tax") or 0.0
            tot = amts[0].get("amount_total") or 0.0
            holded_tax = float(doc.get("tax") or 0.0)
            holded_tot = float(doc.get("total") or 0.0)
            if abs(ax - holded_tax) > 0.02 or abs(tot - holded_tot) > 0.02:
                stats.decimal_mismatch_warnings += 1
                row["error"] = (
                    f"decimal mismatch: holded tax={holded_tax} tot={holded_tot} | "
                    f"odoo tax={ax} tot={tot}"
                )

    return row


def _build_line(
    item: dict,
    resolvers: HoldedResolvers,
    *,
    saleschannels_idx: dict[str, str],
    template_by_holded: dict[str, int],
    variant_by_template: dict[int, int],
    default_income_id: int | None,
    stats: InvoiceStats,
    flip_signs: bool = False,
) -> dict | None:
    """Devuelve vals de line, o None si la line aborta el doc.

    Args:
        flip_signs: si True, multiplica `quantity` por -1 para invertir el
            signo del subtotal. Usado en conversion total<0 -> out_refund
            (Holded almacenaba lines con units negativas; out_refund Odoo
            espera quantity positiva).
    """
    # Tax
    tax_key, n_keys = extract_item_tax_key(item)
    tax_id: int | None = None
    if n_keys > 1:
        stats.multi_tax_lines += 1
        return None
    if n_keys == 1:
        tid = resolvers.resolve_tax(tax_key, {"doc_type": "sale"})
        if tid > 0:
            tax_id = tid
        else:
            stats.tax_unresolved_lines += 1
            return None
    # 0 keys -> tax_id None (linea sin IVA explicito, 165 items en el dump)

    # Account: via saleschannel
    account_id: int | None = None
    sc_id = item.get("account")
    if not sc_id:
        stats.items_no_account += 1
    else:
        acc_num = saleschannels_idx.get(sc_id)
        if not acc_num:
            stats.items_orphan_channel += 1
        else:
            aid = resolvers.resolve_account(acc_num, autocreate=False)
            if aid > 0:
                account_id = aid
            else:
                stats.items_orphan_channel += 1

    # Product (template -> variant)
    product_id: int | None = None
    pid_h = item.get("productId")
    if pid_h:
        tpl_id = template_by_holded.get(pid_h)
        if tpl_id:
            product_id = variant_by_template.get(tpl_id)
    else:
        stats.items_no_product += 1

    # Fallback: si ni product ni account resoluble, usar default income empresa.
    # Sin esto Odoo aborta con "Missing required account on accountable line"
    # (12/3430 docs en dump inpr3mium 2026-05-11 — items sin productId con
    # saleschannel huerfano).
    if account_id is None and product_id is None and default_income_id:
        account_id = default_income_id

    if flip_signs:
        # Flip quantity solo, mantener price_unit. Subtotal final = qty * price
        # negativo en Holded; out_refund Odoo lo quiere positivo.
        item = dict(item)
        item["units"] = -float(item.get("units") or 0.0)

    return build_invoice_line_vals(
        item,
        product_id=product_id,
        account_id=account_id,
        tax_id=tax_id,
    )


def _write_report(
    rows: list[dict],
    dump_dir: Path,
    dry_run: bool,
    report_dir: Path | None,
) -> None:
    if report_dir is None:
        report_dir = dump_dir / ".etl_reports"
    report_dir.mkdir(exist_ok=True)
    mode_tag = "dryrun" if dry_run else "run"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = report_dir / f"invoices_{mode_tag}_{ts}.csv"
    if not rows:
        return
    fields_order = [
        "holded_id", "docNumber", "contact", "date", "status",
        "n_items", "total_holded", "xmlid", "result", "res_id", "error",
    ]
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields_order, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"report: {out}", file=sys.stderr)


def print_summary(stats: InvoiceStats, dry_run: bool, post: bool) -> None:
    mode = "DRY-RUN" if dry_run else ("REAL+POST" if post else "REAL")
    print(f"\n[invoices {mode}]")
    print(f"  total docs:                {stats.total}")
    if dry_run:
        print(f"  would_create:              {stats.would_create}")
        print(f"  would_update:              {stats.would_update}")
    else:
        print(f"  created:                   {stats.created}")
        print(f"  updated (draft existing):  {stats.updated}")
        if post:
            print(f"  posted:                    {stats.posted}")
            print(f"  post_failed:               {stats.post_failed}")
            print(f"  decimal_mismatch_warns:    {stats.decimal_mismatch_warnings}")
    print(f"  skip_cancelled (status=2):    {stats.skip_cancelled}")
    print(f"  skip_unmapped_prefix (R-, ..): {stats.skip_unmapped_prefix}")
    print(f"  skip_no_contact:               {stats.skip_no_contact}")
    print(f"  skip_existing_posted:          {stats.skip_existing_posted}")
    print(f"  partner_unresolved:            {stats.partner_unresolved}")
    print(f"  journal_unresolved:            {stats.journal_unresolved}")
    print(f"  items_total:                   {stats.items_total}")
    print(f"  items_no_product:              {stats.items_no_product}")
    print(f"  items_orphan_channel:          {stats.items_orphan_channel}")
    print(f"  items_no_account:              {stats.items_no_account}")
    print(f"  tax_unresolved_lines:          {stats.tax_unresolved_lines}")
    print(f"  multi_tax_lines:               {stats.multi_tax_lines}")
    print(f"  dup_docNumber_name_dropped:    {stats.duplicate_docnumber_name_dropped}")
    print(f"  errors:                        {stats.errors}")
    if stats.error_details:
        print("  primeros 10 errores:")
        for hid, reason in stats.error_details[:10]:
            print(f"    - {hid}: {reason}")
