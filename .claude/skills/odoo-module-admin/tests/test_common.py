"""Tests para _common.py: require_env, format_amount, retry_on_network."""
from __future__ import annotations

import pytest

from _common import OdooEnvError, format_amount, require_env, retry_on_network


class TestRequireEnv:
    def test_returns_dict_when_all_present(self, monkeypatch):
        monkeypatch.setenv("FOO", "1")
        monkeypatch.setenv("BAR", "two")
        assert require_env("FOO", "BAR") == {"FOO": "1", "BAR": "two"}

    def test_raises_when_missing(self, monkeypatch):
        monkeypatch.delenv("MISSING_XYZ", raising=False)
        with pytest.raises(OdooEnvError) as exc:
            require_env("MISSING_XYZ")
        assert "MISSING_XYZ" in str(exc.value)

    def test_lists_all_missing(self, monkeypatch):
        monkeypatch.delenv("A1", raising=False)
        monkeypatch.delenv("A2", raising=False)
        with pytest.raises(OdooEnvError) as exc:
            require_env("A1", "A2")
        msg = str(exc.value)
        assert "A1" in msg and "A2" in msg


class TestFormatAmount:
    def test_basic(self):
        assert format_amount(1234.5) == "1,234.50 EUR"

    def test_zero(self):
        assert format_amount(0) == "0.00 EUR"

    def test_negative(self):
        assert format_amount(-100) == "-100.00 EUR"

    def test_other_currency(self):
        assert format_amount(99.9, currency="USD") == "99.90 USD"


class TestRetryOnNetwork:
    def test_returns_value_on_first_success(self):
        calls = {"n": 0}
        def fn():
            calls["n"] += 1
            return "ok"
        assert retry_on_network(fn) == "ok"
        assert calls["n"] == 1

    def test_does_not_retry_business_errors(self):
        from _common import OdooError
        def fn():
            raise OdooError("validation failed")
        with pytest.raises(OdooError):
            retry_on_network(fn, attempts=3, base_delay=0)

    def test_retries_on_network_error_then_succeeds(self):
        # Simular fallo de red -> exito
        # Usamos OSError que retry_on_network captura.
        attempts = {"n": 0}
        def fn():
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise OSError("connection reset")
            return "ok"
        assert retry_on_network(fn, attempts=5, base_delay=0) == "ok"
        assert attempts["n"] == 3

    def test_exhausts_retries_and_raises(self):
        def fn():
            raise OSError("nope")
        with pytest.raises(OSError):
            retry_on_network(fn, attempts=2, base_delay=0)
