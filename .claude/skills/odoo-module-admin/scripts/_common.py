"""Helpers comunes a todos los scripts del skill odoo-accounting-es."""
from __future__ import annotations

import os
import sys
import time


class OdooError(Exception):
    """Error de negocio devuelto por Odoo (UserError, ValidationError, etc.)."""


class OdooEnvError(Exception):
    """Variable de entorno requerida ausente."""


def require_env(*names: str) -> dict[str, str]:
    """Devuelve un dict con las env vars pedidas; aborta si falta alguna."""
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        raise OdooEnvError(
            "Faltan variables de entorno: "
            + ", ".join(missing)
            + ". Configurelas antes de ejecutar el script."
        )
    return {n: os.environ[n] for n in names}


def retry_on_network(fn, *, attempts: int = 3, base_delay: float = 1.0):
    """Reintenta `fn()` ante errores de red. NO reintenta errores de negocio."""
    import requests
    import xmlrpc.client

    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except (requests.ConnectionError, requests.Timeout, OSError) as exc:
            last_exc = exc
        except xmlrpc.client.ProtocolError as exc:
            if exc.errcode >= 500:
                last_exc = exc
            else:
                raise
        time.sleep(base_delay * (2 ** i))
    assert last_exc is not None
    raise last_exc


def format_amount(value: float, currency: str = "EUR") -> str:
    return f"{value:,.2f} {currency}"


def die(message: str, code: int = 1) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)
