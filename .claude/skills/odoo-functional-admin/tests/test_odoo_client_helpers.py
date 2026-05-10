"""Tests para helpers puros de odoo_client.py: _clean_fault."""
from __future__ import annotations

from odoo_client import _clean_fault


class TestCleanFault:
    def test_extracts_business_message(self):
        text = "UserError\n\nLa cuenta no esta configurada\n\nTraceback (most recent call last):\n  ..."
        assert _clean_fault(text) == "La cuenta no esta configurada"

    def test_returns_text_when_no_double_newline(self):
        assert _clean_fault("Simple error") == "Simple error"

    def test_returns_empty_for_none(self):
        assert _clean_fault(None) == ""
        assert _clean_fault("") == ""

    def test_strips_whitespace(self):
        text = "ValidationError\n\n  Asiento desbalanceado  \n\nTraceback..."
        assert _clean_fault(text) == "Asiento desbalanceado"
