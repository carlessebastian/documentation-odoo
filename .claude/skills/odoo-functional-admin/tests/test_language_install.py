"""Tests para helpers puros de language_install.py."""
from __future__ import annotations

import pytest

from _common import OdooError
from language_install import validate_lang_code


class TestValidateLangCode:
    def test_es(self):
        assert validate_lang_code("es_ES") == "es_ES"

    def test_ca(self):
        assert validate_lang_code("ca_ES") == "ca_ES"

    def test_pt_br(self):
        assert validate_lang_code("pt_BR") == "pt_BR"

    def test_three_letter_lang(self):
        assert validate_lang_code("nrm") == "nrm"  # Norman, ISO 639-3

    def test_lang_only(self):
        assert validate_lang_code("eu") == "eu"

    def test_rejects_uppercase_lang(self):
        with pytest.raises(OdooError):
            validate_lang_code("ES_ES")

    def test_rejects_lowercase_country(self):
        with pytest.raises(OdooError):
            validate_lang_code("es_es")

    def test_rejects_no_separator(self):
        with pytest.raises(OdooError):
            validate_lang_code("esES")

    def test_rejects_dash(self):
        with pytest.raises(OdooError):
            validate_lang_code("es-ES")
