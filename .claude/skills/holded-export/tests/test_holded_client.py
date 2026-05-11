"""Tests para holded_client.HoldedClient.

Cubren la garantia read-only (sin verbos de escritura), la whitelist de
endpoints, la paginacion y el manejo de 429.

No hace HTTP real: los tests mockean urllib mediante un fake opener.
"""
from __future__ import annotations

import io
import json
from typing import Any
from unittest.mock import MagicMock

import pytest

import holded_client
from holded_client import (
    ALLOWED_ENDPOINTS,
    DOC_TYPES,
    EndpointNotAllowedError,
    HoldedClient,
    HoldedError,
    HoldedRateLimited,
    HoldedServerError,
    _check_allowed,
    _path_matches_template,
)


# ---------------------------------------------------------------------------
# Garantia read-only
# ---------------------------------------------------------------------------

class TestReadOnlyContract:
    """La superficie publica no expone NADA que pueda escribir en Holded."""

    def test_no_write_verbs_in_public_api(self):
        # Solo metodos publicos (no '_'). Filtra dataclass/Iterator helpers.
        public = [m for m in dir(HoldedClient)
                  if not m.startswith("_") and callable(getattr(HoldedClient, m))]
        # Esperamos exactamente: get, download_pdf, paginate.
        # Cualquier otro miembro publico debe ser explicitamente permitido.
        assert set(public) == {"get", "download_pdf", "paginate"}, (
            f"Superficie publica cambio: {public}. "
            "Si anyades un metodo publico, valida que no introduce escrituras "
            "y actualiza este test."
        )

    @pytest.mark.parametrize("forbidden", [
        "post", "put", "patch", "delete", "create", "update", "remove",
        "send", "upload", "write", "modify", "submit",
    ])
    def test_no_forbidden_method_names(self, forbidden):
        assert not hasattr(HoldedClient, forbidden), (
            f"HoldedClient no debe tener metodo '{forbidden}' (read-only)"
        )

    def test_request_internal_only_handles_get(self):
        """El metodo interno _request_get es el unico canal HTTP."""
        # No existe _request_post / _request_put en el modulo.
        internals = [m for m in dir(HoldedClient) if m.startswith("_request")]
        assert internals == ["_request_get"], internals


# ---------------------------------------------------------------------------
# Whitelist de endpoints
# ---------------------------------------------------------------------------

class TestAllowedEndpoints:
    def test_path_matches_template_exact(self):
        assert _path_matches_template("/contacts", "/contacts")

    def test_path_matches_template_placeholder(self):
        assert _path_matches_template("/contacts/abc123", "/contacts/{contactId}")

    def test_path_matches_template_mismatch_segs(self):
        assert not _path_matches_template("/contacts", "/contacts/{id}")
        assert not _path_matches_template("/contacts/a/b", "/contacts/{id}")

    def test_path_matches_template_literal_mismatch(self):
        assert not _path_matches_template("/foo/abc", "/bar/{id}")

    def test_check_allowed_pass(self):
        # No debe lanzar.
        _check_allowed("invoicing", "/contacts")
        _check_allowed("invoicing", "/contacts/abc")
        _check_allowed("invoicing", "/documents/invoice")
        _check_allowed("invoicing", "/documents/invoice/abc/pdf")
        _check_allowed("accounting", "/dailyledger")

    def test_check_allowed_unknown_domain(self):
        with pytest.raises(EndpointNotAllowedError):
            _check_allowed("custom", "/contacts")

    def test_check_allowed_unknown_path(self):
        with pytest.raises(EndpointNotAllowedError):
            _check_allowed("invoicing", "/webhooks")
        with pytest.raises(EndpointNotAllowedError):
            _check_allowed("invoicing", "/dangerous-write-endpoint")

    def test_client_get_rejects_unknown_path(self, monkeypatch):
        monkeypatch.setenv("HOLDED_API_KEY", "k_test")
        c = HoldedClient()
        with pytest.raises(EndpointNotAllowedError):
            c.get("invoicing", "/webhooks")

    def test_all_allowed_endpoints_are_get_resources(self):
        # Sanity check: ningun endpoint listado huele a write
        suspicious = ("/create", "/update", "/delete", "/send", "/upload",
                      "/webhook", "/notify")
        for domain, path in ALLOWED_ENDPOINTS:
            assert not any(s in path for s in suspicious), (
                f"Endpoint sospechoso de escritura en whitelist: {domain}{path}"
            )


