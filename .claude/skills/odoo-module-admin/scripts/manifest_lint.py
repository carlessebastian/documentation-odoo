#!/usr/bin/env python3
"""Valida un `__manifest__.py` (o varios) sin ejecutar codigo Odoo.

Parsea via `ast.literal_eval` (seguro). Verifica claves obligatorias y
warnings sobre claves desaconsejadas en Odoo 19.

Uso:
    python3 manifest_lint.py path/to/module          # un modulo
    python3 manifest_lint.py path/to/repo/*/         # glob de modulos
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path


REQUIRED_KEYS = ("name", "version", "depends", "license")
RECOMMENDED_KEYS = ("category", "summary", "author", "installable")
SUSPECTED_DEPRECATED = ("active", "complexity", "sequence")
ODOO_19_VERSION_PREFIX = "19.0."


class ManifestError(Exception):
    """Error sintactico o semantico en un __manifest__.py."""


def parse_manifest(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    try:
        node = ast.parse(text, mode="eval")
    except SyntaxError as exc:
        raise ManifestError(f"{path}: SyntaxError {exc.msg} at line {exc.lineno}")
    try:
        data = ast.literal_eval(node)
    except ValueError as exc:
        raise ManifestError(
            f"{path}: el manifest contiene expresiones que no son "
            f"literales (variables, llamadas a funciones): {exc}"
        )
    if not isinstance(data, dict):
        raise ManifestError(f"{path}: el manifest no evalua a un dict.")
    return data


def lint_one(module_dir: Path) -> dict:
    manifest_path = module_dir / "__manifest__.py"
    if not manifest_path.exists():
        # Probar __openerp__.py legacy (no aceptado en Odoo 19)
        legacy = module_dir / "__openerp__.py"
        if legacy.exists():
            return {
                "module": module_dir.name,
                "status": "error",
                "errors": [
                    "Usa __openerp__.py legacy. Renombrar a __manifest__.py "
                    "(Odoo >=10)."
                ],
            }
        return {
            "module": module_dir.name,
            "status": "skip",
            "errors": ["No es un modulo Odoo (sin __manifest__.py)."],
        }

    errors: list[str] = []
    warnings: list[str] = []
    try:
        data = parse_manifest(manifest_path)
    except ManifestError as exc:
        return {
            "module": module_dir.name,
            "status": "error",
            "errors": [str(exc)],
        }

    for k in REQUIRED_KEYS:
        if k not in data:
            errors.append(f"Falta clave obligatoria: {k!r}")

    for k in RECOMMENDED_KEYS:
        if k not in data:
            warnings.append(f"Falta clave recomendada: {k!r}")

    version = data.get("version", "")
    if version and not isinstance(version, str):
        errors.append("`version` debe ser str.")
    elif version and not version.startswith(ODOO_19_VERSION_PREFIX):
        warnings.append(
            f"`version` es {version!r}; para Odoo 19 deberia empezar por "
            f"{ODOO_19_VERSION_PREFIX!r}."
        )

    installable = data.get("installable", True)
    if installable is False:
        warnings.append(
            "`installable=False`: el modulo NO se podra instalar tal cual. "
            "Suele indicar migracion en curso."
        )

    deps = data.get("depends", [])
    if not isinstance(deps, list):
        errors.append("`depends` debe ser una lista de nombres de modulo.")
    elif not deps:
        warnings.append(
            "`depends` esta vacio: la mayoria de modulos dependen al menos "
            "de `base`."
        )

    license_ = data.get("license")
    if license_ and license_ not in (
        "LGPL-3",
        "AGPL-3",
        "GPL-3",
        "GPL-3 or any later version",
        "OEEL-1",
        "OPL-1",
        "Other proprietary",
        "Other OSI approved licence",
    ):
        warnings.append(
            f"License {license_!r} no esta en la lista estandar de Odoo."
        )

    for k in SUSPECTED_DEPRECATED:
        if k in data:
            warnings.append(
                f"Clave {k!r} desaconsejada en Odoo 19; suele ser legado."
            )

    return {
        "module": module_dir.name,
        "path": str(module_dir),
        "status": "error" if errors else ("warn" if warnings else "ok"),
        "version": data.get("version"),
        "depends": data.get("depends"),
        "license": data.get("license"),
        "installable": installable,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="Carpetas de modulo a auditar")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Salida JSON (default: texto humano).",
    )
    ns = parser.parse_args()

    targets: list[Path] = []
    for raw in ns.paths:
        p = Path(raw)
        if not p.exists():
            print(f"warning: {p} no existe; ignorando.", file=sys.stderr)
            continue
        if (p / "__manifest__.py").exists() or (p / "__openerp__.py").exists():
            targets.append(p)
        else:
            # carpeta padre: tomar subdirectorios que parecen modulos
            for child in sorted(p.iterdir()):
                if child.is_dir() and (child / "__manifest__.py").exists():
                    targets.append(child)

    if not targets:
        print("No se encontraron modulos.", file=sys.stderr)
        return 4

    results = [lint_one(t) for t in targets]
    has_error = any(r["status"] == "error" for r in results)

    if ns.json:
        json.dump(results, sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        for r in results:
            tag = {"ok": "OK", "warn": "WARN", "error": "ERR", "skip": "--"}[r["status"]]
            print(f"[{tag}] {r['module']}: v={r.get('version')} "
                  f"deps={len(r.get('depends') or [])} "
                  f"license={r.get('license')}")
            for e in r.get("errors", []):
                print(f"    ERR: {e}")
            for w in r.get("warnings", []):
                print(f"    warn: {w}")

    return 1 if has_error else 0


if __name__ == "__main__":
    sys.exit(main())
