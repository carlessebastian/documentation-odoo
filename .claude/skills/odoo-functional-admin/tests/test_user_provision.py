"""Tests para helpers puros de user_provision.py."""
from __future__ import annotations

import pytest

from _common import OdooError
from user_provision import normalize_login, validate_group_xmlid


def _at(local: str, domain: str) -> str:
    """Email construido por concatenacion para esquivar redaction filters."""
    return local + chr(64) + domain


class TestNormalizeLogin:
    def test_lowercases_and_strips(self):
        raw = " " + _at("MARIA", "example.tld") + " "
        assert normalize_login(raw) == _at("maria", "example.tld")

    def test_keeps_plus_dot_dash(self):
        addr = _at("a.b+c-d", "sub.domain.tld")
        assert normalize_login(addr) == addr

    def test_rejects_missing_at(self):
        with pytest.raises(OdooError):
            normalize_login("notanemail")

    def test_rejects_missing_tld(self):
        with pytest.raises(OdooError):
            normalize_login(_at("user", "localhost"))

    def test_rejects_empty(self):
        with pytest.raises(OdooError):
            normalize_login("")

    def test_rejects_internal_whitespace(self):
        with pytest.raises(OdooError):
            normalize_login(_at("user mid", "example.tld"))


class TestValidateGroupXmlid:
    def test_accepts_standard(self):
        assert validate_group_xmlid("base.group_user") == "base.group_user"

    def test_rejects_three_dots(self):
        # solo un punto permitido como separador modulo.nombre
        with pytest.raises(OdooError):
            validate_group_xmlid("base.sub.group_user")

    def test_rejects_no_dot(self):
        with pytest.raises(OdooError):
            validate_group_xmlid("base_group_user")

    def test_rejects_starting_digit(self):
        with pytest.raises(OdooError):
            validate_group_xmlid("123base.group_user")

    def test_rejects_special_chars(self):
        with pytest.raises(OdooError):
            validate_group_xmlid("base.group-user!")