# ---------------------------------------------------------------------------
# Auth y construccion de URL
# ---------------------------------------------------------------------------

class TestAuth:
    def test_requires_api_key(self, monkeypatch):
        monkeypatch.delenv("HOLDED_API_KEY", raising=False)
        with pytest.raises(HoldedError):
            HoldedClient()

    def test_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("HOLDED_API_KEY", "k_from_env")
        c = HoldedClient()
        assert c.api_key == "k_from_env"

    def test_api_key_explicit_overrides_env(self, monkeypatch):
        monkeypatch.setenv("HOLDED_API_KEY", "from_env")
        c = HoldedClient(api_key="explicit")
        assert c.api_key == "explicit"

    def test_base_url_default(self, monkeypatch):
        monkeypatch.setenv("HOLDED_API_KEY", "k")
        c = HoldedClient()
        assert c.base_url == "https://api.holded.com"

    def test_base_url_override(self, monkeypatch):
        monkeypatch.setenv("HOLDED_API_KEY", "k")
        c = HoldedClient(base_url="https://example.invalid")
        assert c.base_url == "https://example.invalid"


# ---------------------------------------------------------------------------
# Fakes para urllib
# ---------------------------------------------------------------------------

class FakeHTTPResponse:
    def __init__(self, body: bytes, status: int = 200, headers: dict[str, str] | None = None):
        self._body = body
        self.status = status
        self.headers = headers or {"Content-Type": "application/json"}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._body


class FakeOpener:
    """Captura cada request y devuelve respuestas programadas."""

    def __init__(self, scripted_responses):
        # scripted_responses: list of FakeHTTPResponse o Exception
        self.scripted = list(scripted_responses)
        self.requests = []

    def open(self, req, timeout=None):
        self.requests.append({
            "method": req.get_method(),
            "url": req.full_url,
            "headers": dict(req.header_items()),
        })
        if not self.scripted:
            raise AssertionError("No more scripted responses")
        resp = self.scripted.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp


# ---------------------------------------------------------------------------
# GET happy path + URL building
# ---------------------------------------------------------------------------

class TestGet:
    def _client(self, monkeypatch, *responses):
        monkeypatch.setenv("HOLDED_API_KEY", "secret_key_xyz123")
        opener = FakeOpener(responses)
        c = HoldedClient(opener=opener)
        return c, opener

    def test_get_calls_correct_url(self, monkeypatch):
        body = json.dumps([{"id": "a"}, {"id": "b"}]).encode()
        c, opener = self._client(monkeypatch, FakeHTTPResponse(body))
        resp = c.get("invoicing", "/contacts")
        assert resp.status == 200
        assert resp.json == [{"id": "a"}, {"id": "b"}]
        req = opener.requests[0]
        assert req["method"] == "GET"
        assert req["url"] == "https://api.holded.com/api/invoicing/v1/contacts"

    def test_get_with_params(self, monkeypatch):
        body = b"[]"
        c, opener = self._client(monkeypatch, FakeHTTPResponse(body))
        c.get("invoicing", "/contacts", params={"customId": ["a", "b"], "ignored": None, "active": True})
        url = opener.requests[0]["url"]
        assert "customId=a%2Cb" in url
        assert "active=true" in url
        assert "ignored" not in url

    def test_get_sends_api_key_header(self, monkeypatch):
        c, opener = self._client(monkeypatch, FakeHTTPResponse(b"[]"))
        c.get("invoicing", "/contacts")
        headers = opener.requests[0]["headers"]
        # urllib normaliza nombres con title-case.
        assert headers.get("Key") == "secret_key_xyz123" or headers.get("key") == "secret_key_xyz123"

    def test_get_rejects_disallowed_endpoint(self, monkeypatch):
        c, _ = self._client(monkeypatch, FakeHTTPResponse(b"[]"))
        with pytest.raises(EndpointNotAllowedError):
            c.get("invoicing", "/webhooks")


