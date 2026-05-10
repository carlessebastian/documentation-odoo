#!/usr/bin/env python3
"""Wrapper alrededor de `oca-port` (OCA) para portar modulos entre versiones.

`oca-port` es la herramienta oficial de OCA para asistir migraciones de
modulos entre versiones Odoo. Identifica PRs cerrados upstream que aun
no estan portados, ayuda a migrarlos commit-a-commit, y opcionalmente
aplica patrones automaticos via `odoo-module-migrator`.

Repo: https://github.com/OCA/oca-port

Uso:
    python3 oca_port.py --module l10n_es_aeat_mod303 \\
        --from 18.0 --to 19.0 \\
        --repo /opt/doodba/custom/src/l10n-spain
    python3 oca_port.py --list-pending --module l10n_es \\
        --from 18.0 --to 19.0 --repo /local/clone/l10n-spain
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

from _common import OdooError


def check_oca_port_available() -> str:
    """Devuelve la version instalada de oca-port o lanza OdooError."""
    try:
        result = subprocess.run(
            ["oca-port", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except FileNotFoundError:
        raise OdooError(
            "`oca-port` no esta instalado en el host. Instalalo con "
            "`pip install oca-port` o `uv tool install oca-port`."
        )
    if result.returncode != 0:
        raise OdooError(
            f"`oca-port --version` fallo: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def run_oca_port(
    repo_path: Path,
    module: str,
    src: str,
    dst: str,
    *,
    list_pending: bool = False,
    fork_remote: str | None = None,
    extra_args: list[str] | None = None,
) -> tuple[int, str, str]:
    if not repo_path.exists():
        raise OdooError(f"Repo path no existe: {repo_path}")
    cmd: list[str] = [
        "oca-port",
        f"{src}",
        f"{dst}",
        module,
    ]
    if list_pending:
        cmd.append("--non-interactive")
    if fork_remote:
        cmd.extend(["--fork", fork_remote])
    if extra_args:
        cmd.extend(extra_args)

    proc = subprocess.run(
        cmd,
        cwd=str(repo_path),
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", required=True, help="Nombre tecnico del modulo.")
    parser.add_argument("--from", dest="src", required=True, help="Version origen (18.0).")
    parser.add_argument("--to", dest="dst", required=True, help="Version destino (19.0).")
    parser.add_argument("--repo", required=True, help="Path local al clone del repo OCA.")
    parser.add_argument(
        "--list-pending",
        action="store_true",
        help="Solo lista commits/PRs pendientes; no inicia migracion interactiva.",
    )
    parser.add_argument("--fork", help="Remote de fork donde pushear (opcional).")
    parser.add_argument(
        "--",
        dest="passthrough",
        nargs="*",
        help="Args adicionales que pasan literalmente a oca-port.",
    )
    ns = parser.parse_args()

    version = check_oca_port_available()
    repo = Path(ns.repo).resolve()

    rc, out, err = run_oca_port(
        repo,
        ns.module,
        ns.src,
        ns.dst,
        list_pending=ns.list_pending,
        fork_remote=ns.fork,
        extra_args=ns.passthrough,
    )

    json.dump(
        {
            "oca_port_version": version,
            "module": ns.module,
            "from": ns.src,
            "to": ns.dst,
            "repo": str(repo),
            "returncode": rc,
            "stdout_tail": out[-2000:],
            "stderr_tail": err[-2000:],
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
