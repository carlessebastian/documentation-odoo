#!/usr/bin/env python3
"""Dump completo (read-only) de una cuenta Holded a disco.

Salida
------
  <output-dir>/
    manifest.json              # version, timestamp, counts, sha256 por fichero
    contacts.jsonl
    products.jsonl
    services.jsonl
    warehouses.jsonl
    treasuries.jsonl
    expensesaccount.jsonl
    taxes.jsonl
    saleschannels.jsonl
    payments.jsonl
    remittances.jsonl
    contact_groups.json        # objeto raw (no es lista paginable)
    numbering_series.json      # dict { docType: series_data } por cada docType
    documents/
      invoice.jsonl
      purchase.jsonl
      ...
    dailyledger.jsonl
    pdfs/
      purchase/<id>.pdf        # PDF original escaneado, si la app movil lo subio
      invoice/<id>.pdf         # PDF generado por Holded
    errors.jsonl               # 1 linea por fallo, con resource + id + error

Idempotencia y resume
---------------------
- El manifest se actualiza al cerrar cada resource (no al final).
- Si re-ejecutas con el mismo output-dir, los resources ya escritos
  (con bytes > 0 en manifest) se saltan. Para forzar, usa `--force`.
- Los PDFs son atomic: temp file + os.replace al final.

CLI
---
    --output-dir PATH       (default: ./holded-export/<YYYY-MM-DD>)
    --resources LIST        CSV de resources (default: todos)
    --doc-types LIST        CSV de docTypes a incluir (default: todos)
    --start-date YYYY-MM-DD limite inferior para documents + dailyledger
    --end-date YYYY-MM-DD   limite superior
    --include-pdfs          (default: false) descarga PDFs de docs
    --pdf-doc-types LIST    para que docTypes bajar PDFs (default: invoice,purchase)
    --resume                honra manifest existente y continua
    --force                 sobrescribe lo existente
    --limit N               smoke test: max N items por resource
    --no-confirm            no pedir confirmacion interactiva
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import OdooEnvError, require_env  # type: ignore
from holded_client import (  # type: ignore
    DOC_TYPES,
    HoldedClient,
    HoldedError,
    iter_contacts,
    iter_dailyledger,
    iter_documents,
    iter_payments,
    iter_products,
    iter_remittances,
    iter_saleschannels,
    iter_services,
    iter_taxes,
    iter_treasuries,
    iter_warehouses,
    iter_expensesaccount,
    get_contact_groups,
    get_numbering_series,
)

logger = logging.getLogger("holded_export")

ALL_RESOURCES = (
    "contacts",
    "contact_groups",
    "products",
    "services",
    "warehouses",
    "treasuries",
    "expensesaccount",
    "taxes",
    "saleschannels",
    "payments",
    "remittances",
    "numbering_series",
    "documents",
    "dailyledger",
)


def _date_to_ts(s: str | None) -> int | None:
    if not s:
        return None
    return int(dt.datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp())


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(64 * 1024):
            h.update(chunk)
    return h.hexdigest()


def _write_atomic(path: Path, data: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(data)
    tmp.replace(path)


def _append_jsonl_iter(
    path: Path,
    items: Iterator[Any],
    *,
    limit: int | None = None,
    error_log: Path | None = None,
    resource_label: str = "",
) -> int:
    """Stream items to a JSONL file, returns count. Errors -> error_log."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as fh:
        try:
            for it in items:
                fh.write(json.dumps(it, ensure_ascii=False) + "\n")
                n += 1
                if limit is not None and n >= limit:
                    break
        except Exception as e:
            if error_log:
                with error_log.open("a", encoding="utf-8") as ef:
                    ef.write(json.dumps({
                        "resource": resource_label,
                        "error": f"{type(e).__name__}: {e}",
                        "at_item": n,
                        "ts": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
                    }, ensure_ascii=False) + "\n")
            raise
    return n


def _load_manifest(path: Path) -> dict[str, Any]:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {"version": 1, "resources": {}, "pdfs": {}}


