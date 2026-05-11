"""Tests offline para helpers puros de holded_resolvers.py."""
from __future__ import annotations

import pytest

from holded_resolvers import (
    derive_pgce_parent,
    iso_from_unix,
    normalize_vat,
    parse_journal_prefix,
    partner_active_from_name,
    HoldedResolvers,
)


# ---------------------------------------------------------------------------
# normalize_vat
# ---------------------------------------------------------------------------


class TestNormalizeVat:
    def test_none(self):
        assert normalize_vat(None) is None

    def test_empty(self):
        assert normalize_vat("") is None
        assert normalize_vat("   ") is None

    def test_already_prefixed(self):
        assert normalize_vat("ESB12345678") == "ESB12345678"
        assert normalize_vat("ESb12345678") == "ESB12345678"
        assert normalize_vat("FR12345678901") == "FR12345678901"

    def test_strips_separators(self):
        assert normalize_vat("ES-B12.345-678") == "ESB12345678"
        assert normalize_vat(" ES B 12 345 678 ") == "ESB12345678"

    def test_prepends_country(self):
        assert normalize_vat("12345678Z", country="ES") == "ES12345678Z"
        assert normalize_vat("12345678Z", country="es") == "ES12345678Z"

    def test_country_invalid_falls_through_to_es_heuristic(self):
        # country invalido (len!=2): ignora country y aplica ES heuristic
        # si el patron casa (8-9 chars digito+letra control).
        assert normalize_vat("12345678Z", country="X") == "ES12345678Z"
        # Si NO casa la heuristica, devuelve limpio sin pais.
        assert normalize_vat("123456", country="X") == "123456"

    def test_es_heuristic_when_no_country(self):
        # 9 chars digito+letra control valido: presupone ES
        assert normalize_vat("12345678Z") == "ES12345678Z"
        assert normalize_vat("B12345674") == "ESB12345674"

    def test_too_short_not_es_heuristic(self):
        # 7 chars: ni 8-9, no aplica heuristica
        assert normalize_vat("123456") == "123456"

    def test_too_long_not_es_heuristic(self):
        # 10 chars: ya tiene prefijo (dos letras + 8)
        assert normalize_vat("ABCDEFGHIJ") == "ABCDEFGHIJ"


# ---------------------------------------------------------------------------
# parse_journal_prefix
# ---------------------------------------------------------------------------


class TestParseJournalPrefix:
    @pytest.mark.parametrize(
        "doc_number,expected",
        [
            ("A-2024-0001", "A-"),
            ("PB-1234", "PB-"),
            ("FVU-25-7", "FVU-"),
            ("AC-0001", "AC-"),
            ("KD-99", "KD-"),
            ("AF-3", "AF-"),
            ("L-1", "L-"),
            ("PI-456", "PI-"),
            ("PR-7", "PR-"),  # extrae aunque resolve_journal lo rechace
            ("a-2024-1", "A-"),  # case-insensitive
            ("  PB-1  ", "PB-"),  # strip
        ],
    )
    def test_extracts(self, doc_number, expected):
        assert parse_journal_prefix(doc_number) == expected

    @pytest.mark.parametrize("bad", [None, "", "1234", " 999"])
    def test_no_prefix(self, bad):
        assert parse_journal_prefix(bad) is None

    def test_extracts_any_prefix_validation_is_resolvers_job(self):
        # parse_journal_prefix es un tokenizer: extrae cualquier "LETRAS-".
        # La validacion contra JOURNAL_PREFIX_TO_CODE la hace resolve_journal.
        assert parse_journal_prefix("FACT-123") == "FACT-"
        assert parse_journal_prefix("XYZ-1") == "XYZ-"


# ---------------------------------------------------------------------------
# derive_pgce_parent
# ---------------------------------------------------------------------------


class TestDerivePgceParent:
    @pytest.mark.parametrize(
        "code,expected",
        [
            ("57200049002", "572000"),  # Santander 11d
            ("57200018201", "572000"),  # BBVA 11d
            ("52100000014", "521000"),  # tarjeta BBVA
            ("47200000121", "472000"),  # IVA soportado intracom
            ("47700000021", "477000"),  # IVA repercutido 21
            ("47510000019", "475100"),  # IRPF 19%
            ("60000000001", "600000"),  # compras
            ("62300000010", "623000"),  # servicios profesionales
            ("70500000099", "705000"),  # prestacion servicios
            ("70000000001", "700000"),  # ventas mercaderias
        ],
    )
    def test_maps_known_prefixes(self, code, expected):
        assert derive_pgce_parent(code) == expected

    def test_longest_prefix_wins(self):
        # 4751 (IRPF) gana sobre 47 (IVA), aunque "47" no esta en rules
        assert derive_pgce_parent("47510000099") == "475100"

    def test_unknown_prefix(self):
        # 13X no esta mapeado (capital, no aparece en compras/ventas/iva)
        assert derive_pgce_parent("10000000001") is None
        assert derive_pgce_parent("12900000001") is None

    @pytest.mark.parametrize("bad", [None, "", "abc", "123ABC456", "  "])
    def test_invalid_input(self, bad):
        assert derive_pgce_parent(bad) is None


