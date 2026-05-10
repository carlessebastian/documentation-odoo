#!/usr/bin/env python3
"""Lista, pausa, reanuda o ejecuta `ir.cron` jobs.

Uso:
    python3 cron_manage.py list
    python3 cron_manage.py pause --id 42
    python3 cron_manage.py resume --id 42
    python3 cron_manage.py run --id 42
"""
from __future__ import annotations

import argparse
import json
import sys

from _common import OdooError
from odoo_client import OdooClient


def cmd_list(client: OdooClient) -> list[dict]:
    return client.call(
        "ir.cron",
        "search_read",
        [[]],
        {
            "fields": [
                "id",
                "cron_name",
                "model_id",
                "interval_number",
                "interval_type",
                "nextcall",
                "lastcall",
                "active",
                "numbercall",
                "user_id",
            ],
            "order": "active desc, cron_name",
        },
    )


def cmd_pause(client: OdooClient, cron_id: int) -> None:
    client.call("ir.cron", "write", [[cron_id], {"active": False}])


def cmd_resume(client: OdooClient, cron_id: int) -> None:
    client.call("ir.cron", "write", [[cron_id], {"active": True}])


def cmd_run(client: OdooClient, cron_id: int) -> None:
    client.call("ir.cron", "method_direct_trigger", [[cron_id]])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("list", "pause", "resume", "run"))
    parser.add_argument("--id", dest="cron_id", type=int)
    ns = parser.parse_args()

    if ns.action != "list" and not ns.cron_id:
        raise OdooError(f"--id es obligatorio para '{ns.action}'.")

    client = OdooClient()
    if ns.action == "list":
        result: object = cmd_list(client)
    elif ns.action == "pause":
        cmd_pause(client, ns.cron_id)
        result = {"id": ns.cron_id, "action": "paused"}
    elif ns.action == "resume":
        cmd_resume(client, ns.cron_id)
        result = {"id": ns.cron_id, "action": "resumed"}
    else:  # run
        cmd_run(client, ns.cron_id)
        result = {"id": ns.cron_id, "action": "triggered"}

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False, default=str)
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
