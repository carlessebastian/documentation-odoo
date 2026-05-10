#!/usr/bin/env python3
"""Actualiza modulo(s) ya instalados via SSH + docker compose run.

Uso:
    python3 module_upgrade.py --names l10n_es,l10n_es_aeat_mod303
    python3 module_upgrade.py --all-installed --dry-run    # equivalente a -u all
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

import ssh_runner
from _common import OdooError
from odoo_client import OdooClient


def list_installed(client: OdooClient) -> list[str]:
    rows = client.call(
        "ir.module.module",
        "search_read",
        [[("state", "=", "installed")]],
        {"fields": ["name"]},
    )
    return [r["name"] for r in rows]


def precheck(client: OdooClient, names: Sequence[str]) -> list[str]:
    rows = client.call(
        "ir.module.module",
        "search_read",
        [[("name", "in", list(names))]],
        {"fields": ["name", "state"]},
    )
    by_name = {r["name"]: r["state"] for r in rows}
    not_installed = [
        n for n in names if by_name.get(n) != "installed"
    ]
    if not_installed:
        raise OdooError(
            f"No instalados (no se pueden upgradear): {not_installed}. "
            "Para instalarlos, usa module_install.py."
        )
    return list(names)


def upgrade_via_ssh(
    names: Sequence[str], dry_run: bool, db_name: str, all_installed: bool
) -> ssh_runner.SshResult:
    target = "all" if all_installed else ",".join(names)
    odoo_args = [
        "odoo",
        "--stop-after-init",
        "--no-http",
        "-d",
        db_name,
        "-u",
        target,
        "--logfile=/dev/stderr",
    ]
    return ssh_runner.docker_compose_run(odoo_args, dry_run=dry_run, timeout=7200)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--names", help="CSV de modulos a actualizar.")
    grp.add_argument(
        "--all-installed",
        action="store_true",
        help="Equivalente a `odoo -u all` sobre los instalados.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-restart", action="store_true")
    ns = parser.parse_args()

    client = OdooClient()
    cfg = ssh_runner.get_ssh_config()
    if not cfg["db_name"]:
        raise OdooError("DOODBA_DB_NAME / ODOO_DB no esta seteado.")

    if ns.all_installed:
        names = list_installed(client)
        if not names:
            raise OdooError("Ningun modulo instalado.")
    else:
        names = [n.strip() for n in ns.names.split(",") if n.strip()]
        if not names:
            raise OdooError("--names vacio.")
        precheck(client, names)

    ssh_result = upgrade_via_ssh(
        names, ns.dry_run, cfg["db_name"], ns.all_installed
    )
    if ssh_runner.is_transport_failure(ssh_result):
        raise OdooError(
            f"Fallo SSH (exit 255). stderr: {ssh_result.stderr.strip()}"
        )
    if not ns.dry_run and ssh_result.returncode != 0:
        raise OdooError(
            f"odoo-bin -u fallo (exit {ssh_result.returncode}). "
            f"stderr (ultimas lineas): {ssh_result.stderr[-2000:]}"
        )

    if not ns.dry_run and not ns.skip_restart:
        ssh_runner.docker_compose_restart(dry_run=False)

    json.dump(
        {
            "action": "upgraded" if not ns.dry_run else "would_upgrade",
            "target": "all" if ns.all_installed else "named",
            "names": names if not ns.all_installed else f"{len(names)} modulos",
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
