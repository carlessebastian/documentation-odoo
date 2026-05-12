"""Helpers puros + orquestacion para `loader_products.py` (paso 2 del ETL).

Carga unificada de `products.jsonl` (1.569) + `services.jsonl` (440) a
`product.template` Odoo. Mismo loader: el dump Holded distingue product
vs service en archivos separados; en Odoo lo distingue `type` (`consu`
vs `service`) y los accounts properties (`expense` vs solo `income`).

Funciones puras (testables offline, sin red):
- `extract_tax_key`: extrae la unica key de `record.taxes` o None.
- `build_product_vals`: vals para `product.template.create()` (kind=product).
- `build_service_vals`: vals para `product.template.create()` (kind=service).
- `index_by_id`: helper para cargar saleschannels / expensesaccount como
  `{id: accountNum}` desde el dump.

`load_products_and_services` orquesta:
- Carga indices saleschannels + expensesaccount (mapeo accountNum).
- Inicializa `HoldedResolvers` con `tax_reclassification.yaml`.
- Por cada record: resuelve tax + income/expense account, build vals,
  upsert via ext_id `__holded__.product_<id>` / `__holded__.service_<id>`.
- Aborta el record con error claro si tax/account no resuelven.

Decisiones (ver `migration-from-holded.md` -> Productos, y dump-analysis):

- **Schema real != schema doc**: el dump usa `taxes` (array) no `tax`
  (single). Hoy 1.536/1.569 products tienen 1 sola key (s_iva_21);
  los 33 sin tax usan default product company. Si en el futuro Holded
  emite 2 keys (e.g., IVA + RE), abortamos record (no mergeamos).
- **No `purchaseTax` en el dump**: products Holded NO traen tax de
  compra. Si en Odoo necesitamos `supplier_taxes_id` para los items
  de compra, lo derivara `loader_purchases` desde `item.tax` (no del
  product). Aqui dejamos `supplier_taxes_id` vacio.
- **`categoryId` siempre vacio** en el dump (verificado: 0 categorias
  unicas). Skip mapeo a `product.category` -- todos van a la categoria
  default `All` (id=1).
- **Variants (`attributes`)**: 688 products tienen attributes pero NO
  los expandimos a `product.product` con `product.attribute.line`.
  Cargamos como product.template plano. Si el operador necesita
  variants funcionales se puede ampliar despues; los moves usaran
  `product.template` directamente (no requieren `product.product`).
- **`hasStock` / `stock`**: ignorado en este paso. Los saldos de stock
  se cargaran en Fase 5.4 via `stock.change.product.qty` si aplica.
  Aqui solo seteamos `type='consu'` para products fisicos.
- **Income/expense accounts**: derivados via `salesChannelId` ->
  `accountNum` -> `resolve_account` (income, services y products
  marcados forSale=1) y `expAccountId` -> `accountNum` ->
  `resolve_account` (expense, solo products con expAccountId; 102/1569
  productos). Escritos directamente en el create. Odoo 19 maneja
  `company_dependent` per-record en `company_dependent_attribute`.
- **SKU collisions**: Holded `sku` mapea a `default_code` en Odoo. Si
  hay duplicados los reportamos pero NO abortamos -- Odoo permite
  default_code duplicado (no es unique). Los logueamos en CSV.
"""
from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from holded_resolvers import EXT_MODULE, HoldedResolvers


