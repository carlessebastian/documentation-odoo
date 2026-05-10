"""Tests para partner_fiscal_setup.py."""
from __future__ import annotations

import pytest

from _common import OdooError
import partner_fiscal_setup


class _StubClient:
    """OdooClient mock que devuelve respuestas pre-canned por (model, method)."""

    def __init__(self, responses: dict | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[tuple] = []

    def call(self, model, method, args, kwargs=None):
        self.calls.append((model, method, args, kwargs or {}))
        key = (model, method)
        if key in self.responses:
            return self.responses[key]
        # Defaults razonables
        if method == "search":
            return [1]
        if method == "search_read":
            return [{"res_id": 1}]
        return None


class TestBuildDomain:
    def _client_with_es_and_eu(self):
        return _StubClient({
            ("res.country", "search"): [69],
            ("ir.model.data", "search_read"): [{"res_id": 5}],
        })

    def test_match_partner_ids(self):
        d = partner_fiscal_setup.build_domain(
            _StubClient(), "match_partner_ids", 1, [10, 20, 30]
        )
        assert d == [("id", "in", [10, 20, 30])]

    def test_match_partner_ids_requires_ids(self):
        with pytest.raises(OdooError):
            partner_fiscal_setup.build_domain(
                _StubClient(), "match_partner_ids", 1, None
            )

    def test_spain_only_filters_country(self):
        c = self._client_with_es_and_eu()
        d = partner_fiscal_setup.build_domain(c, "spain_only", 1, None)
        assert ("country_id", "=", 69) in d

    def test_eu_with_vat_excludes_es(self):
        c = self._client_with_es_and_eu()
        d = partner_fiscal_setup.build_domain(c, "eu_with_vat", 1, None)
        assert ("country_id", "!=", 69) in d
        assert ("country_id.country_group_ids", "in", [5]) in d
        assert ("vat", "!=", False) in d

    def test_non_eu_with_vat_negates_eu(self):
        c = self._client_with_es_and_eu()
        d = partner_fiscal_setup.build_domain(c, "non_eu_with_vat", 1, None)
        # negacion antes del operador "in"
        assert "!" in d
        assert ("vat", "!=", False) in d

    def test_unknown_criterion(self):
        with pytest.raises(OdooError):
            partner_fiscal_setup.build_domain(
                _StubClient(), "unknown", 1, None
            )


class TestResolveFp:
    def test_found(self):
        c = _StubClient({("account.fiscal.position", "search"): [42]})
        assert partner_fiscal_setup.resolve_fp(c, "Intra UE", 1) == 42

    def test_not_found(self):
        c = _StubClient({("account.fiscal.position", "search"): []})
        with pytest.raises(OdooError) as exc:
            partner_fiscal_setup.resolve_fp(c, "Inexistente", 1)
        assert "no existe" in str(exc.value)


class TestResolvePaymentTerm:
    def test_found(self):
        c = _StubClient({("account.payment.term", "search"): [99]})
        assert partner_fiscal_setup.resolve_payment_term(c, "30 Days") == 99

    def test_not_found_helpful_error(self):
        c = _StubClient({("account.payment.term", "search"): []})
        with pytest.raises(OdooError) as exc:
            partner_fiscal_setup.resolve_payment_term(c, "Nope")
        assert "no encontrado" in str(exc.value)


class TestValidCriteria:
    def test_canonical(self):
        for c in ("eu_with_vat", "non_eu_with_vat", "spain_only",
                  "match_partner_ids"):
            assert c in partner_fiscal_setup.VALID_CRITERIA
