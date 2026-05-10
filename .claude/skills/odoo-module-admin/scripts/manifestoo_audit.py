#!/usr/bin/env python3
"""Wrapper alrededor de `manifestoo` (ACSONE) para auditar arboles de modulos.

`manifestoo` analiza manifests Odoo: lista todos los modulos en un
directorio, expande dependencias, detecta core addons, valida.

Repo: https://github.com/acsone/manifestoo

Uso:
    python3 manifestoo_audit.py --addons-dir /opt/doodba/custom/src/l10n-spain
    python3 manifestoo_audit.py --addons-dir /local/path/to/repos --action list-codepends \\
        --select l10n_es_aeat_mod303
    python3 manifestoo_audit.py --addons-dir /local/path/to/repos --action check
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from _common import OdooError


VALID_ACTIONS = (
    "list",
    "list-depends",
    "list-codepends",
    "list-external-dependencies",
    "check",
    "tree",
)


def check_manifestoo_available() -> str:
    try:
        result = subprocess.run(
            ["manifestoo", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except FileNotFoundError:
        raise OdooError(
            "`manifestoo` no esta instalado. Instalalo con "
            "`pip install manifestoo` o `uv tool install manifestoo`."
        )
    if result.returncode != 0:
        raise OdooError(f"manifestoo --version fallo: {result.stderr.strip()}")
    return result.stdout.strip()


def run_manifestoo(
    addons_dir: Path,
    action: str,
    select: list[str] | None,
    odoo_series: str,
) -> tuple[int, str, str]:
    cmd: list[str] = [
        "manifestoo",
        "--addons-dir",
        str(addons_dir),
        "--odoo-series",
        odoo_series,
    ]
    if select:
        cmd.extend(["--select", ",".join(select)])
    cmd.append(action)
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--addons-dir",
        required=True,
        help="Directorio con modulos Odoo (puede contener varios repos).",
    )
    parser.add_argument(
        "--action",
        default="list",
        choices=VALID_ACTIONS,
        help="Operacion manifestoo (default: list).",
    )
    parser.add_argument(
        "--select",
        default="",
        help="CSV de modulos a seleccionar (vacio = todos).",
    )
    parser.add_argument(
        "--odoo-series",
        default="19.0",
    )
    ns = parser.parse_args()

    version = check_manifestoo_available()
    addons = Path(ns.addons_dir).resolve()
    if not addons.exists():
        raise OdooError(f"--addons-dir no existe: {addons}")

    select = [s.strip() for s in ns.select.split(",") if s.strip()] or None

    rc, out, err = run_manifestoo(addons, ns.action, select, ns.odoo_series)
    json.dump(
        {
            "manifestoo_version": version,
            "addons_dir": str(addons),
            "action": ns.action,
            "select": select,
            "odoo_series": ns.odoo_series,
            "returncode": rc,
            "stdout": out,
            "stderr_tail": err[-500:],
        },
        sys.stdout,
        indent=2,
        ensure_ascii=False,
    )
    print()
    return rc


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