def _save_manifest(path: Path, manifest: dict[str, Any]) -> None:
    manifest["updated_at"] = dt.datetime.now(tz=dt.timezone.utc).isoformat()
    _write_atomic(path, (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode())


def _resource_done(manifest: dict[str, Any], key: str) -> bool:
    e = manifest.get("resources", {}).get(key)
    return bool(e and e.get("items", 0) >= 0 and e.get("status") == "ok")


def _record_resource(
    manifest: dict[str, Any],
    key: str,
    *,
    path: Path | None,
    items: int,
    elapsed_s: float,
    status: str = "ok",
    detail: dict[str, Any] | None = None,
) -> None:
    entry: dict[str, Any] = {
        "items": items,
        "elapsed_s": round(elapsed_s, 3),
        "status": status,
    }
    if path is not None and path.exists():
        entry["path"] = path.name if path.parent == Path(manifest.get("_root", "")) else str(path.relative_to(manifest.get("_root", path.parent)))
        entry["bytes"] = path.stat().st_size
        entry["sha256"] = _sha256_file(path)
    if detail:
        entry.update(detail)
    manifest.setdefault("resources", {})[key] = entry


def dump_resource_jsonl(
    *,
    root: Path,
    manifest: dict[str, Any],
    key: str,
    relpath: str,
    iter_fn: Callable[[], Iterator[Any]],
    limit: int | None,
    resume: bool,
    force: bool,
) -> tuple[int, float]:
    out_path = root / relpath
    if resume and not force and _resource_done(manifest, key):
        logger.info("[skip]  %s (resume)", key)
        return manifest["resources"][key].get("items", 0), 0.0
    t0 = time.time()
    error_log = root / "errors.jsonl"
    n = _append_jsonl_iter(out_path, iter_fn(), limit=limit, error_log=error_log, resource_label=key)
    elapsed = time.time() - t0
    _record_resource(manifest, key, path=out_path, items=n, elapsed_s=elapsed)
    logger.info("[done]  %s -> %d items in %.1fs", key, n, elapsed)
    return n, elapsed


def dump_pdfs(
    *,
    client: HoldedClient,
    root: Path,
    manifest: dict[str, Any],
    documents_dir: Path,
    pdf_doc_types: tuple[str, ...],
    resume: bool,
    force: bool,
) -> dict[str, int]:
    """Tras tener documents/<type>.jsonl, descarga el PDF de cada uno."""
    stats: dict[str, int] = {"downloaded": 0, "skipped": 0, "errors": 0, "no_pdf": 0}
    pdfs_root = root / "pdfs"
    pdfs_manifest: dict[str, dict[str, Any]] = manifest.setdefault("pdfs", {})
    error_log = root / "errors.jsonl"
    for doc_type in pdf_doc_types:
        if doc_type not in DOC_TYPES:
            logger.warning("pdf: doc_type %r no es valido; skip", doc_type)
            continue
        jsonl = documents_dir / f"{doc_type}.jsonl"
        if not jsonl.exists():
            logger.info("pdf: no hay %s.jsonl; skip", doc_type)
            continue
        target_dir = pdfs_root / doc_type
        target_dir.mkdir(parents=True, exist_ok=True)
        per_type = pdfs_manifest.setdefault(doc_type, {"downloaded": 0, "no_pdf": 0, "errors": 0})
        with jsonl.open("r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f):
                try:
                    doc = json.loads(line)
                except json.JSONDecodeError:
                    continue
                doc_id = doc.get("id") or doc.get("_id")
                if not doc_id:
                    continue
                pdf_path = target_dir / f"{doc_id}.pdf"
                if pdf_path.exists() and pdf_path.stat().st_size > 0 and resume and not force:
                    stats["skipped"] += 1
                    continue
                try:
                    body = client.download_pdf(doc_type, doc_id)
                except HoldedError as e:
                    stats["errors"] += 1
                    per_type["errors"] += 1
                    with error_log.open("a", encoding="utf-8") as ef:
                        ef.write(json.dumps({
                            "resource": f"pdf.{doc_type}",
                            "doc_id": doc_id,
                            "error": str(e),
                            "ts": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
                        }, ensure_ascii=False) + "\n")
                    continue
                except Exception as e:
                    stats["errors"] += 1
                    per_type["errors"] += 1
                    with error_log.open("a", encoding="utf-8") as ef:
                        ef.write(json.dumps({
                            "resource": f"pdf.{doc_type}",
                            "doc_id": doc_id,
                            "error": f"{type(e).__name__}: {e}",
                            "ts": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
                        }, ensure_ascii=False) + "\n")
                    continue
                if not body:
                    stats["no_pdf"] += 1
                    per_type["no_pdf"] += 1
                    continue
                _write_atomic(pdf_path, body)
                stats["downloaded"] += 1
                per_type["downloaded"] += 1
                if stats["downloaded"] % 20 == 0:
                    logger.info("pdf: %s downloaded=%d errors=%d no_pdf=%d skipped=%d",
                                doc_type, stats["downloaded"], stats["errors"],
                                stats["no_pdf"], stats["skipped"])
    return stats


def confirm_or_die(msg: str, no_confirm: bool) -> None:
    if no_confirm:
        return
    print(msg)
    print("Continue? [y/N] ", end="", flush=True)
    resp = sys.stdin.readline().strip().lower()
    if resp not in ("y", "yes"):
        print("aborted.", file=sys.stderr)
        sys.exit(130)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dump read-only de Holded a disco.")
    today = dt.date.today().isoformat()
    parser.add_argument("--output-dir", type=Path, default=Path(f"./holded-export/{today}"),
                        help="Directorio de salida (default: ./holded-export/<today>).")
    parser.add_argument("--resources", default=",".join(ALL_RESOURCES),
                        help=f"CSV de resources a incluir. Disponibles: {','.join(ALL_RESOURCES)}.")
    parser.add_argument("--doc-types", default=",".join(DOC_TYPES),
                        help=f"CSV de docTypes para `documents`. Validos: {','.join(DOC_TYPES)}.")
    parser.add_argument("--start-date", help="YYYY-MM-DD (limite inferior para documents/dailyledger).")
    parser.add_argument("--end-date", help="YYYY-MM-DD (limite superior).")
    parser.add_argument("--include-pdfs", action="store_true", help="Descarga PDFs originales de docs.")
    parser.add_argument("--pdf-doc-types", default="invoice,purchase",
                        help="CSV de docTypes para descargar PDFs (default: invoice,purchase).")
    parser.add_argument("--resume", action="store_true", help="Salta lo ya descargado segun manifest.")
    parser.add_argument("--force", action="store_true", help="Sobrescribe lo existente.")
    parser.add_argument("--limit", type=int, help="Max N items por resource (smoke test).")
    parser.add_argument("--no-confirm", action="store_true", help="No pedir confirmacion.")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        require_env("HOLDED_API_KEY")
    except OdooEnvError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    requested = [r.strip() for r in args.resources.split(",") if r.strip()]
    invalid = [r for r in requested if r not in ALL_RESOURCES]
    if invalid:
        print(f"error: resources desconocidos: {invalid}. Validos: {ALL_RESOURCES}",
              file=sys.stderr)
        return 2

    requested_doc_types = [t.strip() for t in args.doc_types.split(",") if t.strip()]
    invalid_dt = [t for t in requested_doc_types if t not in DOC_TYPES]
    if invalid_dt:
        print(f"error: docTypes desconocidos: {invalid_dt}. Validos: {DOC_TYPES}",
              file=sys.stderr)
        return 2

    pdf_doc_types = tuple(t.strip() for t in args.pdf_doc_types.split(",") if t.strip())

    start_ts = _date_to_ts(args.start_date)
    end_ts = _date_to_ts(args.end_date)

    root = args.output_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "manifest.json"
    manifest = _load_manifest(manifest_path)
    manifest["_root"] = str(root)
    manifest.setdefault("created_at", dt.datetime.now(tz=dt.timezone.utc).isoformat())
    manifest["args"] = {
        "resources": requested,
        "doc_types": requested_doc_types,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "include_pdfs": bool(args.include_pdfs),
        "pdf_doc_types": list(pdf_doc_types),
        "limit": args.limit,
    }

    pdfs_estimate = ""
    if args.include_pdfs:
        pdfs_estimate = f"\n  - PDFs: SI ({','.join(pdf_doc_types)})"
    confirm_or_die(
        f"\n=== Holded export plan ===\n"
        f"  - Output: {root}\n"
        f"  - Resources: {','.join(requested)}\n"
        f"  - Doc types: {','.join(requested_doc_types)}\n"
        f"  - Date range: {args.start_date or '-inf'} -> {args.end_date or '+inf'}"
        f"{pdfs_estimate}\n"
        f"  - Resume: {args.resume} | Force: {args.force} | Limit: {args.limit}\n",
        no_confirm=args.no_confirm,
    )

    client = HoldedClient()

    # ---------------- Resources simples ----------------
    iter_map: dict[str, tuple[str, Callable[[], Iterator[Any]]]] = {
        "contacts": ("contacts.jsonl", lambda: iter_contacts(client)),
        "products": ("products.jsonl", lambda: iter_products(client)),
        "services": ("services.jsonl", lambda: iter_services(client)),
        "warehouses": ("warehouses.jsonl", lambda: iter_warehouses(client)),
        "treasuries": ("treasuries.jsonl", lambda: iter_treasuries(client)),
        "expensesaccount": ("expensesaccount.jsonl", lambda: iter_expensesaccount(client)),
        "taxes": ("taxes.jsonl", lambda: iter_taxes(client)),
        "saleschannels": ("saleschannels.jsonl", lambda: iter_saleschannels(client)),
        "payments": ("payments.jsonl", lambda: iter_payments(client)),
        "remittances": ("remittances.jsonl", lambda: iter_remittances(client)),
    }
    for key in requested:
        if key not in iter_map:
            continue
        relpath, factory = iter_map[key]
        try:
            dump_resource_jsonl(
                root=root, manifest=manifest, key=key, relpath=relpath,
                iter_fn=factory, limit=args.limit, resume=args.resume, force=args.force,
            )
        except Exception as e:
            logger.error("resource %s failed: %s", key, e)
            _record_resource(manifest, key, path=root / relpath, items=-1,
                             elapsed_s=0, status="error", detail={"error": str(e)})
        _save_manifest(manifest_path, manifest)

    # ---------------- contact_groups (raw) ----------------
    if "contact_groups" in requested:
        try:
            data = get_contact_groups(client)
            cg_path = root / "contact_groups.json"
            _write_atomic(cg_path, (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode())
            items = len(data) if isinstance(data, list) else (1 if data else 0)
            _record_resource(manifest, "contact_groups", path=cg_path, items=items, elapsed_s=0)
        except Exception as e:
            logger.error("contact_groups failed: %s", e)
            _record_resource(manifest, "contact_groups", path=None, items=-1,
                             elapsed_s=0, status="error", detail={"error": str(e)})
        _save_manifest(manifest_path, manifest)

    # ---------------- numbering_series (1 GET por docType) ----------------
    if "numbering_series" in requested:
        ns_path = root / "numbering_series.json"
        result: dict[str, Any] = {}
        if ns_path.exists() and args.resume and not args.force:
            try:
                result = json.loads(ns_path.read_text())
            except Exception:
                result = {}
        for t in requested_doc_types:
            try:
                result[t] = get_numbering_series(client, t)
            except Exception as e:
                logger.warning("numbering_series.%s failed: %s", t, e)
                result.setdefault(t, {"error": str(e)})
        _write_atomic(ns_path, (json.dumps(result, indent=2, ensure_ascii=False) + "\n").encode())
        _record_resource(manifest, "numbering_series", path=ns_path,
                         items=len(result), elapsed_s=0)
        _save_manifest(manifest_path, manifest)

    # ---------------- documents (1 jsonl por docType) ----------------
    documents_dir = root / "documents"
    if "documents" in requested:
        documents_dir.mkdir(parents=True, exist_ok=True)
        date_filters: dict[str, Any] = {}
        if start_ts is not None:
            date_filters["starttmp"] = start_ts
        if end_ts is not None:
            date_filters["endtmp"] = end_ts
        for t in requested_doc_types:
            key = f"documents.{t}"
            relpath = f"documents/{t}.jsonl"
            try:
                dump_resource_jsonl(
                    root=root, manifest=manifest, key=key, relpath=relpath,
                    iter_fn=lambda t=t: iter_documents(client, t, **date_filters),
                    limit=args.limit, resume=args.resume, force=args.force,
                )
            except Exception as e:
                logger.error("documents.%s failed: %s", t, e)
                _record_resource(manifest, key, path=root / relpath, items=-1,
                                 elapsed_s=0, status="error", detail={"error": str(e)})
            _save_manifest(manifest_path, manifest)

    # ---------------- dailyledger (page=N, max 500/page) ----------------
    if "dailyledger" in requested:
        date_filters = {}
        if start_ts is not None:
            date_filters["starttmp"] = start_ts
        if end_ts is not None:
            date_filters["endtmp"] = end_ts
        try:
            dump_resource_jsonl(
                root=root, manifest=manifest, key="dailyledger",
                relpath="dailyledger.jsonl",
                iter_fn=lambda: iter_dailyledger(client, **date_filters),
                limit=args.limit, resume=args.resume, force=args.force,
            )
        except Exception as e:
            logger.error("dailyledger failed: %s", e)
            _record_resource(manifest, "dailyledger", path=root / "dailyledger.jsonl",
                             items=-1, elapsed_s=0, status="error", detail={"error": str(e)})
        _save_manifest(manifest_path, manifest)

    # ---------------- PDFs ----------------
    if args.include_pdfs:
        stats = dump_pdfs(
            client=client, root=root, manifest=manifest,
            documents_dir=documents_dir, pdf_doc_types=pdf_doc_types,
            resume=args.resume, force=args.force,
        )
        manifest.setdefault("pdfs", {})["_summary"] = stats
        _save_manifest(manifest_path, manifest)
        logger.info("pdfs summary: %s", stats)

    print("---")
    print(f"Manifest: {manifest_path}")
    print(f"Resources: {list(manifest.get('resources', {}).keys())}")
    err_path = root / "errors.jsonl"
    if err_path.exists() and err_path.stat().st_size > 0:
        print(f"WARN: errors.jsonl tiene contenido ({err_path.stat().st_size} bytes). Revisar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