# ---------------------------------------------------------------------------
# Retry / backoff
# ---------------------------------------------------------------------------

class TestRetryBackoff:
    def _client(self, monkeypatch, *responses, attempts=3):
        monkeypatch.setenv("HOLDED_API_KEY", "k")
        opener = FakeOpener(responses)
        c = HoldedClient(opener=opener, attempts=attempts, backoff=0)
        return c, opener

    def test_429_then_success(self, monkeypatch):
        import urllib.error
        err429 = urllib.error.HTTPError(
            url="x", code=429, msg="Too Many", hdrs=None, fp=io.BytesIO(b"")
        )
        # urllib.error.HTTPError needs headers attribute for our code.
        err429.headers = {"Retry-After": "0"}
        c, opener = self._client(
            monkeypatch,
            err429,
            FakeHTTPResponse(b"[]"),
        )
        resp = c.get("invoicing", "/contacts")
        assert resp.status == 200
        assert len(opener.requests) == 2

    def test_429_exhausts_retries(self, monkeypatch):
        import urllib.error
        err = urllib.error.HTTPError(url="x", code=429, msg="", hdrs=None, fp=io.BytesIO(b""))
        err.headers = {}
        c, _ = self._client(monkeypatch, err, err, err, attempts=3)
        with pytest.raises(HoldedRateLimited):
            c.get("invoicing", "/contacts")

    def test_5xx_then_success(self, monkeypatch):
        import urllib.error
        err = urllib.error.HTTPError(url="x", code=503, msg="busy", hdrs=None, fp=io.BytesIO(b""))
        err.headers = {}
        c, opener = self._client(
            monkeypatch,
            err,
            FakeHTTPResponse(b"[]"),
        )
        resp = c.get("invoicing", "/contacts")
        assert resp.status == 200

    def test_4xx_other_does_not_retry(self, monkeypatch):
        import urllib.error
        err = urllib.error.HTTPError(url="x", code=400, msg="bad", hdrs=None, fp=io.BytesIO(b"oops"))
        err.headers = {}
        c, opener = self._client(monkeypatch, err)
        with pytest.raises(HoldedError):
            c.get("invoicing", "/contacts")
        assert len(opener.requests) == 1  # no retry

    def test_retry_after_parsing(self):
        assert HoldedClient._parse_retry_after("12") == 12.0
        assert HoldedClient._parse_retry_after(None) is None
        assert HoldedClient._parse_retry_after("") is None
        assert HoldedClient._parse_retry_after("Mon, 01 Jan 2026 00:00 GMT") is None  # http-date no soportado


# ---------------------------------------------------------------------------
# Paginacion
# ---------------------------------------------------------------------------

