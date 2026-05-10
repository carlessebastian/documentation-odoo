#!/usr/bin/env python3
"""Desinstala modulo(s). PIDE --confirm explicitamente antes de tocar.

Flujo:
1. Comprueba dependientes instalados; si hay, listalos y aborta sin --cascade.
2. Lista modelos definidos por el modulo (datos que se perderan).
3. Sin --confirm: solo imprime el plan.
4. Con --confirm: SSH -> docker compose run --rm -T odoo odoo
   --stop-after-init -d <db> con `button_immediate_uninstall` via shell.

Uso:
    python3 module_uninstall.py --names X            # plan
    python3 module_uninstall.py --names X --confirm  # ejecuta
    python3 module_uninstall.py --names X --confirm --cascade
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

import ssh_runner
from _common import OdooError
from odoo_client import OdooClient


def collect_rdeps(
    client: OdooClient, names: Sequence[str]
) -> dict[str, list[str]]:
    rows = client.call(
        "ir.module.module.dependency",
        "search_read",
        [[("name", "in", list(names))]],
        {"fields": ["name", "module_id"]},
    )
    out: dict[str, list[str]] = {n: [] for n in names}
    if not rows:
        return out
    module_ids = sorted({r["module_id"][0] for r in rows})
    modules = client.call("ir.module.module", "read", [module_ids, ["name", "state"]])
    by_id = {m["id"]: m for m in modules}
    for r in rows:
        m = by_id.get(r["module_id"][0])
        if m and m["state"] == "installed":
            out[r["name"]].append(m["name"])
    return out


def list_module_models(client: OdooClient, names: Sequence[str]) -> dict[str, list[str]]:
    rows = client.call(
        "ir.model.data",
        "search_read",
        [[("module", "in", list(names)), ("model", "=", "ir.model")]],
        {"fields": ["module", "res_id"]},
    )
    if not rows:
        return {n: [] for n in names}
    model_ids = sorted({r["res_id"] for r in rows})
    models = client.call("ir.model", "read", [model_ids, ["model"]])
    by_id = {m["id"]: m["model"] for m in models}
    out: dict[str, list[str]] = {n: [] for n in names}
    for r in rows:
        m = by_id.get(r["res_id"])
        if m:
            out[r["module"]].append(m)
    return {k: sorted(v) for k, v in out.items()}


def uninstall_via_ssh(
    names: Sequence[str], db_name: str
) -> ssh_runner.SshResult:
    """Usa `odoo shell` con un script Python que llama button_immediate_uninstall."""
    py = (
        "modules = env['ir.module.module'].search([('name','in',"
        + repr(list(names))
        + "),('state','=','installed')]); "
        "modules.button_immediate_uninstall(); env.cr.commit()"
    )
    odoo_args = [
        "odoo",
        "shell",
        "--stop-after-init",
        "--no-http",
        "-d",
        db_name,
        "-c",
        py,
    ]
    return ssh_runner.docker_compose_run(odoo_args, dry_run=False, timeout=1800)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--names", required=True, help="CSV de modulos.")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirma la desinstalacion (sin esto, solo plan).",
    )
    parser.add_argument(
        "--cascade",
        action="store_true",
        help="Permite desinstalar aunque haya modulos dependientes instalados.",
    )
    ns = parser.parse_args()

    names = [n.strip() for n in ns.names.split(",") if n.strip()]
    if not names:
        raise OdooError("--names vacio.")

    client = OdooClient()
    rdeps = collect_rdeps(client, names)
    has_blockers = any(rdeps[n] for n in names)
    models = list_module_models(client, names)

    plan = {
        "names": names,
        "reverse_dependencies_installed": rdeps,
        "models_defined_by_module": models,
        "data_loss_warning": (
            "Se borraran registros de los modelos definidos arriba. "
            "Datos en modelos estandar (account.move, res.partner) sobreviven, "
            "pero columnas custom anyadidas por estos modulos NO."
        ),
    }

    if has_blockers and not ns.cascade:
        plan["status"] = "blocked"
        plan["error"] = (
            "Hay modulos instalados que dependen de los que quieres "
            "desinstalar. Pasa --cascade si aceptas que tambien se "
            "desinstalen, o desinstala primero los dependientes."
        )
        json.dump(plan, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return 3

    if not ns.confirm:
        plan["status"] = "dry_run"
        plan["next_step"] = "Re-ejecutar con --confirm para aplicar."
        json.dump(plan, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return 0

    cfg = ssh_runner.get_ssh_config()
    if not cfg["db_name"]:
        raise OdooError("DOODBA_DB_NAME / ODOO_DB no esta seteado.")

    ssh_result = uninstall_via_ssh(names, cfg["db_name"])
    if ssh_runner.is_transport_failure(ssh_result):
        raise OdooError(
            f"SSH fallo (exit 255). stderr: {ssh_result.stderr.strip()}"
        )
    if ssh_result.returncode != 0:
        raise OdooError(
            f"button_immediate_uninstall fallo (exit "
            f"{ssh_result.returncode}). stderr (ultimas lineas): "
            f"{ssh_result.stderr[-2000:]}"
        )

    ssh_runner.docker_compose_restart(dry_run=False)
    plan["status"] = "uninstalled"
    plan["ssh_returncode"] = ssh_result.returncode
    json.dump(plan, sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
