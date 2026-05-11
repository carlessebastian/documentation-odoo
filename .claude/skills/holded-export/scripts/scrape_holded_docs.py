#!/usr/bin/env python3
"""Vendoriza la doc de developers.holded.com a un directorio local.

Estrategia
----------
developers.holded.com es un site ReadMe.io que renderiza el sidebar
client-side; no expone sitemap.xml ni un OpenAPI publico. Las paginas
de endpoint sirven una variante `.md` muy limpia (la pagina + el
OpenAPI definition embebido).

Este scraper:

1. Toma una lista canonica de slugs (SEED_SLUGS, una entrada por
   endpoint conocido — invoicing, accounting, crm, projects, team).
2. Para cada slug intenta `GET https://developers.holded.com/reference/<slug>.md`.
3. Detecta el "404 que devuelve HTML del SPA" (typical de ReadMe.io)
   inspeccionando los primeros bytes del body. Si parece HTML, descarta.
4. Calcula sha256 del contenido y lo escribe a
   `references/holded-api/<slug>.md`. Si el fichero existe y el sha256
   coincide, salta (idempotente).
5. Genera un `references/holded-api/INDEX.json` con metadata: slugs
   recuperados, no encontrados, timestamps, hashes.

Re-ejecutable sin efectos secundarios. Si ReadMe.io anyade endpoints
nuevos, anyade el slug a SEED_SLUGS y vuelve a correr.

Uso
---
    python3 scripts/scrape_holded_docs.py \
        --output references/holded-api/

Flags utiles:
    --output PATH        Directorio destino (default: references/holded-api).
    --base URL           Base URL (default: https://developers.holded.com).
    --force              Re-escribe aunque el sha256 coincida.
    --probe SLUG         No descarga; comprueba si SLUG existe.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# -----------------------------------------------------------------------------
# Slugs canonicos
# -----------------------------------------------------------------------------
# Curados a partir de la doc oficial (https://developers.holded.com/reference)
# Cada slug corresponde a un endpoint individual (`/reference/<slug>.md`).
# Si descubres un slug nuevo, anyadelo aqui y vuelve a correr el scraper.
SEED_SLUGS: list[str] = [
    # --- Invoicing -> contacts ---
    "list-contacts-1",
    "create-contact-1",
    "get-contact-1",
    "update-contact-1",
    "delete-contact-1",
    # --- Invoicing -> contact groups ---
    "list-contact-groups",
    "update-contact-group",
    "delete-contact-group",
    # --- Invoicing -> documents (the heaviest area) ---
    "list-documents-1",        # incluye GET-by-id implicito via filtros
    "create-document-1",
    "update-document-1",       # PUT /documents/{docType}/{documentId}
    "delete-document-1",       # DELETE /documents/{docType}/{documentId}
    "getdocumentpdf",          # GET /documents/{docType}/{id}/pdf -> base64
    # --- Invoicing -> products ---
    "list-products-1",
    "create-product-1",
    "get-product",
    "update-product-1",
    "delete-product-1",
    # --- Invoicing -> services ---
    "list-services",
    "create-service",
    "get-service",
    "update-service",
    "delete-service",
    # --- Invoicing -> warehouses ---
    "list-warehouses-1",
    "get-warehouse-1",
    "update-warehouse-1",
    "delete-warehouse",
    # --- Invoicing -> treasury accounts ---
    "list-treasuries",
    "get-treasury-1",
    # --- Invoicing -> taxes ---
    "gettaxes",
    # --- Invoicing -> numbering series (Holded only expone GET by type) ---
    "get-numbering-series-1",
    # --- Invoicing -> payments ---
    "list-payments-1",
    "create-payment-1",
    "get-payment-1",
    "update-payment-1",
    "delete-payment-1",
    # --- Invoicing -> remittances ---
    "list-remittances",
    # --- Invoicing -> sales channels ---
    "list-sales-channels-1",
    "create-sales-channel-1",
    "get-sales-channel-1",
    "update-sales-channel-1",
    "delete-sales-channel-1",
    # --- Accounting -> daily ledger (asientos) ---
    "listdailyledger",
    # --- Projects ---
    "list-projects",
    "create-project",
    "get-project",
    "update-project",
    "delete-project",
    "list-tasks",
    "create-task",
    "get-task",
    "delete-task",
    # --- Team / employees (limitada) ---
    "update-employee",
    # --- Stub / category pages (no endpoint, narrativa minima) ---
    "authentication",
    "getting-started",
    "taxes",
    "numbering-series",
    "expenses-accounts",
    "bookings",
]
# Slugs auxiliares (probados pero NO encontrados — dejados aqui como pista para
# futuras incorporaciones si Holded los anyade):
#   list-warehouse-movements, list-funnels, list-leads, list-employees,
#   list-expense-accounts*, list-taxes, list-numbering-series-1,
#   create-numbering-series, update-numbering-series, contactsupplier-*,
#   senddocumentemail, paydocument, shipdocument, getproductstock,
#   createdailyledgerentry, updatedailyledgerentry, list-payslips,
#   rate-limits, pagination, errors, webhooks.


BASE = "https://developers.holded.com"
TIMEOUT = 20.0
USER_AGENT = "odoo-agent-holded-export/0.1 (+https://github.com/carlessebastian/odoo-agent)"


class ScrapeError(Exception):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_spa_fallback(body: bytes) -> bool:
    """ReadMe.io devuelve la SPA (HTML) cuando el slug no existe (200/404).

    Detectamos por los primeros bytes. La doc real empieza por `# Titulo`
    (Markdown) o por `---` (frontmatter) o por backticks de bloque OpenAPI.
    """
    head = body.lstrip()[:200].lower()
    if head.startswith(b"<!doctype") or head.startswith(b"<html") or b"<script" in head[:200]:
        return True
    return False


def fetch_md(slug: str, *, base: str = BASE, attempts: int = 3, base_delay: float = 1.0) -> bytes | None:
    """Descarga el .md de un slug. Devuelve None si no existe."""
    url = f"{base}/reference/{slug}.md"
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/plain, text/markdown, */*"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                body = resp.read()
                status = resp.status
                ctype = resp.headers.get("Content-Type", "")
                if status == 200 and ctype.startswith("text/plain") and not is_spa_fallback(body):
                    return body
                if status == 200 and is_spa_fallback(body):
                    return None  # slug no existe; ReadMe sirve la SPA
                if status >= 500:
                    last_exc = ScrapeError(f"{slug}: HTTP {status}")
                else:
                    return None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code >= 500 or e.code == 429:
                last_exc = e
            else:
                raise ScrapeError(f"{slug}: HTTP {e.code}") from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_exc = e
        time.sleep(base_delay * (2 ** i))
    if last_exc:
        raise ScrapeError(f"{slug}: agotados {attempts} intentos: {last_exc}")
    return None


def write_atomic(path: Path, data: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def scrape(output_dir: Path, *, base: str = BASE, force: bool = False, slugs: list[str] | None = None) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "INDEX.json"
    prior: dict = {}
    if index_path.exists():
        try:
            prior = json.loads(index_path.read_text())
        except Exception:
            prior = {}
    prior_entries: dict = {e["slug"]: e for e in prior.get("entries", [])}

    target_slugs = slugs if slugs is not None else SEED_SLUGS
    entries = []
    not_found: list[str] = []
    errors: list[dict] = []
    skipped = 0
    new = 0
    updated = 0

    for slug in target_slugs:
        path = output_dir / f"{slug}.md"
        try:
            body = fetch_md(slug, base=base)
        except ScrapeError as e:
            errors.append({"slug": slug, "error": str(e)})
            print(f"[err]   {slug}: {e}", file=sys.stderr)
            continue
        if body is None:
            not_found.append(slug)
            print(f"[404]   {slug}")
            continue
        sha = sha256_bytes(body)
        existed = path.exists()
        prior_entry = prior_entries.get(slug)
        if existed and not force and prior_entry and prior_entry.get("sha256") == sha:
            entries.append(prior_entry)
            skipped += 1
            print(f"[skip]  {slug}  ({sha[:8]})")
            continue
        write_atomic(path, body)
        entry = {
            "slug": slug,
            "path": f"{slug}.md",
            "bytes": len(body),
            "sha256": sha,
            "fetched_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        }
        entries.append(entry)
        if existed:
            updated += 1
            print(f"[upd]   {slug}  ({len(body)} B, {sha[:8]})")
        else:
            new += 1
            print(f"[new]   {slug}  ({len(body)} B, {sha[:8]})")

    summary = {
        "base": base,
        "scraped_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        "total_attempted": len(target_slugs),
        "found": len(entries),
        "not_found": len(not_found),
        "errors": len(errors),
        "new": new,
        "updated": updated,
        "skipped": skipped,
        "entries": sorted(entries, key=lambda e: e["slug"]),
        "missing_slugs": sorted(not_found),
        "error_details": errors,
    }
    write_atomic(index_path, (json.dumps(summary, indent=2, ensure_ascii=False) + "\n").encode())
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scrape developers.holded.com docs to local markdown.")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent.parent / "references" / "holded-api",
                        help="Output directory (default: references/holded-api/).")
    parser.add_argument("--base", default=BASE, help=f"Base URL (default: {BASE}).")
    parser.add_argument("--force", action="store_true", help="Re-write even if sha256 matches.")
    parser.add_argument("--probe", metavar="SLUG", help="Probe a single slug; do not write.")
    parser.add_argument("--slug", action="append", help="Restrict to specific slugs (can repeat). Default: all SEED_SLUGS.")
    args = parser.parse_args(argv)

    if args.probe:
        body = fetch_md(args.probe, base=args.base)
        if body is None:
            print(f"NOT FOUND: {args.probe}")
            return 2
        print(f"FOUND: {args.probe} ({len(body)} bytes, sha256={sha256_bytes(body)[:12]})")
        print("--- preview ---")
        sys.stdout.write(body[:500].decode(errors="replace"))
        return 0

    slugs = args.slug if args.slug else None
    summary = scrape(args.output, base=args.base, force=args.force, slugs=slugs)
    print("---")
    print(f"Total: attempted={summary['total_attempted']}, "
          f"found={summary['found']}, not_found={summary['not_found']}, "
          f"errors={summary['errors']}")
    print(f"Detail: new={summary['new']}, updated={summary['updated']}, skipped={summary['skipped']}")
    print(f"Index: {args.output / 'INDEX.json'}")
    return 0 if summary["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
