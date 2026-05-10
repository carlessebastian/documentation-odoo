"""Helper para detectar modulos cuyo codigo cambio desde el ultimo upgrade.

Implementacion:
1. Por SSH, computa SHA256 de los .py + .xml + __manifest__.py de cada
   modulo bajo `auto/addons/`.
2. Compara el checksum actual contra el guardado en
   `ir.config_parameter` clave `__custom__.module_checksums` (JSON).
3. Devuelve la lista de modulos cuyo checksum cambio.
4. Tras un upgrade exitoso, llama `save_checksums` para persistir el
   nuevo estado.

Inspirado en `click-odoo-update` de ACSONE; reimplementado aqui sin
anyadir dependencia externa.
"""
from __future__ import annotations

import json
from typing import Iterable

import ssh_runner
from _common import OdooError
from odoo_client import OdooClient


CHECKSUM_PARAM_KEY = "__custom__.module_checksums"


def compute_remote_checksums() -> dict[str, str]:
    """Devuelve {module_name: sha256} ejecutando find+sha256sum via SSH.

    Asume que `auto/addons/<modulo>/` contiene los modulos activos en doodba.
    Concatena hashes de cada `*.py` y `*.xml` del modulo en un orden estable.
    """
    cfg = ssh_runner.get_ssh_config()
    # Script remoto: para cada subcarpeta de auto/addons que tenga
    # __manifest__.py, computa el sha256 de la lista ordenada de hashes
    # de sus *.py y *.xml.
    remote_cmd = (
        f"cd {cfg['project_dir']}/odoo/auto/addons 2>/dev/null && "
        "for d in */; do "
        "  m=\"${d%/}\"; "
        "  [ -f \"$d/__manifest__.py\" ] || continue; "
        "  h=$(find \"$d\" -type f \\( -name '*.py' -o -name '*.xml' "
        "      -o -name '*.csv' \\) -print0 | sort -z | "
        "      xargs -0 sha256sum 2>/dev/null | sha256sum | cut -d' ' -f1); "
        "  echo \"$m $h\"; "
        "done"
    )
    result = ssh_runner.run(remote_cmd, dry_run=False, timeout=300)
    if ssh_runner.is_transport_failure(result):
        raise OdooError(f"SSH fallo en compute_remote_checksums: {result.stderr}")
    if result.returncode != 0:
        raise OdooError(
            f"find/sha256sum remoto fallo (rc={result.returncode}): "
            f"{result.stderr[-500:]}"
        )
    return parse_checksum_output(result.stdout)


def parse_checksum_output(text: str) -> dict[str, str]:
    """Parsea lineas '<module> <sha>' en dict. Ignora vacias / mal formadas."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2:
            continue
        module, sha = parts
        if len(sha) != 64:
            continue
        out[module] = sha
    return out


def load_stored_checksums(client: OdooClient) -> dict[str, str]:
    rec = client.call(
        "ir.config_parameter",
        "search_read",
        [[("key", "=", CHECKSUM_PARAM_KEY)]],
        {"fields": ["value"], "limit": 1},
    )
    if not rec:
        return {}
    try:
        data = json.loads(rec[0]["value"] or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def save_checksums(client: OdooClient, checksums: dict[str, str]) -> None:
    value = json.dumps(checksums, sort_keys=True)
    existing = client.call(
        "ir.config_parameter",
        "search",
        [[("key", "=", CHECKSUM_PARAM_KEY)]],
        {"limit": 1},
    )
    if existing:
        client.call(
            "ir.config_parameter",
            "write",
            [[existing[0]], {"value": value}],
        )
    else:
        client.call(
            "ir.config_parameter",
            "create",
            [{"key": CHECKSUM_PARAM_KEY, "value": value}],
        )


def diff_checksums(
    current: dict[str, str], stored: dict[str, str], installed: Iterable[str]
) -> dict[str, list[str]]:
    """Devuelve {'changed': [...], 'new': [...], 'gone': [...]}."""
    installed_set = set(installed)
    changed: list[str] = []
    new: list[str] = []
    for m, sha in current.items():
        if m not in installed_set:
            continue  # solo nos interesa lo instalado para upgrade
        if m not in stored:
            new.append(m)
        elif stored[m] != sha:
            changed.append(m)
    gone = sorted(set(stored) - set(current))
    return {
        "changed": sorted(changed),
        "new": sorted(new),
        "gone": gone,
    }
