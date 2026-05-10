#!/usr/bin/env python3
"""Diferencia `external_dependencies` declaradas en manifests vs `pip list`
del contenedor Odoo.

Uso:
    python3 pip_deps_check.py --paths /local/path/to/repos
    python3 pip_deps_check.py --names module1,module2  # busca via RPC los paths
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

import ssh_runner
from _common import OdooError


def parse_manifest(path: Path) -> dict | None:
    try:
        return ast.literal_eval(path.read_text(encoding="utf-8"))
    except (SyntaxError, ValueError):
        return None


def collect_deps_from_paths(paths: list[Path]) -> dict[str, set[str]]:
    """{module_name: set[pip_package]} para cada modulo encontrado."""
    out: dict[str, set[str]] = {}
    for root in paths:
        if not root.exists():
            print(f"warning: {root} no existe.", file=sys.stderr)
            continue
        for manifest in root.rglob("__manifest__.py"):
            data = parse_manifest(manifest)
            if not data:
                continue
            ed = data.get("external_dependencies") or {}
            pip_pkgs = ed.get("python") or []
            if pip_pkgs:
                out[manifest.parent.name] = set(pip_pkgs)
    return out


def get_container_pip_list(dry_run: bool = False) -> dict[str, str]:
    """{package_name_lower: version} ejecutando `pip list --format=json` en odoo."""
    cfg = ssh_runner.get_ssh_config()
    odoo_args = ["pip", "list", "--format=json", "--disable-pip-version-check"]
    result = ssh_runner.run(
        f"cd {cfg['project_dir']} && "
        f"docker compose exec -T {cfg['compose_service']} "
        + " ".join(odoo_args),
        dry_run=dry_run,
        timeout=120,
    )
    if dry_run:
        return {}
    if result.returncode != 0:
        raise OdooError(
            f"`pip list` fallo (exit {result.returncode}). "
            f"stderr: {result.stderr[-500:]}"
        )
    try:
        rows = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise OdooError(f"pip list devolvio JSON invalido: {exc}") from exc
    return {r["name"].lower(): r["version"] for r in rows}


def diff(declared: dict[str, set[str]], installed: dict[str, str]) -> dict:
    declared_all: set[str] = set()
    for pkgs in declared.values():
        declared_all.update(p.lower().split(">=")[0].split("==")[0].strip()
                            for p in pkgs)
    installed_lower = set(installed)
    missing = sorted(declared_all - installed_lower)
    by_module_missing: dict[str, list[str]] = {}
    for mod, pkgs in declared.items():
        gone = [
            p for p in pkgs
            if p.lower().split(">=")[0].split("==")[0].strip()
            not in installed_lower
        ]
        if gone:
            by_module_missing[mod] = gone
    return {
        "declared_packages": sorted(declared_all),
        "installed_packages": sorted(installed_lower),
        "missing_in_container": missing,
        "missing_by_module": by_module_missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--paths",
        required=True,
        help="CSV de directorios locales que contienen modulos.",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="No ejecuta SSH; muestra el comando.")
    ns = parser.parse_args()

    paths = [Path(p.strip()) for p in ns.paths.split(",") if p.strip()]
    declared = collect_deps_from_paths(paths)
    if not declared:
        print(
            "No se encontraron manifests con external_dependencies.python.",
            file=sys.stderr,
        )
        return 4

    installed = get_container_pip_list(dry_run=ns.dry_run)
    if ns.dry_run:
        json.dump(
            {"declared_by_module": {k: sorted(v) for k, v in declared.items()}},
            sys.stdout,
            indent=2,
            ensure_ascii=False,
        )
        print()
        return 0

    out = diff(declared, installed)
    json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0 if not out["missing_in_container"] else 5


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