@dataclass
class ProductStats:
    total_products: int = 0
    total_services: int = 0
    product_create: int = 0
    product_update: int = 0
    service_create: int = 0
    service_update: int = 0
    would_create: int = 0
    would_update: int = 0
    no_tax: int = 0                     # records sin tax key
    tax_unresolved: int = 0             # tax key no resuelto en Odoo
    multi_tax: int = 0                  # records con > 1 tax key (no soportado)
    no_income_account: int = 0          # salesChannelId vacio o no mapeable
    no_expense_account: int = 0         # expAccountId presente pero no mapeable
    sku_collision: int = 0
    errors: int = 0
    error_details: list[tuple[str, str]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def extract_tax_key(record: dict) -> tuple[str | None, int]:
    """Devuelve `(tax_key, n_keys)` desde `record.taxes`.

    - n_keys=0 -> (None, 0): record sin tax (33 products del dump).
    - n_keys=1 -> (key, 1): caso normal.
    - n_keys>1 -> (None, n): caso no soportado, caller debe abortar el record.
    """
    taxes = record.get("taxes") or []
    if not taxes:
        return (None, 0)
    if len(taxes) > 1:
        return (None, len(taxes))
    return (str(taxes[0]).strip(), 1)


def index_by_id(records: Iterator[dict]) -> dict[str, str]:
    """Construye `{id: accountNum}` desde un JSONL de saleschannels/expensesaccount.

    `accountNum` viene como int en el dump -> stringificamos para coherencia
    con `resolve_account` (que aplica `str(...).strip()`).
    """
    out: dict[str, str] = {}
    for r in records:
        rid = r.get("id")
        acc = r.get("accountNum")
        if rid and acc:
            out[rid] = str(acc).strip()
    return out


def _common_vals(record: dict) -> dict:
    """Vals compartidos entre products y services."""
    vals: dict[str, Any] = {
        "name": (record.get("name") or "(sin nombre)").strip() or "(sin nombre)",
        "list_price": float(record.get("price") or 0.0),
        "standard_price": float(record.get("cost") or 0.0),
        "sale_ok": True,
        "purchase_ok": True,
    }
    desc = (record.get("desc") or "").strip()
    if desc and desc != vals["name"]:
        # `description` es la nota interna en product.template; `description_sale`
        # es la que se renderiza en las lineas de factura. Holded.desc se usa
        # ambas, asi que vamos a description_sale (mas util en facturas).
        vals["description_sale"] = desc
    return vals


def build_product_vals(
    record: dict,
    *,
    tax_id: int | None,
    income_account_id: int | None,
    expense_account_id: int | None,
) -> dict:
    """Mapea un record de `products.jsonl` a vals de `product.template`.

    Args:
        record: dict del JSONL.
        tax_id: `account.tax.id` para sale o None si no se pudo resolver
            (el caller puede decidir cargar sin tax si lo permite el flujo).
        income_account_id: `account.account.id` para
            `property_account_income_id` (derivado via salesChannelId).
        expense_account_id: para `property_account_expense_id` (derivado
            via expAccountId si presente; None si no).
    """
    vals = _common_vals(record)
    vals["type"] = "consu"           # producto fisico (no storable sin stock module)
    sku = (record.get("sku") or "").strip()
    if sku:
        vals["default_code"] = sku
    barcode = (record.get("barcode") or "").strip()
    if barcode:
        vals["barcode"] = barcode
    weight = record.get("weight")
    if weight:
        try:
            vals["weight"] = float(weight)
        except (TypeError, ValueError):
            pass
    # forSale / forPurchase override del default True
    if record.get("forSale") == 0:
        vals["sale_ok"] = False
    if record.get("forPurchase") == 0:
        vals["purchase_ok"] = False
    if tax_id:
        vals["taxes_id"] = [(6, 0, [tax_id])]
    if income_account_id:
        vals["property_account_income_id"] = income_account_id
    if expense_account_id:
        vals["property_account_expense_id"] = expense_account_id
    return vals


def build_service_vals(
    record: dict,
    *,
    tax_id: int | None,
    income_account_id: int | None,
) -> dict:
    """Mapea un record de `services.jsonl` a vals de `product.template`.

    Services no tienen sku/barcode/weight/forSale en el dump (verificado).
    Solo `name`, `desc`, `price`, `cost`, `taxes`, `salesChannelId`.
    """
    vals = _common_vals(record)
    vals["type"] = "service"
    if tax_id:
        vals["taxes_id"] = [(6, 0, [tax_id])]
    if income_account_id:
        vals["property_account_income_id"] = income_account_id
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


def search_ext_id(client: Any, xmlid: str) -> int | None:
    module, name = xmlid.split(".", 1)
    hits = client.call(
        "ir.model.data",
        "search_read",
        [[("module", "=", module), ("name", "=", name)]],
        {"fields": ["res_id"], "limit": 1},
    )
    return hits[0]["res_id"] if hits else None


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def load_products_and_services(
    client: Any,
    resolvers: HoldedResolvers,
    dump_dir: Path,
    *,
    dry_run: bool = False,
    limit: int | None = None,
    report_dir: Path | None = None,
) -> ProductStats:
    """Carga products.jsonl + services.jsonl -> product.template.

    Args:
        client: OdooClient con sesion activa.
        resolvers: HoldedResolvers ya construido (necesita tax_rules
            cargados si hay reclasificacion; para s_iva_* el lookup
            directo basta).
        dump_dir: ruta a `holded-export/<YYYY-MM-DD>/`.
        dry_run: si True, no escribe en Odoo; solo simula y reporta.
        limit: procesa solo los primeros N records de CADA archivo (debug).
        report_dir: directorio de CSV report; default `dump_dir/.etl_reports/`.

    Returns:
        ProductStats con conteos por kind y por estado de resolucion.
    """
    products_path = dump_dir / "products.jsonl"
    services_path = dump_dir / "services.jsonl"

    # Lazy import: solo modo real.
    upsert = None
    if not dry_run:
        try:
            from ext_id_upsert import upsert as _upsert
            upsert = _upsert
        except ImportError as exc:
            raise RuntimeError(
                "ext_id_upsert no en PYTHONPATH. Anade "
                "`.claude/skills/odoo-functional-admin/scripts` al "
                "PYTHONPATH antes de correr en modo real."
            ) from exc

    # Indices: saleschannels (income), expensesaccount (expense)
    saleschannels_idx = index_by_id(iter_jsonl(dump_dir / "saleschannels.jsonl"))
    expensesacct_idx = index_by_id(iter_jsonl(dump_dir / "expensesaccount.jsonl"))

    stats = ProductStats()
    rows: list[dict[str, Any]] = []
    seen_skus: dict[str, str] = {}  # sku -> first holded_id (deteccion colision)

    # Carga products
    products = list(iter_jsonl(products_path))
    if limit:
        products = products[:limit]
    stats.total_products = len(products)
    for r in products:
        row = _process_record(
            client, resolvers, r,
            kind="product",
            saleschannels_idx=saleschannels_idx,
            expensesacct_idx=expensesacct_idx,
            seen_skus=seen_skus,
            stats=stats,
            dry_run=dry_run,
            upsert=upsert,
        )
        rows.append(row)

    # Carga services
    services = list(iter_jsonl(services_path))
    if limit:
        services = services[:limit]
    stats.total_services = len(services)
    for r in services:
        row = _process_record(
            client, resolvers, r,
            kind="service",
            saleschannels_idx=saleschannels_idx,
            expensesacct_idx=expensesacct_idx,
            seen_skus=seen_skus,
            stats=stats,
            dry_run=dry_run,
            upsert=upsert,
        )
        rows.append(row)

    _write_report(rows, dump_dir, dry_run, report_dir)
    return stats


def _process_record(
    client: Any,
    resolvers: HoldedResolvers,
    record: dict,
    *,
    kind: str,
    saleschannels_idx: dict[str, str],
    expensesacct_idx: dict[str, str],
    seen_skus: dict[str, str],
    stats: ProductStats,
    dry_run: bool,
    upsert: Any,
) -> dict:
    """Procesa un product o service, emite upsert (o would_*), llena `row`."""
    hid = record.get("id") or ""
    xmlid = f"{EXT_MODULE}.{kind}_{hid}"

    row: dict[str, Any] = {
        "kind": kind,
        "holded_id": hid,
        "name": (record.get("name") or "")[:80],
        "sku": record.get("sku") or "",
        "tax_key": "",
        "tax_id": "",
        "income_account_id": "",
        "expense_account_id": "",
        "xmlid": xmlid,
        "status": "",
        "res_id": "",
        "error": "",
    }

    # 1. Tax
    tax_key, n_keys = extract_tax_key(record)
    row["tax_key"] = tax_key or ""
    tax_id: int | None = None
    if n_keys == 0:
        stats.no_tax += 1
    elif n_keys > 1:
        stats.multi_tax += 1
        row["status"] = "error"
        row["error"] = f"multi-tax keys: {record.get('taxes')!r}"
        stats.errors += 1
        stats.error_details.append((hid, row["error"]))
        return row
    else:
        tid = resolvers.resolve_tax(tax_key, {"doc_type": "sale"})
        if tid > 0:
            tax_id = tid
            row["tax_id"] = tid
        else:
            stats.tax_unresolved += 1
            row["status"] = "error"
            row["error"] = f"tax key no resoluble: {tax_key!r}"
            stats.errors += 1
            stats.error_details.append((hid, row["error"]))
            return row

    # 2. Income account (saleschannel)
    income_account_id: int | None = None
    sc_id = (record.get("salesChannelId") or "").strip()
    if sc_id:
        acc_num = saleschannels_idx.get(sc_id)
        if acc_num:
            aid = resolvers.resolve_account(acc_num, autocreate=False)
            if aid > 0:
                income_account_id = aid
                row["income_account_id"] = aid
            else:
                stats.no_income_account += 1
        else:
            stats.no_income_account += 1
    else:
        stats.no_income_account += 1

    # 3. Expense account (solo products con expAccountId)
    expense_account_id: int | None = None
    if kind == "product":
        exp_id = (record.get("expAccountId") or "").strip() if record.get("expAccountId") else ""
        if exp_id:
            acc_num = expensesacct_idx.get(exp_id)
            if acc_num:
                aid = resolvers.resolve_account(acc_num, autocreate=False)
                if aid > 0:
                    expense_account_id = aid
                    row["expense_account_id"] = aid
                else:
                    stats.no_expense_account += 1
            else:
                stats.no_expense_account += 1

    # 4. SKU collision tracking
    sku = (record.get("sku") or "").strip()
    if sku:
        if sku in seen_skus and seen_skus[sku] != hid:
            stats.sku_collision += 1
        else:
            seen_skus[sku] = hid

    # 5. Build vals + upsert
    if kind == "product":
        vals = build_product_vals(
            record,
            tax_id=tax_id,
            income_account_id=income_account_id,
            expense_account_id=expense_account_id,
        )
    else:
        vals = build_service_vals(
            record,
            tax_id=tax_id,
            income_account_id=income_account_id,
        )

    if dry_run:
        existing = search_ext_id(client, xmlid)
        if existing:
            row["status"] = "would_update"
            row["res_id"] = existing
            stats.would_update += 1
        else:
            row["status"] = "would_create"
            stats.would_create += 1
        return row

    try:
        res_id, action = upsert(client, xmlid, "product.template", vals, noupdate=True)
    except Exception as exc:
        row["status"] = "error"
        row["error"] = f"upsert: {exc}"
        stats.errors += 1
        stats.error_details.append((hid, row["error"]))
        return row

    row["res_id"] = res_id
    if action == "created":
        row["status"] = f"{kind}_create"
        if kind == "product":
            stats.product_create += 1
        else:
            stats.service_create += 1
    else:
        row["status"] = f"{kind}_update"
        if kind == "product":
            stats.product_update += 1
        else:
            stats.service_update += 1
    return row


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
    out = report_dir / f"products_{mode_tag}_{ts}.csv"
    if not rows:
        return
    fields_order = [
        "kind",
        "holded_id",
        "name",
        "sku",
        "tax_key",
        "tax_id",
        "income_account_id",
        "expense_account_id",
        "xmlid",
        "status",
        "res_id",
        "error",
    ]
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields_order, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"report: {out}", file=sys.stderr)


def print_summary(stats: ProductStats, dry_run: bool) -> None:
    mode = "DRY-RUN" if dry_run else "REAL"
    print(f"\n[products+services {mode}]")
    print(f"  total products:   {stats.total_products}")
    print(f"  total services:   {stats.total_services}")
    if dry_run:
        print(f"  would_create:     {stats.would_create}")
        print(f"  would_update:     {stats.would_update}")
    else:
        print(f"  product_create:   {stats.product_create}")
        print(f"  product_update:   {stats.product_update}")
        print(f"  service_create:   {stats.service_create}")
        print(f"  service_update:   {stats.service_update}")
    print(f"  no_tax:           {stats.no_tax}")
    print(f"  tax_unresolved:   {stats.tax_unresolved}")
    print(f"  multi_tax:        {stats.multi_tax}")
    print(f"  no_income_acct:   {stats.no_income_account}")
    print(f"  no_expense_acct:  {stats.no_expense_account}")
    print(f"  sku_collision:    {stats.sku_collision}")
    print(f"  errors:           {stats.errors}")
    if stats.error_details:
        print("  primeros 10 errores:")
        for hid, reason in stats.error_details[:10]:
            print(f"    - {hid}: {reason}")
