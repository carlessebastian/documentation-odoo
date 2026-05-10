"""Tests para helpers puros de settings_param.py."""
from __future__ import annotations

import pytest

from _common import OdooError
from settings_param import PROTECTED_KEYS, validate_key


class TestValidateKey:
    def test_simple_dotted(self):
        assert validate_key("web.base.url") == "web.base.url"

    def test_with_underscore_and_dash(self):
        assert validate_key("my_module.flag-x") == "my_module.flag-x"

    def test_rejects_starting_digit(self):
        with pytest.raises(OdooError):
            validate_key("1.bad.key")

    def test_rejects_special(self):
        with pytest.raises(OdooError):
            validate_key("foo bar")

    def test_rejects_protected(self):
        with pytest.raises(OdooError):
            validate_key("database.uuid")

    def test_protected_set_known(self):
        assert "database.uuid" in PROTECTED_KEYS
        assert "database.secret" in PROTECTED_KEYS
