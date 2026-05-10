#!/usr/bin/env python3
"""Instala modulo(s) en una instancia doodba via SSH + docker compose run.

Flujo:
1. Comprueba via RPC el estado actual de los modulos.
2. Si alguno esta `installed`, avisa y aborta.
3. Refresca apps list.
4. SSH -> docker compose run --rm -T odoo odoo --stop-after-init -i ...
5. Verifica via RPC que el state paso a `installed`.
6. Reinicia el contenedor para reanudar HTTP.

Uso:
    python3 module_install.py --names l10n_es_aeat_mod303
    python3 module_install.py --names auditlog,queue_job --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

import ssh_runner
from _common import OdooError
from odoo_client import OdooClient


def precheck_states(
    client: OdooClient, names: Sequence[str]
) -> tuple[list[str], list[str], list[str]]:
    """Devuelve (to_install, already_installed, missing)."""
    rows = client.call(
        "ir.module.module",
        "search_read",
        [[("name", "in", list(names))]],
        {"fields": ["name", "state"]},
    )
    by_name = {r["name"]: r["state"] for r in rows}
    to_install = [n for n in names if by_name.get(n) == "uninstalled"]
    already = [n for n in names if by_name.get(n) == "installed"]
    missing = [n for n in names if n not in by_name]
    bad = [n for n in names if by_name.get(n) == "uninstallable"]
    if bad:
        raise OdooError(
            f"Modulos en estado uninstallable: {bad}. "
            "Revisa __manifest__.py con scripts/manifest_lint.py."
        )
    return to_install, already, missing


def install_via_ssh(
    names: Sequence[str], dry_run: bool, db_name: str
) -> ssh_runner.SshResult:
    odoo_args = [
        "odoo",
        "--stop-after-init",
        "--no-http",
        "-d",
        db_name,
        "-i",
        ",".join(names),
        "--logfile=/dev/stderr",
    ]
    return ssh_runner.docker_compose_run(odoo_args, dry_run=dry_run, timeout=3600)


def verify_post(client: OdooClient, names: Sequence[str]) -> dict[str, str]:
    rows = client.call(
        "ir.module.module",
        "search_read",
        [[("name", "in", list(names))]],
        {"fields": ["name", "state"]},
    )
    return {r["name"]: r["state"] for r in rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--names", required=True, help="CSV de modulos.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Muestra el comando que se ejecutaria.")
    parser.add_argument("--skip-restart", action="store_true",
                        help="No reinicia el servicio tras instalar.")
    ns = parser.parse_args()

    names = [n.strip() for n in ns.names.split(",") if n.strip()]
    if not names:
        raise OdooError("--names vacio.")

    client = OdooClient()
    cfg = ssh_runner.get_ssh_config()
    if not cfg["db_name"]:
        raise OdooError("DOODBA_DB_NAME / ODOO_DB no esta seteado.")

    # Refrescar apps list para detectar nuevos modulos en custom/
    client.call("ir.module.module", "update_list", [])

    to_install, already, missing = precheck_states(client, names)
    if missing:
        raise OdooError(
            f"Modulos no encontrados (probablemente faltan en addons.yaml o "
            f"falta `gitaggregate`): {missing}."
        )
    if already:
        print(
            f"warning: ya instalados, se omiten: {already}",
            file=sys.stderr,
        )
    if not to_install:
        json.dump(
            {"action": "noop", "reason": "all already installed",
             "names": names},
            sys.stdout,
            indent=2,
            ensure_ascii=False,
        )
        print()
        return 0

    ssh_result = install_via_ssh(to_install, ns.dry_run, cfg["db_name"])
    if ssh_runner.is_transport_failure(ssh_result):
        raise OdooError(
            f"Fallo SSH al ejecutar el install (exit 255). stderr: "
            f"{ssh_result.stderr.strip()}"
        )
    if not ns.dry_run and ssh_result.returncode != 0:
        raise OdooError(
            f"odoo-bin -i fallo (exit {ssh_result.returncode}). "
            f"stderr (ultimas lineas): {ssh_result.stderr[-2000:]}"
        )

    if not ns.dry_run and not ns.skip_restart:
        ssh_runner.docker_compose_restart(dry_run=False)

    states = (
        {n: "(dry-run)" for n in to_install}
        if ns.dry_run
        else verify_post(client, names)
    )

    json.dump(
        {
            "action": "installed" if not ns.dry_run else "would_install",
            "names_to_install": to_install,
            "already_installed": already,
            "post_states": states,
            "ssh_returncode": ssh_result.returncode,
            "cmd": " ".join(ssh_result.cmd),
        },
        sys.stdout,
        indent=2,
        ensure_ascii=False,
    )
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
