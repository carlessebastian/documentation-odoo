"""Tests para helpers puros de record_rule_create.py."""
from __future__ import annotations

import pytest

from _common import OdooError
from record_rule_create import (
    HIGH_RISK_MODELS,
    parse_perms,
    validate_domain_syntax,
)


class TestParsePerms:
    def test_default(self):
        assert parse_perms("r,w,c") == {
            "perm_read": True,
            "perm_write": True,
            "perm_create": True,
            "perm_unlink": False,
        }

    def test_full(self):
        assert parse_perms("r,w,c,u")["perm_unlink"] is True

    def test_only_read(self):
        p = parse_perms("r")
        assert p["perm_read"] is True
        assert p["perm_write"] is False
        assert p["perm_unlink"] is False

    def test_handles_whitespace(self):
        assert parse_perms("r, w , c") == parse_perms("r,w,c")

    def test_rejects_unknown(self):
        with pytest.raises(OdooError):
            parse_perms("x")

    def test_rejects_mixed(self):
        with pytest.raises(OdooError):
            parse_perms("r,foo,c")


class TestValidateDomainSyntax:
    def test_simple(self):
        validate_domain_syntax("[('user_id','=',user.id)]")

    def test_or(self):
        validate_domain_syntax(
            "['|', ('company_id','=',False), ('company_id','in',company_ids)]"
        )

    def test_empty_list(self):
        validate_domain_syntax("[]")

    def test_rejects_syntax_error(self):
        with pytest.raises(OdooError):
            validate_domain_syntax("[('field','=',user.id")

    def test_rejects_non_list(self):
        with pytest.raises(OdooError):
            validate_domain_syntax("{'field': 'x'}")

    def test_rejects_string(self):
        with pytest.raises(OdooError):
            validate_domain_syntax("'just a string'")


class TestHighRiskSet:
    def test_includes_users_companies_rules(self):
        for m in ("res.users", "res.company", "ir.rule", "ir.model.access"):
            assert m in HIGH_RISK_MODELS

    def test_excludes_normal_models(self):
        for m in ("res.partner", "account.move", "crm.lead", "sale.order"):
            assert m not in HIGH_RISK_MODELS
