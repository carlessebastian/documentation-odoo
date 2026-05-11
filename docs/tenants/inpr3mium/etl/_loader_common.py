"""Logica compartida entre los loaders de pasos 0a y 0b.

Ambos loaders (`loader_expenseaccounts.py` y `loader_saleschannels.py`)
hacen lo mismo: leer un JSONL `{id, name, accountNum, color}`, derivar
el padre PGCE Pymes via `derive_pgce_parent`, y crear una subcuenta
hija con ext_id `__holded__.account_<accountNum>` heredando
`account_type` del padre.

Por que existe este modulo en vez de duplicar 60 lineas en cada
loader: la operacion es identica salvo el archivo de input. Mantener
una sola fuente de verdad simplifica iteraciones futuras (e.g., si en
5.3 detectamos que algun `accountNum` tiene leading space, el fix va
en un sitio).
"""
from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from holded_resolvers import EXT_MODULE, derive_pgce_parent


@dataclass
class LoadStats:
    total: int = 0
    created: int = 0
    updated: int = 0
    would_create: int = 0
    would_update: int = 0
    errors: int = 0
    error_details: list[tuple[str, str]] = field(default_factory=list)  # (code, reason)


def iter_jsonl(path: Path, limit: int | None = None) -> Iterator[dict]:
    """Itera registros JSONL. Strip leading/trailing space en `name`."""
    n = 0
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)
            n += 1
            if limit and n >= limit:
                return


def lookup_parent_types(client: Any, parent_codes: set[str]) -> dict[str, str]:
    """Devuelve `{parent_code: account_type}` para los padres pedidos.

    Codes no encontrados quedan ausentes del dict (el caller debe
    reportarlos como `parent_missing`).
    """
    if not parent_codes:
        return {}
    hits = client.call(
        "account.account",
        "search_read",
        [[("code", "in", sorted(parent_codes))]],
        {"fields": ["code", "account_type"]},
    )
    return {h["code"]: h["account_type"] for h in hits}


def load_accounts(
    client: Any,
    dump_dir: Path,
    source: str,
    *,
    dry_run: bool = False,
    limit: int | None = None,
    report_dir: Path | None = None,
) -> LoadStats:
    """Carga subcuentas PGCE desde `<source>.jsonl`.

    Args:
        client: OdooClient con sesion activa.
        dump_dir: ruta al directorio `holded-export/<YYYY-MM-DD>/`.
        source: nombre del archivo sin extension (`expensesaccount` o
            `saleschannels`). El loader es agnostico al chapter PGCE;
            `derive_pgce_parent` decide.
        dry_run: si True, no llama a `create()`; solo simula y reporta.
        limit: procesa solo los primeros N records (debug).
        report_dir: si dado, escribe CSV `<source>_<run>.csv` ahi. Si
            None, usa `dump_dir/.etl_reports/` (crea si falta).

    Returns:
        LoadStats con conteos por estado.
    """
    input_path = dump_dir / f"{source}.jsonl"
    if not input_path.exists():
        raise FileNotFoundError(f"No existe: {input_path}")

    # Lazy import: solo necesario en modo no-dry-run.
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

    records = list(iter_jsonl(input_path, limit=limit))

    # Pre-fetch parent types en un solo call.
    parents_needed: set[str] = set()
    for r in records:
        p = derive_pgce_parent(r.get("accountNum"))
        if p:
            parents_needed.add(p)
    parent_types = lookup_parent_types(client, parents_needed)

    stats = LoadStats(total=len(records))
    rows: list[dict[str, Any]] = []

    for r in records:
        code = str(r.get("accountNum") or "").strip()
        name = (r.get("name") or "").strip()
        ext_id = f"{EXT_MODULE}.account_{code}"
        parent_code = derive_pgce_parent(code)

        row = {
            "holded_id": r.get("id"),
            "accountNum": code,
            "name": name,
            "parent_code": parent_code,
            "parent_type": parent_types.get(parent_code) if parent_code else None,
            "ext_id": ext_id,
            "status": "",
            "error": "",
        }

        if not code or not parent_code:
            row["status"] = "unresolved_parent"
            row["error"] = "derive_pgce_parent returned None"
            stats.errors += 1
            stats.error_details.append((code, row["error"]))
            rows.append(row)
            continue

        parent_type = parent_types.get(parent_code)
        if not parent_type:
            row["status"] = "parent_missing_in_odoo"
            row["error"] = f"account {parent_code} not found in account.account"
            stats.errors += 1
            stats.error_details.append((code, row["error"]))
            rows.append(row)
            continue

        if dry_run:
            existing_id = _search_ext_id(client, ext_id)
            row["status"] = "would_update" if existing_id else "would_create"
            if existing_id:
                stats.would_update += 1
            else:
                stats.would_create += 1
            rows.append(row)
            continue

        vals = {"code": code, "name": name, "account_type": parent_type}
        res_id, action = upsert(client, ext_id, "account.account", vals, noupdate=True)
        row["status"] = action
        row["res_id"] = res_id
        if action == "created":
            stats.created += 1
        else:
            stats.updated += 1
        rows.append(row)

    _write_report(rows, dump_dir, source, dry_run, report_dir)
    return stats


def _search_ext_id(client: Any, ext_id: str) -> int | None:
    module, name = ext_id.split(".", 1)
    hits = client.call(
        "ir.model.data",
        "search_read",
        [[("module", "=", module), ("name", "=", name)]],
        {"fields": ["res_id"], "limit": 1},
    )
    return hits[0]["res_id"] if hits else None


def _write_report(
    rows: list[dict],
    dump_dir: Path,
    source: str,
    dry_run: bool,
    report_dir: Path | None,
) -> None:
    if report_dir is None:
        report_dir = dump_dir / ".etl_reports"
    report_dir.mkdir(exist_ok=True)
    mode_tag = "dryrun" if dry_run else "run"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = report_dir / f"{source}_{mode_tag}_{ts}.csv"
    if not rows:
        return
    fields_order = [
        "holded_id",
        "accountNum",
        "name",
        "parent_code",
        "parent_type",
        "ext_id",
        "status",
        "error",
        "res_id",
    ]
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields_order, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"report: {out}", file=sys.stderr)


def print_summary(source: str, stats: LoadStats, dry_run: bool) -> None:
    mode = "DRY-RUN" if dry_run else "REAL"
    print(f"\n[{source} {mode}]")
    print(f"  total:        {stats.total}")
    if dry_run:
        print(f"  would_create: {stats.would_create}")
        print(f"  would_update: {stats.would_update}")
    else:
        print(f"  created:      {stats.created}")
        print(f"  updated:      {stats.updated}")
    print(f"  errors:       {stats.errors}")
    if stats.error_details:
        print("  primeros 10 errores:")
        for code, reason in stats.error_details[:10]:
            print(f"    - {code}: {reason}")
