#!/usr/bin/env python3
"""Cliente Odoo unificado: usa JSON-2 (Odoo 19+) o XML-RPC como fallback.

Variables de entorno requeridas:
    ODOO_URL, ODOO_DB, ODOO_API_KEY
    ODOO_USER (solo necesario para XML-RPC)
    ODOO_FORCE_XMLRPC=1 (opcional, fuerza XML-RPC)
"""
from __future__ import annotations

import json
import os
import sys
import xmlrpc.client
from typing import Any

import requests

from _common import OdooError, require_env, retry_on_network


class OdooClient:
    def __init__(self) -> None:
        env = require_env("ODOO_URL", "ODOO_DB", "ODOO_API_KEY")
        self.url = env["ODOO_URL"].rstrip("/")
        self.db = env["ODOO_DB"]
        self.key = env["ODOO_API_KEY"]
        self.user = os.environ.get("ODOO_USER")

        self.version = self._detect_version()
        force_xml = os.environ.get("ODOO_FORCE_XMLRPC") == "1"
        self.mode = "xmlrpc" if (force_xml or self.version < 19) else "json2"

        if self.mode == "xmlrpc":
            self._xmlrpc_login()

    def _detect_version(self) -> int:
        # /web/version es publico en versiones recientes; si falla, caer a XML-RPC.
        try:
            r = requests.get(f"{self.url}/web/version", timeout=10)
            if r.status_code == 200:
                info = r.json()
                vi = info.get("version_info") or info.get("server_version_info")
                if vi:
                    return int(vi[0])
        except (requests.RequestException, ValueError):
            pass
        common = xmlrpc.client.ServerProxy(
            f"{self.url}/xmlrpc/2/common", allow_none=True
        )
        return int(common.version()["server_version_info"][0])

    def _xmlrpc_login(self) -> None:
        if not self.user:
            raise OdooError(
                "ODOO_USER es obligatorio para autenticacion XML-RPC."
            )
        common = xmlrpc.client.ServerProxy(
            f"{self.url}/xmlrpc/2/common", allow_none=True
        )
        uid = common.authenticate(self.db, self.user, self.key, {})
        if not uid:
            raise OdooError("Autenticacion Odoo XML-RPC fallida.")
        self.uid = uid
        self.models = xmlrpc.client.ServerProxy(
            f"{self.url}/xmlrpc/2/object", allow_none=True
        )

    def call(
        self,
        model: str,
        method: str,
        args: list | None = None,
        kwargs: dict | None = None,
    ) -> Any:
        args = args or []
        kwargs = kwargs or {}
        if self.mode == "json2":
            return retry_on_network(lambda: self._json2(model, method, args, kwargs))
        return retry_on_network(
            lambda: self._xmlrpc(model, method, args, kwargs)
        )

    def _xmlrpc(self, model: str, method: str, args: list, kwargs: dict) -> Any:
        try:
            return self.models.execute_kw(
                self.db, self.uid, self.key, model, method, args, kwargs
            )
        except xmlrpc.client.Fault as e:
            raise OdooError(_clean_fault(e.faultString)) from e

    def _json2(self, model: str, method: str, args: list, kwargs: dict) -> Any:
        body: dict = dict(kwargs)
        if args:
            body["args"] = args
        r = requests.post(
            f"{self.url}/json/2/{model}/{method}",
            headers={
                "Authorization": f"bearer {self.key}",
                "Content-Type": "application/json",
                "X-Odoo-Database": self.db,
            },
            json=body,
            timeout=60,
        )
        if r.status_code >= 400:
            try:
                payload = r.json()
                msg = (
                    payload.get("error", {})
                    .get("data", {})
                    .get("message")
                    or payload.get("error", {}).get("message")
                    or r.text
                )
            except ValueError:
                msg = r.text
            raise OdooError(f"HTTP {r.status_code}: {_clean_fault(msg)}")
        return r.json()

    # ---------- conveniencias ----------

    def search_read(
        self,
        model: str,
        domain: list,
        fields: list[str] | None = None,
        limit: int = 80,
        offset: int = 0,
        order: str | None = None,
        ctx: dict | None = None,
    ) -> list[dict]:
        kw: dict = {"fields": fields or [], "limit": limit, "offset": offset}
        if order:
            kw["order"] = order
        if ctx:
            kw["context"] = ctx
        return self.call(model, "search_read", [domain], kw)

    def search_count(self, model: str, domain: list, ctx: dict | None = None) -> int:
        kw: dict = {}
        if ctx:
            kw["context"] = ctx
        return self.call(model, "search_count", [domain], kw)

    def read(
        self,
        model: str,
        ids: list[int],
        fields: list[str] | None = None,
        ctx: dict | None = None,
    ) -> list[dict]:
        kw: dict = {"fields": fields or []}
        if ctx:
            kw["context"] = ctx
        return self.call(model, "read", [ids], kw)

    def create(self, model: str, vals: dict, ctx: dict | None = None) -> int:
        kw: dict = {}
        if ctx:
            kw["context"] = ctx
        return self.call(model, "create", [vals], kw)

    def write(
        self, model: str, ids: list[int], vals: dict, ctx: dict | None = None
    ) -> bool:
        kw: dict = {}
        if ctx:
            kw["context"] = ctx
        return self.call(model, "write", [ids, vals], kw)

    def unlink(self, model: str, ids: list[int]) -> bool:
        return self.call(model, "unlink", [ids])

    def action(
        self,
        model: str,
        ids: list[int],
        method: str,
        ctx: dict | None = None,
    ) -> Any:
        kw: dict = {}
        if ctx:
            kw["context"] = ctx
        return self.call(model, method, [ids], kw)


def _clean_fault(text: str) -> str:
    """Extrae el mensaje de negocio de un Fault.faultString largo."""
    if not text:
        return ""
    # XML-RPC suele devolver "TipoError\n\nMensaje\n\nTraceback..."
    parts = text.split("\n\n")
    if len(parts) >= 2:
        return parts[1].strip()
    return text.strip()


def _cli() -> None:
    """CLI minimo: `odoo_client.py search_read account.move '[]' '["id","name"]' 5`."""
    import argparse

    parser = argparse.ArgumentParser(description="Cliente Odoo CLI")
    parser.add_argument("method", help="search_read | read | create | write | call")
    parser.add_argument("model", help="Nombre del modelo, p.ej. account.move")
    parser.add_argument("args", nargs="*", help="Argumentos JSON-encoded")
    ns = parser.parse_args()

    c = OdooClient()
    parsed_args = [json.loads(a) for a in ns.args]
    if ns.method == "search_read":
        domain = parsed_args[0] if parsed_args else []
        fields = parsed_args[1] if len(parsed_args) > 1 else None
        limit = parsed_args[2] if len(parsed_args) > 2 else 80
        result = c.search_read(ns.model, domain, fields, limit=limit)
    elif ns.method == "create":
        result = c.create(ns.model, parsed_args[0])
    elif ns.method == "write":
        result = c.write(ns.model, parsed_args[0], parsed_args[1])
    elif ns.method == "read":
        result = c.read(ns.model, parsed_args[0], parsed_args[1] if len(parsed_args) > 1 else None)
    else:
        result = c.call(
            ns.model, ns.method,
            parsed_args[0] if parsed_args else [],
            parsed_args[1] if len(parsed_args) > 1 else {},
        )
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False, default=str)
    print()


if __name__ == "__main__":
    try:
        _cli()
    except OdooError as e:
        print(f"OdooError: {e}", file=sys.stderr)
        sys.exit(2)
