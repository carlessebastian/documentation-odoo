#!/usr/bin/env python3
"""Post-mortem de un dump Holded.

Valida que el manifest cuadra con los ficheros en disco, cuenta items
por resource, suma tamanyos, lista PDFs descargados, y resume errors.jsonl.

Uso:
    python3 scripts/dump_summary.py --dir docs/tenants/inpr3mium/holded-export/2026-05-11
    python3 scripts/dump_summary.py --dir <path> --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def count_jsonl(path: Path) -> int:
    n = 0
    with path.open("rb") as f:
        for _ in f:
            n += 1
    return n


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Validate / summarize a Holded dump directory.")
    p.add_argument("--dir", "-d", required=True, type=Path, help="Dump directory.")
    p.add_argument("--json", action="store_true", help="Machine-readable output.")
    args = p.parse_args(argv)

    root: Path = args.dir.resolve()
    if not root.exists():
        print(f"error: {root} no existe", file=sys.stderr)
        return 2
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        print(f"error: no manifest.json en {root}", file=sys.stderr)
        return 2
    manifest = json.loads(manifest_path.read_text())

    summary: dict = {
        "root": str(root),
        "created_at": manifest.get("created_at"),
        "updated_at": manifest.get("updated_at"),
        "resources": {},
        "pdfs": {},
        "errors_lines": 0,
        "warnings": [],
        "totals": {"bytes": 0, "items": 0},
    }

    for key, entry in manifest.get("resources", {}).items():
        rel = entry.get("path")
        info = {"items_manifest": entry.get("items"),
                "status": entry.get("status"), "elapsed_s": entry.get("elapsed_s")}
        if rel:
            actual = root / rel
            if not actual.exists():
                info["disk"] = "MISSING"
                summary["warnings"].append(f"{key}: {actual} no existe pese a estar en manifest")
            else:
                info["bytes"] = actual.stat().st_size
                if actual.suffix == ".jsonl":
                    info["lines"] = count_jsonl(actual)
                    if info["lines"] != entry.get("items"):
                        summary["warnings"].append(
                            f"{key}: manifest dice {entry.get('items')} items, archivo tiene {info['lines']} lineas"
                        )
                summary["totals"]["bytes"] += info["bytes"]
                if isinstance(entry.get("items"), int):
                    summary["totals"]["items"] += max(0, entry["items"])
        summary["resources"][key] = info

    # PDFs
    pdfs_root = root / "pdfs"
    if pdfs_root.exists():
        for type_dir in sorted(pdfs_root.iterdir()):
            if not type_dir.is_dir():
                continue
            files = list(type_dir.glob("*.pdf"))
            empties = [f.name for f in files if f.stat().st_size == 0]
            total_b = sum(f.stat().st_size for f in files)
            summary["pdfs"][type_dir.name] = {
                "files": len(files), "bytes": total_b, "empty_files": empties,
            }
            if empties:
                summary["warnings"].append(
                    f"pdfs/{type_dir.name}: {len(empties)} PDFs vacios"
                )
            summary["totals"]["bytes"] += total_b

    # errors.jsonl
    err = root / "errors.jsonl"
    if err.exists():
        summary["errors_lines"] = sum(1 for _ in err.open())

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0 if not summary["warnings"] and summary["errors_lines"] == 0 else 1

    print(f"Dump: {root}")
    print(f"Created: {summary['created_at']}  Updated: {summary['updated_at']}")
    print()
    print(f"{'resource':<28} {'items':>10} {'bytes':>14} status")
    print("-" * 70)
    for key, info in summary["resources"].items():
        items = info.get("lines", info.get("items_manifest", 0))
        size = fmt_bytes(info.get("bytes", 0))
        status = info.get("status", "?")
        print(f"{key:<28} {items:>10} {size:>14} {status}")
    if summary["pdfs"]:
        print()
        print(f"{'pdfs/':<28} {'files':>10} {'bytes':>14} empties")
        print("-" * 70)
        for t, info in summary["pdfs"].items():
            print(f"{t:<28} {info['files']:>10} {fmt_bytes(info['bytes']):>14} {len(info['empty_files'])}")
    print()
    print(f"Total bytes: {fmt_bytes(summary['totals']['bytes'])}")
    print(f"errors.jsonl: {summary['errors_lines']} lineas")
    if summary["warnings"]:
        print()
        print("WARNINGS:")
        for w in summary["warnings"]:
            print(f"  - {w}")
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
