#!/usr/bin/env python3
"""HoldedClient: cliente read-only de la API de Holded.

Garantia de read-only
---------------------
La superficie publica solo expone metodos GET. No hay `post`, `put`,
`patch` ni `delete`. La fabrica interna `_request` rechaza cualquier
verbo != GET con `ValueError`. Los paths se validan contra
`ALLOWED_ENDPOINTS` antes de salir a red.

Esto significa que esta skill no puede crear, modificar ni borrar
nada en la cuenta Holded del usuario.

Auth
----
Header `key: <HOLDED_API_KEY>`. Configurada via env var. El cliente
enmascara la clave al loggear cualquier request.

Base URLs
---------
Holded particiona el API en dominios:
- invoicing  -> https://api.holded.com/api/invoicing/v1/...
- accounting -> https://api.holded.com/api/accounting/v1/...
- projects   -> https://api.holded.com/api/projects/v1/...
- crm        -> https://api.holded.com/api/crm/v1/...
- team       -> https://api.holded.com/api/team/v1/...

Rate limiting / retries
-----------------------
Holded no publica limites pero la comunidad reporta 429 esporadicos.
El cliente reintenta sobre 429 y 5xx con backoff exponencial
(1s, 2s, 4s) y respeta el header `Retry-After` cuando viene.

No es asincrono ni multi-proceso a proposito: el dump corre en serie
para evitar disparar 429.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterator

logger = logging.getLogger("holded_client")


# -----------------------------------------------------------------------------
# Configuracion estatica
# -----------------------------------------------------------------------------

DEFAULT_BASE = "https://api.holded.com"
DOMAINS = ("invoicing", "accounting", "projects", "crm", "team")
USER_AGENT = "odoo-agent-holded-export/0.1 (+https://github.com/carlessebastian/odoo-agent)"
TIMEOUT = 30.0
DEFAULT_ATTEMPTS = 3
DEFAULT_BACKOFF = 1.0  # base; multiplicado por 2**i

# -----------------------------------------------------------------------------
# Lista blanca de endpoints
# -----------------------------------------------------------------------------
# Cada entrada es (domain, path_template). Los path_template usan {placeholder}
# para los segmentos variables. El cliente valida el path contra esta lista
# antes de hacer ningun request. Cualquier path no listado lanza ValueError,
# y por construccion solo cubre endpoints GET de lectura.
#
# La lista esta derivada de la doc vendorizada en
# `references/holded-api/`. Si Holded anyade un endpoint nuevo, anyade aqui
# su patron tras vendorizar la doc.

ALLOWED_ENDPOINTS: tuple[tuple[str, str], ...] = (
    # --- Invoicing ---
    ("invoicing", "/contacts"),
    ("invoicing", "/contacts/{contactId}"),
    ("invoicing", "/contacts/groups"),
    ("invoicing", "/products"),
    ("invoicing", "/products/{productId}"),
    ("invoicing", "/services"),
    ("invoicing", "/services/{serviceId}"),
    ("invoicing", "/warehouse"),
    ("invoicing", "/warehouse/{warehouseId}"),
    ("invoicing", "/treasury"),
    ("invoicing", "/treasury/{treasuryId}"),
    ("invoicing", "/expensesaccount"),
    ("invoicing", "/numberingseries/{type}"),
    ("invoicing", "/saleschannels"),
    ("invoicing", "/saleschannels/{salesChannelId}"),
    ("invoicing", "/payments"),
    ("invoicing", "/payments/{paymentId}"),
    ("invoicing", "/remittances"),
    ("invoicing", "/remittances/{remittanceId}"),
    ("invoicing", "/taxes"),
    ("invoicing", "/documents/{docType}"),
    ("invoicing", "/documents/{docType}/{documentId}"),
    ("invoicing", "/documents/{docType}/{documentId}/pdf"),
    # --- Accounting ---
    ("accounting", "/dailyledger"),
    # --- Projects ---
    ("projects", "/projects"),
    ("projects", "/projects/{projectId}"),
    ("projects", "/projects/{projectId}/tasks"),
    ("projects", "/projects/{projectId}/tasks/{taskId}"),
)

# Doc-types validos para documents (los confirmados en list-documents-1.md).
DOC_TYPES = (
    "invoice", "salesreceipt", "creditnote", "salesorder", "proform", "waybill",
    "estimate", "purchase", "purchaseorder", "purchaserefund",
)

# -----------------------------------------------------------------------------
# Errores
# -----------------------------------------------------------------------------

class HoldedError(Exception):
    """Error de API (4xx no recuperable)."""


class HoldedRateLimited(Exception):
    """429 sostenido tras agotar reintentos."""


class HoldedServerError(Exception):
    """5xx tras agotar reintentos."""


class EndpointNotAllowedError(ValueError):
    """Endpoint no esta en la lista blanca; el cliente rechaza el request."""


# -----------------------------------------------------------------------------
# Helpers internos
# -----------------------------------------------------------------------------

def _mask(s: str | None, *, keep: int = 4) -> str:
    if not s:
        return "<missing>"
    if len(s) <= keep * 2:
        return "*" * len(s)
    return f"{s[:keep]}...{s[-keep:]}"


def _normalize_path(path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return path


def _path_matches_template(path: str, template: str) -> bool:
    """Comprueba que `path` (con valores concretos) corresponde a `template`
    (con `{placeholders}`).

    Ejemplo: `/contacts/abc123` matches `/contacts/{contactId}`.
    """
    path_segs = path.strip("/").split("/")
    tpl_segs = template.strip("/").split("/")
    if len(path_segs) != len(tpl_segs):
        return False
    for p, t in zip(path_segs, tpl_segs):
        if t.startswith("{") and t.endswith("}"):
            if not p:
                return False
            continue
        if p != t:
            return False
    return True


def _check_allowed(domain: str, path: str) -> None:
    if domain not in DOMAINS:
        raise EndpointNotAllowedError(f"dominio invalido: {domain!r}")
    for d, tpl in ALLOWED_ENDPOINTS:
        if d == domain and _path_matches_template(path, tpl):
            return
    raise EndpointNotAllowedError(
        f"endpoint GET {domain}{path} no esta en ALLOWED_ENDPOINTS. "
        "Si Holded anyadio un endpoint nuevo, anyade su patron a "
        "holded_client.ALLOWED_ENDPOINTS tras vendorizar la doc."
    )


# -----------------------------------------------------------------------------
# Cliente
# -----------------------------------------------------------------------------

@dataclass
class HoldedResponse:
    status: int
    body: bytes
    headers: dict[str, str]

    @property
    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8")) if self.body else None


class HoldedClient:
    """Cliente HTTP read-only de la API Holded.

    Solo expone `get(...)` y `download_pdf(...)` como superficie publica.
    Cualquier otra forma de hablar con la API esta deliberadamente fuera.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        timeout: float = TIMEOUT,
        attempts: int = DEFAULT_ATTEMPTS,
        backoff: float = DEFAULT_BACKOFF,
        opener: Any | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("HOLDED_API_KEY") or ""
        if not self.api_key:
            raise HoldedError(
                "HOLDED_API_KEY no esta definida. Configurala en .env "
                "antes de instanciar HoldedClient."
            )
        self.base_url = (base_url or os.environ.get("HOLDED_API_BASE") or DEFAULT_BASE).rstrip("/")
        self.timeout = timeout
        self.attempts = max(1, attempts)
        self.backoff = max(0.0, backoff)
        # opener inyectable para tests (urllib.request.OpenerDirector compatible).
        self._opener = opener

    # -------------- API publica (SOLO LECTURA) --------------

    def get(
        self,
        domain: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> HoldedResponse:
        """GET https://api.holded.com/api/<domain>/v1<path>.

        - `domain`: uno de DOMAINS.
        - `path`: path relativo (empieza por '/'). Debe matchear algun
          patron de ALLOWED_ENDPOINTS o lanza EndpointNotAllowedError.
        - `params`: query params opcionales.
        """
        path = _normalize_path(path)
        _check_allowed(domain, path)
        return self._request_get(domain, path, params=params)

    def download_pdf(self, doc_type: str, document_id: str) -> bytes:
        """Descarga el PDF (raw bytes) asociado a un documento.

        Internamente: `GET /documents/{docType}/{documentId}/pdf` ->
        `{"status": 1, "data": "<base64>"}`. Decodifica y devuelve los
        bytes binarios.

        Devuelve `b""` si la respuesta de Holded indica status != 1 o
        el campo `data` no esta.
        """
        if doc_type not in DOC_TYPES:
            raise ValueError(f"doc_type invalido: {doc_type!r}. Validos: {DOC_TYPES}")
        if not document_id or not re.fullmatch(r"[A-Za-z0-9_-]+", document_id):
            raise ValueError(f"document_id invalido: {document_id!r}")
        resp = self.get("invoicing", f"/documents/{doc_type}/{document_id}/pdf")
        try:
            payload = resp.json
        except Exception as exc:
            raise HoldedError(f"PDF: respuesta no-JSON para {doc_type}/{document_id}: {exc}") from exc
        if not isinstance(payload, dict):
            return b""
        if payload.get("status") != 1:
            logger.warning("PDF: status != 1 para %s/%s: %r", doc_type, document_id, payload)
            return b""
        b64 = payload.get("data") or ""
        if not isinstance(b64, str):
            return b""
        import base64
        try:
            return base64.b64decode(b64, validate=False)
        except Exception as exc:
            raise HoldedError(f"PDF: base64 invalido para {doc_type}/{document_id}: {exc}") from exc

    def paginate(
        self,
        domain: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        page_size: int | None = None,
        max_pages: int | None = None,
    ) -> Iterator[Any]:
        """Generator que pagina sobre un endpoint list.

        Holded tiene 2 modos:
        - `dailyledger` y algunos similares: query param `page=N`, hasta
          500 items/pagina. Iteramos hasta que la pagina devuelva < page_size.
        - El resto (contacts, products, documents, ...): NO pagina —
          devuelve toda la lista de golpe. En ese caso yieldeamos todos
          los items y paramos en la primera "pagina".

        Heuristica: si el caller pasa `page_size`, asumimos paginacion;
        si no, asumimos lista completa.
        """
        params = dict(params or {})
        page = 1
        pages = 0
        while True:
            this_params = dict(params)
            if page_size is not None:
                this_params.setdefault("page", page)
            resp = self.get(domain, path, params=this_params)
            data = resp.json
            if data is None:
                return
            # En Holded los list-endpoints devuelven lista directa.
            # Defensivo por si algun endpoint devuelve {data: [...]}.
            if isinstance(data, dict):
                items = data.get("data") or data.get("items") or []
            elif isinstance(data, list):
                items = data
            else:
                items = []
            if not items:
                return
            for it in items:
                yield it
            pages += 1
            if max_pages is not None and pages >= max_pages:
                return
            if page_size is None or len(items) < page_size:
                return
            page += 1

    # -------------- Internos --------------

    def _request_get(
        self,
        domain: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> HoldedResponse:
        url = self._build_url(domain, path, params)
        headers = {
            "key": self.api_key,
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        log_url = self._loggable_url(url)
        last_exc: Exception | None = None
        for attempt in range(self.attempts):
            t0 = time.time()
            try:
                req = urllib.request.Request(url, headers=headers, method="GET")
                opener = self._opener
                if opener is None:
                    response = urllib.request.urlopen(req, timeout=self.timeout)
                else:
                    response = opener.open(req, timeout=self.timeout)
                with response as r:
                    body = r.read()
                    status = r.status
                    resp_headers = {k.lower(): v for k, v in r.headers.items()}
                dur_ms = int((time.time() - t0) * 1000)
                logger.info("GET %s -> %d (%d B, %d ms, attempt %d)",
                            log_url, status, len(body), dur_ms, attempt + 1)
                return HoldedResponse(status=status, body=body, headers=resp_headers)
            except urllib.error.HTTPError as e:
                dur_ms = int((time.time() - t0) * 1000)
                retry_after = self._parse_retry_after(e.headers.get("Retry-After") if e.headers else None)
                if e.code == 429:
                    logger.warning("GET %s -> 429 rate-limited (attempt %d/%d, retry-after=%s)",
                                   log_url, attempt + 1, self.attempts, retry_after)
                    last_exc = HoldedRateLimited(f"429 from {log_url}")
                elif 500 <= e.code < 600:
                    logger.warning("GET %s -> %d server error (attempt %d/%d)",
                                   log_url, e.code, attempt + 1, self.attempts)
                    last_exc = HoldedServerError(f"{e.code} from {log_url}")
                else:
                    body = e.read() if hasattr(e, "read") else b""
                    snippet = body[:200].decode(errors="replace")
                    raise HoldedError(f"GET {log_url} -> {e.code}: {snippet}") from e
                self._sleep_backoff(attempt, retry_after)
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                logger.warning("GET %s -> network error %s (attempt %d/%d)",
                               log_url, e, attempt + 1, self.attempts)
                last_exc = e
                self._sleep_backoff(attempt, None)
        assert last_exc is not None
        raise last_exc

    def _build_url(self, domain: str, path: str, params: dict[str, Any] | None) -> str:
        path = _normalize_path(path)
        base = f"{self.base_url}/api/{domain}/v1{path}"
        if not params:
            return base
        # Filtrar None y serializar listas como CSV (Holded asi lo espera en `customId[]`).
        cleaned: list[tuple[str, str]] = []
        for k, v in params.items():
            if v is None:
                continue
            if isinstance(v, (list, tuple)):
                cleaned.append((k, ",".join(str(x) for x in v)))
            elif isinstance(v, bool):
                cleaned.append((k, "true" if v else "false"))
            else:
                cleaned.append((k, str(v)))
        if not cleaned:
            return base
        return base + "?" + urllib.parse.urlencode(cleaned)

    def _loggable_url(self, url: str) -> str:
        # Nunca loggeamos la api_key (va por header, no en URL) — pero
        # enmascaramos por defensa si alguien la metio mal.
        if self.api_key and self.api_key in url:
            return url.replace(self.api_key, _mask(self.api_key))
        return url

    def _sleep_backoff(self, attempt: int, retry_after: float | None) -> None:
        if attempt + 1 >= self.attempts:
            return
        if retry_after is not None:
            delay = max(0.1, retry_after)
        else:
            delay = self.backoff * (2 ** attempt)
        time.sleep(delay)

    @staticmethod
    def _parse_retry_after(header_value: str | None) -> float | None:
        if not header_value:
            return None
        header_value = header_value.strip()
        if header_value.isdigit():
            return float(header_value)
        # Formato HTTP-date no lo soportamos; suficiente con el numerico.
        return None


# -----------------------------------------------------------------------------
# Helpers de alto nivel para resources frecuentes
# -----------------------------------------------------------------------------

def iter_contacts(client: HoldedClient) -> Iterator[dict]:
    yield from client.paginate("invoicing", "/contacts")


def iter_products(client: HoldedClient) -> Iterator[dict]:
    yield from client.paginate("invoicing", "/products")


def iter_services(client: HoldedClient) -> Iterator[dict]:
    yield from client.paginate("invoicing", "/services")


def iter_documents(client: HoldedClient, doc_type: str, **filters: Any) -> Iterator[dict]:
    if doc_type not in DOC_TYPES:
        raise ValueError(f"doc_type invalido: {doc_type!r}. Validos: {DOC_TYPES}")
    yield from client.paginate("invoicing", f"/documents/{doc_type}", params=filters or None)


def iter_dailyledger(client: HoldedClient, **filters: Any) -> Iterator[dict]:
    yield from client.paginate(
        "accounting",
        "/dailyledger",
        params=filters or None,
        page_size=500,  # dailyledger SI pagina con page=N, hasta 500/pagina
    )


def iter_payments(client: HoldedClient) -> Iterator[dict]:
    yield from client.paginate("invoicing", "/payments")


def iter_treasuries(client: HoldedClient) -> Iterator[dict]:
    yield from client.paginate("invoicing", "/treasury")


def iter_taxes(client: HoldedClient) -> Iterator[dict]:
    yield from client.paginate("invoicing", "/taxes")


def iter_warehouses(client: HoldedClient) -> Iterator[dict]:
    yield from client.paginate("invoicing", "/warehouse")


def iter_expensesaccount(client: HoldedClient) -> Iterator[dict]:
    yield from client.paginate("invoicing", "/expensesaccount")


def iter_remittances(client: HoldedClient) -> Iterator[dict]:
    yield from client.paginate("invoicing", "/remittances")


def iter_saleschannels(client: HoldedClient) -> Iterator[dict]:
    yield from client.paginate("invoicing", "/saleschannels")


def get_numbering_series(client: HoldedClient, type_: str) -> Any:
    """`type_` es uno de los documentTypes (invoice, purchase, ...)."""
    if type_ not in DOC_TYPES:
        raise ValueError(f"type invalido: {type_!r}. Validos: {DOC_TYPES}")
    return client.get("invoicing", f"/numberingseries/{type_}").json


def get_contact_groups(client: HoldedClient) -> Any:
    return client.get("invoicing", "/contacts/groups").json


if __name__ == "__main__":
    # Diagnostico rapido: cargar el cliente y listar endpoints permitidos.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    print(f"Allowed endpoints ({len(ALLOWED_ENDPOINTS)}):")
    for d, p in ALLOWED_ENDPOINTS:
        print(f"  GET https://api.holded.com/api/{d}/v1{p}")
    if not os.environ.get("HOLDED_API_KEY"):
        print("\n(set HOLDED_API_KEY to construct a client)")
        sys.exit(0)
    c = HoldedClient()
    print(f"\nClient ready. base_url={c.base_url} api_key={_mask(c.api_key)}")
