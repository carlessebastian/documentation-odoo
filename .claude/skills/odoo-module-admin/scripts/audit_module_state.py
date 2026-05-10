#!/usr/bin/env python3
"""Snapshot completo del estado de modulos. Solo lectura.

Uso:
    python3 audit_module_state.py > pre-upgrade.json
    python3 audit_module_state.py --installed-only
"""
from __future__ import annotations

import argparse
import json
import sys

from _common import OdooError
from odoo_client import OdooClient


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-only", action="store_true")
    parser.add_argument(
        "--state",
        choices=("installed", "uninstalled", "to install", "to upgrade",
                 "to remove", "uninstallable"),
        help="Filtra por state.",
    )
    ns = parser.parse_args()

    client = OdooClient()
    domain: list = []
    if ns.installed_only:
        domain.append(("state", "=", "installed"))
    elif ns.state:
        domain.append(("state", "=", ns.state))

    rows = client.call(
        "ir.module.module",
        "search_read",
        [domain],
        {
            "fields": [
                "id",
                "name",
                "shortdesc",
                "state",
                "latest_version",
                "installed_version",
                "author",
                "license",
                "category_id",
            ],
            "order": "state, name",
        },
    )
    json.dump(rows, sys.stdout, indent=2, ensure_ascii=False, default=str)
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