class TestPaginate:
    def _client(self, monkeypatch, *responses):
        monkeypatch.setenv("HOLDED_API_KEY", "k")
        opener = FakeOpener(responses)
        c = HoldedClient(opener=opener, attempts=1, backoff=0)
        return c, opener

    def test_no_pagination_single_page(self, monkeypatch):
        body = json.dumps([{"id": "a"}, {"id": "b"}, {"id": "c"}]).encode()
        c, opener = self._client(monkeypatch, FakeHTTPResponse(body))
        items = list(c.paginate("invoicing", "/contacts"))
        assert [i["id"] for i in items] == ["a", "b", "c"]
        assert len(opener.requests) == 1

    def test_page_size_paginates(self, monkeypatch):
        # 2 paginas de 2 + 1 final con 1 (< page_size -> stop)
        page1 = json.dumps([{"id": 1}, {"id": 2}]).encode()
        page2 = json.dumps([{"id": 3}, {"id": 4}]).encode()
        page3 = json.dumps([{"id": 5}]).encode()
        c, opener = self._client(
            monkeypatch,
            FakeHTTPResponse(page1),
            FakeHTTPResponse(page2),
            FakeHTTPResponse(page3),
        )
        items = list(c.paginate("accounting", "/dailyledger", page_size=2))
        assert [i["id"] for i in items] == [1, 2, 3, 4, 5]
        # Verifica que el query tiene ?page=N progresivo
        urls = [r["url"] for r in opener.requests]
        assert "page=1" in urls[0]
        assert "page=2" in urls[1]
        assert "page=3" in urls[2]

    def test_empty_first_page_stops(self, monkeypatch):
        c, opener = self._client(monkeypatch, FakeHTTPResponse(b"[]"))
        items = list(c.paginate("invoicing", "/contacts"))
        assert items == []
        assert len(opener.requests) == 1

    def test_max_pages_caps(self, monkeypatch):
        page = json.dumps([{"id": i} for i in range(100)]).encode()
        c, opener = self._client(
            monkeypatch,
            FakeHTTPResponse(page),
            FakeHTTPResponse(page),
            FakeHTTPResponse(page),
        )
        items = list(c.paginate("accounting", "/dailyledger", page_size=100, max_pages=2))
        assert len(items) == 200
        assert len(opener.requests) == 2


# ---------------------------------------------------------------------------
# PDF download
# ---------------------------------------------------------------------------

class TestDownloadPdf:
    def _client(self, monkeypatch, *responses):
        monkeypatch.setenv("HOLDED_API_KEY", "k")
        opener = FakeOpener(responses)
        return HoldedClient(opener=opener, attempts=1), opener

    def test_download_pdf_ok(self, monkeypatch):
        import base64
        pdf_bytes = b"%PDF-1.4\n... fake bytes ..."
        body = json.dumps({"status": 1, "data": base64.b64encode(pdf_bytes).decode()}).encode()
        c, opener = self._client(monkeypatch, FakeHTTPResponse(body))
        out = c.download_pdf("invoice", "abc123")
        assert out == pdf_bytes
        # URL correcto
        assert opener.requests[0]["url"].endswith("/documents/invoice/abc123/pdf")

    def test_download_pdf_status_zero_returns_empty(self, monkeypatch):
        body = json.dumps({"status": 0, "data": ""}).encode()
        c, _ = self._client(monkeypatch, FakeHTTPResponse(body))
        assert c.download_pdf("invoice", "abc") == b""

    def test_download_pdf_invalid_doctype(self, monkeypatch):
        monkeypatch.setenv("HOLDED_API_KEY", "k")
        c = HoldedClient()
        with pytest.raises(ValueError):
            c.download_pdf("bogus", "abc")

    def test_download_pdf_invalid_id(self, monkeypatch):
        monkeypatch.setenv("HOLDED_API_KEY", "k")
        c = HoldedClient()
        with pytest.raises(ValueError):
            c.download_pdf("invoice", "../etc/passwd")
        with pytest.raises(ValueError):
            c.download_pdf("invoice", "")


# ---------------------------------------------------------------------------
# Logging / masking
# ---------------------------------------------------------------------------

class TestLogging:
    def test_loggable_url_masks_key_if_present(self, monkeypatch):
        monkeypatch.setenv("HOLDED_API_KEY", "super_secret_token_value_xyz")
        c = HoldedClient()
        url = f"https://api.holded.com/?token={c.api_key}"
        masked = c._loggable_url(url)
        assert "super_secret_token_value_xyz" not in masked
        assert "..." in masked
