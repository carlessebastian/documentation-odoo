"""Wrapper alrededor de `ssh <host> <cmd>` con --dry-run y exit-code parsing.

NO ejecuta `ssh` automaticamente sin pasarse por `run()`; los tests
mockean `subprocess.run`.
"""
from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from typing import Sequence

from _common import OdooEnvError


@dataclass
class SshResult:
    returncode: int
    stdout: str
    stderr: str
    cmd: list[str]


SSH_TRANSPORT_FAILURE = 255


def get_ssh_config() -> dict[str, str]:
    """Lee config SSH del entorno; aborta si falta DOODBA_SSH_HOST."""
    host = os.environ.get("DOODBA_SSH_HOST")
    if not host:
        raise OdooEnvError(
            "DOODBA_SSH_HOST no esta seteado. Sin SSH no se pueden hacer "
            "operaciones de install/upgrade. Setea DOODBA_SSH_HOST y, si "
            "quieres, DOODBA_PROJECT_DIR y DOODBA_COMPOSE_SERVICE."
        )
    return {
        "host": host,
        "project_dir": os.environ.get("DOODBA_PROJECT_DIR", "/opt/doodba"),
        "compose_service": os.environ.get("DOODBA_COMPOSE_SERVICE", "odoo"),
        "db_name": os.environ.get(
            "DOODBA_DB_NAME", os.environ.get("ODOO_DB", "")
        ),
    }


def build_ssh_cmd(host: str, remote_cmd: str, *, ssh_extra: Sequence[str] = ()) -> list[str]:
    """Construye una lista de args para subprocess.run(['ssh', host, cmd])."""
    base = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "BatchMode=yes"]
    base.extend(ssh_extra)
    base.extend([host, remote_cmd])
    return base


def quote_remote(parts: Sequence[str]) -> str:
    """Une comandos remotos en una sola cadena con shell quoting."""
    return " ".join(shlex.quote(p) for p in parts)


def run(
    remote_cmd: str,
    *,
    dry_run: bool = False,
    timeout: int = 1800,
    ssh_extra: Sequence[str] = (),
) -> SshResult:
    """Ejecuta el comando remoto via SSH.

    Si `dry_run=True`, no llama a subprocess; solo construye la cmd y la
    devuelve con returncode=0.
    """
    cfg = get_ssh_config()
    cmd = build_ssh_cmd(cfg["host"], remote_cmd, ssh_extra=ssh_extra)
    if dry_run:
        return SshResult(
            returncode=0,
            stdout=f"DRY RUN: {' '.join(shlex.quote(c) for c in cmd)}\n",
            stderr="",
            cmd=cmd,
        )
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return SshResult(
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        cmd=cmd,
    )


def is_transport_failure(result: SshResult) -> bool:
    """SSH no llego a ejecutar el comando remoto (network, auth, host_unreachable)."""
    return result.returncode == SSH_TRANSPORT_FAILURE


def docker_compose_run(
    cmd_parts: Sequence[str],
    *,
    dry_run: bool = False,
    extra_compose_args: Sequence[str] = (),
    timeout: int = 1800,
) -> SshResult:
    """`docker compose run --rm -T <service> <cmd_parts>` via SSH.

    Wrapper canonico para `odoo --stop-after-init ...`.
    """
    cfg = get_ssh_config()
    extras = " ".join(shlex.quote(e) for e in extra_compose_args)
    extras_part = f"{extras} " if extras else ""
    inner = quote_remote(cmd_parts)
    remote = (
        f"cd {shlex.quote(cfg['project_dir'])} && "
        f"docker compose run --rm -T {extras_part}{shlex.quote(cfg['compose_service'])} "
        f"{inner}"
    )
    return run(remote, dry_run=dry_run, timeout=timeout)


def docker_compose_restart(*, dry_run: bool = False) -> SshResult:
    """`docker compose restart <service>` via SSH."""
    cfg = get_ssh_config()
    remote = (
        f"cd {shlex.quote(cfg['project_dir'])} && "
        f"docker compose restart {shlex.quote(cfg['compose_service'])}"
    )
    return run(remote, dry_run=dry_run, timeout=120)
