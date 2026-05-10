"""Tests para helpers puros de ext_id_upsert.py."""
from __future__ import annotations

import pytest

from _common import OdooError
from ext_id_upsert import parse_xmlid


class TestParseXmlid:
    def test_basic(self):
        assert parse_xmlid("base.group_user") == ("base", "group_user")

    def test_custom_namespace(self):
        assert parse_xmlid("__custom__.user_maria") == ("__custom__", "user_maria")

    def test_rejects_no_dot(self):
        with pytest.raises(OdooError):
            parse_xmlid("group_user")

    def test_rejects_extra_dots(self):
        with pytest.raises(OdooError):
            parse_xmlid("base.sub.group_user")

    def test_rejects_starting_digit_module(self):
        with pytest.raises(OdooError):
            parse_xmlid("1base.group_user")

    def test_rejects_special_chars(self):
        with pytest.raises(OdooError):
            parse_xmlid("base.group-user")

    def test_accepts_underscores_and_digits(self):
        assert parse_xmlid("acme_admin.fp_intra_eu_2026") == (
            "acme_admin",
            "fp_intra_eu_2026",
        )
