#!/usr/bin/env python3
"""Crea una `ir.rule` con validacion previa.

Idempotente sobre `(model_id, name)`: si ya existe, hace `write()`.

Uso:
    # Comerciales solo ven sus oportunidades
    python3 record_rule_create.py \\
        --name "Salesperson sees only own leads" \\
        --model crm.lead \\
        --groups sales_team.group_sale_salesman \\
        --domain "[('user_id','=',user.id)]" \\
        --perms r,w,c

    # Multi-company global rule (sin grupos = no by-passable)
    python3 record_rule_create.py \\
        --name "res.partner: company" \\
        --model res.partner \\
        --groups "" \\
        --domain "['|', ('company_id','=',False), ('company_id','in',company_ids)]"
"""
from __future__ import annotations

import argparse
import ast
import json
import sys

from _common import OdooError
from odoo_client import OdooClient


HIGH_RISK_MODELS = {
    "res.users",
    "res.company",
    "ir.rule",
    "ir.model.access",
    "ir.model",
    "ir.module.module",
}


def parse_perms(spec: str) -> dict[str, bool]:
    """`r,w,c,u` -> dict; sin `u` significa perm_unlink=False."""
    flags = {p.strip().lower() for p in spec.split(",") if p.strip()}
    valid = {"r", "w", "c", "u"}
    bad = flags - valid
    if bad:
        raise OdooError(
            f"Permisos invalidos: {bad}. Usa subset de r,w,c,u."
        )
    return {
        "perm_read": "r" in flags,
        "perm_write": "w" in flags,
        "perm_create": "c" in flags,
        "perm_unlink": "u" in flags,
    }


def validate_domain_syntax(domain: str) -> None:
    """Valida que `domain` evalua a una lista de tuplas/operadores."""
    try:
        node = ast.parse(domain, mode="eval")
    except SyntaxError as exc:
        raise OdooError(f"Domain con SyntaxError: {exc.msg}")
    # Permitimos identificadores libres (user, company_ids, time) que
    # Odoo evalua en runtime; aqui solo comprobamos que es Python valido
    # y que el AST top-level es una lista.
    if not isinstance(node.body, ast.List):
        raise OdooError(
            "El domain debe ser una lista (top-level). "
            "Ejemplo: [('field','=',value)]"
        )


def resolve_model_id(client: OdooClient, model: str) -> int:
    rec = client.call(
        "ir.model",
        "search",
        [[("model", "=", model)]],
        {"limit": 1},
    )
    if not rec:
        raise OdooError(f"Modelo {model!r} no existe en ir.model.")
    return rec[0]


def resolve_groups(client: OdooClient, group_xmlids: list[str]) -> list[int]:
    if not group_xmlids:
        return []
    ids: list[int] = []
    for xmlid in group_xmlids:
        if "." not in xmlid:
            raise OdooError(f"Group XML-ID invalido: {xmlid!r}")
        module, name = xmlid.split(".", 1)
        rec = client.call(
            "ir.model.data",
            "search_read",
            [
                [
                    ("module", "=", module),
                    ("name", "=", name),
                    ("model", "=", "res.groups"),
                ]
            ],
            {"fields": ["res_id"], "limit": 1},
        )
        if not rec:
            raise OdooError(f"Grupo {xmlid!r} no encontrado.")
        ids.append(rec[0]["res_id"])
    return ids


def upsert_rule(
    client: OdooClient,
    *,
    name: str,
    model_id: int,
    domain_force: str,
    group_ids: list[int],
    perms: dict[str, bool],
) -> tuple[int, str]:
    existing = client.call(
        "ir.rule",
        "search",
        [[("name", "=", name), ("model_id", "=", model_id)]],
        {"limit": 1},
    )
    vals = {
        "name": name,
        "model_id": model_id,
        "domain_force": domain_force,
        "groups": [(6, 0, group_ids)],
        **perms,
        "active": True,
    }
    if existing:
        client.call("ir.rule", "write", [[existing[0]], vals])
        return existing[0], "updated"
    rec_id = client.call("ir.rule", "create", [vals])
    return rec_id, "created"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--groups",
        default="",
        help="CSV de XML-IDs de grupo. Vacio = global rule (no by-passable).",
    )
    parser.add_argument("--domain", required=True, help="Domain Python.")
    parser.add_argument(
        "--perms",
        default="r,w,c",
        help="Subset de r,w,c,u (default r,w,c).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Permite reglas globales sobre modelos high-risk sin confirmacion.",
    )
    ns = parser.parse_args()

    validate_domain_syntax(ns.domain)
    perms = parse_perms(ns.perms)
    group_xmlids = [g.strip() for g in ns.groups.split(",") if g.strip()]

    is_global = not group_xmlids
    if is_global and ns.model in HIGH_RISK_MODELS and not ns.force:
        raise OdooError(
            f"Crear regla GLOBAL sobre modelo high-risk {ns.model!r} "
            "puede ocultar registros a TODOS los usuarios. Pasa --force "
            "para confirmar la intencion."
        )

    client = OdooClient()
    model_id = resolve_model_id(client, ns.model)
    group_ids = resolve_groups(client, group_xmlids)

    rec_id, action = upsert_rule(
        client,
        name=ns.name,
        model_id=model_id,
        domain_force=ns.domain,
        group_ids=group_ids,
        perms=perms,
    )
    json.dump(
        {
            "id": rec_id,
            "action": action,
            "model": ns.model,
            "global_rule": is_global,
            "perms": perms,
            "groups": list(zip(group_xmlids, group_ids)),
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
