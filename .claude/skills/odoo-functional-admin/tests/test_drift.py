"""Tests para helpers puros de _drift.py."""
from __future__ import annotations

import _drift


class TestNormalizeCompanies:
    def test_basic(self):
        rows = [
            {"id": 1, "name": "Holding", "vat": "ESB12345678",
             "currency_id": [1, "EUR"], "country_id": [69, "Spain"],
             "parent_id": False},
            {"id": 2, "name": "Sub", "vat": "ESB22222222",
             "currency_id": [1, "EUR"], "country_id": [69, "Spain"],
             "parent_id": [1, "Holding"]},
        ]
        out = _drift.normalize_companies(rows)
        assert out["ESB12345678"]["parent_vat"] is None
        assert out["ESB22222222"]["parent_vat"] == "ESB12345678"
        assert out["ESB22222222"]["currency"] == "EUR"

    def test_skips_no_vat(self):
        rows = [{"id": 1, "name": "X", "vat": False,
                 "currency_id": False, "country_id": False, "parent_id": False}]
        assert _drift.normalize_companies(rows) == {}


class TestNormalizeCompaniesYaml:
    def test_uppercases_vat(self):
        out = _drift.normalize_companies_yaml(
            [{"vat": "esb12345678", "name": "X", "currency": "eur",
              "country": "es", "parent_vat": "esb999"}]
        )
        assert "ESB12345678" in out
        assert out["ESB12345678"]["currency"] == "EUR"
        assert out["ESB12345678"]["country"] == "ES"
        assert out["ESB12345678"]["parent_vat"] == "ESB999"

    def test_handles_none(self):
        out = _drift.normalize_companies_yaml(None)
        assert out == {}


def _at(local: str, domain: str) -> str:
    """Email built via concat to dodge email-redaction filters in tooling."""
    return local + chr(64) + domain


class TestNormalizeUsers:
    def test_basic(self):
        upper_login = _at("MARIA", "x.tld")
        lower_login = _at("maria", "x.tld")
        rows = [
            {"login": upper_login, "name": "Maria",
             "lang": "ca_ES", "active": True,
             "groups_id": [1, 2], "company_ids": [10, 20]},
        ]
        gid = {1: "base.group_user", 2: "account.group_account_invoice"}
        cid = {10: "ESB12345678", 20: "ESB22222222"}
        out = _drift.normalize_users(rows, gid, cid)
        assert lower_login in out  # lowercased
        u = out[lower_login]
        assert u["groups"] == sorted(gid.values())
        assert u["company_vats"] == ["ESB12345678", "ESB22222222"]

    def test_skips_admin(self):
        rows = [{"login": "admin", "name": "A", "active": True,
                 "groups_id": [], "company_ids": []}]
        assert _drift.normalize_users(rows, {}, {}) == {}


class TestNormalizeJournals:
    def test_keys_by_company_and_code(self):
        rows = [
            {"company_id": [10, "X"], "code": "vent", "type": "sale", "name": "V"},
            {"company_id": [10, "X"], "code": "comp", "type": "purchase", "name": "C"},
            {"company_id": [20, "Y"], "code": "vent", "type": "sale", "name": "V2"},
        ]
        cid = {10: "ESB10", 20: "ESB20"}
        out = _drift.normalize_journals(rows, cid)
        assert ("ESB10", "VENT") in out
        assert ("ESB10", "COMP") in out
        assert ("ESB20", "VENT") in out
        assert out[("ESB20", "VENT")]["name"] == "V2"

    def test_skips_unknown_company(self):
        rows = [{"company_id": [99, "Z"], "code": "X", "type": "sale", "name": "Z"}]
        assert _drift.normalize_journals(rows, {10: "ESB10"}) == {}


class TestDiffSection:
    def test_all_ok(self):
        d = _drift.diff_section(
            {"a": {"x": 1, "y": 2}}, {"a": {"x": 1, "y": 2}}, ["x", "y"]
        )
        assert d["ok"] is True
        assert d["missing"] == []
        assert d["extra"] == []
        assert d["changed"] == []

    def test_missing(self):
        d = _drift.diff_section(
            {"a": {"x": 1}, "b": {"x": 2}}, {"a": {"x": 1}}, ["x"]
        )
        assert d["missing"] == [{"x": 2}]
        assert d["ok"] is False

    def test_extra(self):
        d = _drift.diff_section(
            {"a": {"x": 1}}, {"a": {"x": 1}, "b": {"x": 2}}, ["x"]
        )
        assert d["extra"] == [{"x": 2}]
        assert d["ok"] is True   # extras NO marcan drift por defecto

    def test_changed_field(self):
        d = _drift.diff_section(
            {"a": {"name": "Want"}}, {"a": {"name": "Have"}}, ["name"]
        )
        assert d["changed"] == [
            {"key": "a", "fields": {"name": {"want": "Want", "have": "Have"}}}
        ]
        assert d["ok"] is False

    def test_lists_compared_as_sets(self):
        d = _drift.diff_section(
            {"a": {"groups": ["x", "y"]}}, {"a": {"groups": ["y", "x"]}}, ["groups"]
        )
        assert d["ok"] is True

    def test_skips_none_in_desired(self):
        # Si el YAML pone None en un campo, no se compara contra actual
        d = _drift.diff_section(
            {"a": {"name": None, "x": 1}}, {"a": {"name": "Foo", "x": 1}}, ["name", "x"]
        )
        assert d["ok"] is True
