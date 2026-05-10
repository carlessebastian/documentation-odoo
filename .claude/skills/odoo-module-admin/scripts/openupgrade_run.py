#!/usr/bin/env python3
"""Orquesta un upgrade major version usando OpenUpgrade en doodba.

Flujo:
1. Verifica que existe un clone de OpenUpgrade en el host (`OPENUPGRADE_PATH`).
2. Comprueba que la rama del clone es la version destino (`--to`).
3. Crea un dump de la DB origen.
4. Restaura el dump en una DB de staging (`<src_db>_upg_<timestamp>`).
5. Invoca `odoo-bin --upgrade-path=...` con `--update all --stop-after-init`.
6. Reporta resultados.

NUNCA toca la DB de produccion. El usuario debe revisar la DB staging y,
solo cuando todo este OK, hacer el cutover manual (ver
references/upgrade-strategy.md).

Uso:
    python3 openupgrade_run.py --src-db prod --to 19.0 --confirm
    python3 openupgrade_run.py --src-db prod --to 19.0    # plan
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

import ssh_runner
from _common import OdooError


def get_openupgrade_path() -> str:
    p = os.environ.get("OPENUPGRADE_PATH")
    if not p:
        raise OdooError(
            "OPENUPGRADE_PATH no esta seteado. Apuntalo a un clone de "
            "https://github.com/OCA/OpenUpgrade.git en el host doodba "
            "(p.ej. /opt/openupgrade)."
        )
    return p


def verify_branch(path: str, expected_branch: str, dry_run: bool) -> str:
    """Lee el branch remoto del clone OpenUpgrade. dry_run=True salta la verificacion."""
    if dry_run:
        return "(dry-run)"
    cmd = f"git -C {path} branch --show-current"
    r = ssh_runner.run(cmd, dry_run=False, timeout=30)
    if ssh_runner.is_transport_failure(r):
        raise OdooError(f"SSH fallo: {r.stderr}")
    if r.returncode != 0:
        raise OdooError(
            f"git branch fallo en {path}: {r.stderr.strip()}. "
            "Verifica que OPENUPGRADE_PATH es un clone valido."
        )
    actual = r.stdout.strip()
    if actual != expected_branch:
        raise OdooError(
            f"OpenUpgrade en {path} esta en rama {actual!r}, esperada "
            f"{expected_branch!r}. Haz `git fetch && git checkout {expected_branch}` "
            "antes de continuar."
        )
    return actual


def dump_db(
    src_db: str, dump_path: str, dry_run: bool
) -> ssh_runner.SshResult:
    cfg = ssh_runner.get_ssh_config()
    cmd = (
        f"cd {cfg['project_dir']} && "
        f"docker compose exec -T db pg_dump -U odoo -Fc -f {dump_path} {src_db}"
    )
    return ssh_runner.run(cmd, dry_run=dry_run, timeout=1800)


def restore_db(
    dst_db: str, dump_path: str, dry_run: bool
) -> ssh_runner.SshResult:
    cfg = ssh_runner.get_ssh_config()
    cmd = (
        f"cd {cfg['project_dir']} && "
        f"docker compose exec -T db createdb -U odoo {dst_db} && "
        f"docker compose exec -T db pg_restore -U odoo -d {dst_db} {dump_path}"
    )
    return ssh_runner.run(cmd, dry_run=dry_run, timeout=1800)


def run_openupgrade(
    dst_db: str, openupgrade_path: str, dry_run: bool
) -> ssh_runner.SshResult:
    odoo_args = [
        "odoo",
        "--stop-after-init",
        "--no-http",
        "-d",
        dst_db,
        "--update=all",
        f"--upgrade-path={openupgrade_path}/openupgrade_scripts/scripts",
        "--load=base,web,openupgrade_framework",
        "--logfile=/dev/stderr",
    ]
    return ssh_runner.docker_compose_run(
        odoo_args,
        dry_run=dry_run,
        timeout=14400,
        extra_compose_args=(f"-v", f"{openupgrade_path}:/openupgrade:ro"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src-db", required=True)
    parser.add_argument("--to", required=True, help="Version destino (p.ej. 19.0)")
    parser.add_argument(
        "--dst-db",
        help="DB destino (default: <src_db>_upg_<YYYYMMDDhhmm>).",
    )
    parser.add_argument(
        "--dump-path",
        default="/tmp/openupgrade_dump.pgdump",
        help="Path remoto del dump intermedio.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Sin esto, dry-run.",
    )
    ns = parser.parse_args()

    openupgrade_path = get_openupgrade_path()
    dst_db = ns.dst_db or (
        f"{ns.src_db}_upg_{dt.datetime.now().strftime('%Y%m%d%H%M')}"
    )
    dry = not ns.confirm

    plan = {
        "src_db": ns.src_db,
        "dst_db": dst_db,
        "to_version": ns.to,
        "openupgrade_path": openupgrade_path,
        "dump_path": ns.dump_path,
        "mode": "DRY_RUN" if dry else "EXECUTE",
        "steps": [],
    }

    # Step 1: verify branch
    branch = verify_branch(openupgrade_path, ns.to, dry)
    plan["steps"].append({"step": "verify_branch", "result": branch})

    # Step 2: dump
    r = dump_db(ns.src_db, ns.dump_path, dry)
    plan["steps"].append(
        {"step": "dump_db", "rc": r.returncode, "tail": r.stderr[-200:]}
    )
    if not dry and r.returncode != 0:
        plan["status"] = "failed_at_dump"
        json.dump(plan, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return 1

    # Step 3: restore (creates dst_db)
    r = restore_db(dst_db, ns.dump_path, dry)
    plan["steps"].append(
        {"step": "restore_db", "rc": r.returncode, "tail": r.stderr[-200:]}
    )
    if not dry and r.returncode != 0:
        plan["status"] = "failed_at_restore"
        json.dump(plan, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return 1

    # Step 4: openupgrade
    r = run_openupgrade(dst_db, openupgrade_path, dry)
    plan["steps"].append(
        {
            "step": "openupgrade",
            "rc": r.returncode,
            "stdout_tail": r.stdout[-500:],
            "stderr_tail": r.stderr[-500:],
        }
    )
    if not dry and r.returncode != 0:
        plan["status"] = "failed_at_upgrade"
        plan["recovery"] = (
            f"Inspeccionar la DB staging {dst_db} y los logs del paso "
            "openupgrade para iterar. La DB origen NO se ha tocado."
        )
        json.dump(plan, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return 1

    plan["status"] = "ok" if not dry else "would_run"
    plan["next_step"] = (
        f"Verifica la DB staging {dst_db} (login, smoke tests). "
        "Cuando este OK, planifica un cutover manual: parar Odoo, "
        "renombrar DBs (rename src_db -> backup, dst -> src_db) y reiniciar."
    )
    json.dump(plan, sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