# ---------------------------------------------------------------------------
# partner_active_from_name
# ---------------------------------------------------------------------------


class TestPartnerActiveFromName:
    def test_normal(self):
        assert partner_active_from_name("Acme S.L.") == ("Acme S.L.", True)

    def test_marked_inactive(self):
        assert partner_active_from_name("Acme (NO USAR)") == ("Acme", False)
        assert partner_active_from_name("Acme S.L. (NO USAR) ") == ("Acme S.L.", False)

    def test_marked_inactive_lowercase(self):
        assert partner_active_from_name("Acme (no usar)") == ("Acme", False)

    def test_marked_inline(self):
        n, a = partner_active_from_name("Pre (NO USAR) Post")
        assert n == "Pre Post"
        assert a is False

    def test_marked_extra_whitespace(self):
        assert partner_active_from_name("Acme  (NO  USAR)") == ("Acme", False)

    def test_none(self):
        assert partner_active_from_name(None) == ("", True)

    def test_empty(self):
        assert partner_active_from_name("") == ("", True)


# ---------------------------------------------------------------------------
# iso_from_unix
# ---------------------------------------------------------------------------


class TestIsoFromUnix:
    def test_valid_int(self):
        # 2024-01-15 12:00:00 UTC = 1705320000
        assert iso_from_unix(1705320000) == "2024-01-15"

    def test_valid_float(self):
        assert iso_from_unix(1705320000.5) == "2024-01-15"

    def test_valid_str(self):
        assert iso_from_unix("1705320000") == "2024-01-15"

    @pytest.mark.parametrize("bad", [None, "", 0, "0", -1, "abc", -3600])
    def test_invalid(self, bad):
        assert iso_from_unix(bad) is None


# ---------------------------------------------------------------------------
# HoldedResolvers (smoke: dataclass instancia con fake client)
# ---------------------------------------------------------------------------


class _FakeClient:
    """Stub minimo de OdooClient para tests offline.

    Solo necesitamos que `HoldedResolvers` se pueda instanciar. Las
    llamadas a `.call()` no se ejercitan en estos tests (los resolvers
    completos requieren un Odoo real y se cubren con tests de
    integracion en Fase 5.3).
    """

    def call(self, *_args, **_kwargs):  # pragma: no cover
        raise RuntimeError("FakeClient.call invoked in offline test")


class TestHoldedResolversInstantiation:
    def test_defaults(self):
        r = HoldedResolvers(client=_FakeClient())
        assert r.tax_rules == {}
        assert r.treasury_to_journal == {}
        assert r.stats.partner_hits == 0
        assert r._partner_cache == {}

    def test_apply_tax_rule_by_country(self):
        r = HoldedResolvers(client=_FakeClient())
        rule = {
            "default_tax_id": 95,
            "by_partner_country": {"US": 112, "AU": 112},
        }
        assert r._apply_tax_rule(rule, {"partner_country": "US"}) == 112
        assert r._apply_tax_rule(rule, {"partner_country": "us"}) == 112
        assert r._apply_tax_rule(rule, {"partner_country": "ES"}) == 95

    def test_apply_tax_rule_by_partner_in(self):
        r = HoldedResolvers(client=_FakeClient())
        rule = {
            "default_tax_id": 95,
            "by_partner_in": {
                "renting": [200, "ARVAL", "LEASE PLAN"],
            },
        }
        assert r._apply_tax_rule(rule, {"partner_name": "ARVAL Service SA"}) == 200
        assert r._apply_tax_rule(rule, {"partner_name": "Lease Plan Iberia"}) == 200
        assert r._apply_tax_rule(rule, {"partner_name": "Generic SL"}) == 95

    def test_apply_tax_rule_by_doc_type(self):
        r = HoldedResolvers(client=_FakeClient())
        rule = {
            "default_tax_id": 95,
            "by_doc_type": {"purchase": 159},
        }
        assert r._apply_tax_rule(rule, {"doc_type": "purchase"}) == 159
        assert r._apply_tax_rule(rule, {"doc_type": "invoice"}) == 95

    def test_apply_tax_rule_no_match_returns_default(self):
        r = HoldedResolvers(client=_FakeClient())
        rule = {"default_tax_id": 95}
        assert r._apply_tax_rule(rule, {}) == 95

    def test_apply_tax_rule_no_default_returns_minus_one(self):
        r = HoldedResolvers(client=_FakeClient())
        rule = {"by_partner_country": {"US": 112}}
        assert r._apply_tax_rule(rule, {"partner_country": "ES"}) == -1
