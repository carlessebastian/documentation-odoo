"""Tests para validacion NIF/CIF/NIE en verify_es_compliance.py."""
from __future__ import annotations

import pytest

from verify_es_compliance import (
    _clean_vat,
    validate_cif,
    validate_dni,
    validate_es_vat,
    validate_nie,
)


class TestCleanVat:
    @pytest.mark.parametrize("inp,expected", [
        ("ES12345678Z", "12345678Z"),
        ("12345678Z", "12345678Z"),
        ("ES 12 345 678 Z", "12345678Z"),
        ("es12345678z", "12345678Z"),
        ("ES-B12345674", "B12345674"),
        ("ES.12345678.Z", "12345678Z"),
        ("", ""),
        (None, ""),
    ])
    def test_clean(self, inp, expected):
        assert _clean_vat(inp) == expected


class TestValidateDNI:
    @pytest.mark.parametrize("vat", [
        "12345678Z",   # 12345678 % 23 = 14 -> Z
        "00000001R",   # 1 % 23 = 1 -> R
        "00000023T",   # 23 % 23 = 0 -> T
    ])
    def test_valid(self, vat):
        assert validate_dni(vat), f"Should validate: {vat}"

    @pytest.mark.parametrize("vat", [
        "12345678A",   # control digit incorrect
        "1234567Z",    # too short
        "123456789Z",  # too long
        "12345678",    # missing letter
        "ABCDEFGHI",   # not digits
    ])
    def test_invalid(self, vat):
        assert not validate_dni(vat), f"Should NOT validate: {vat}"


class TestValidateNIE:
    @pytest.mark.parametrize("vat", [
        "X1234567L",   # X=0, 1234567 % 23 = 19 -> L
        "Y0000000Z",   # Y=1, 10000000 % 23 = 14 -> Z
        "Z0000000M",   # Z=2, 20000000 % 23 = 5 -> M
    ])
    def test_valid(self, vat):
        assert validate_nie(vat), f"Should validate: {vat}"

    @pytest.mark.parametrize("vat", [
        "X1234567A",   # bad control
        "A1234567L",   # not X/Y/Z
        "X12345678",   # missing letter
    ])
    def test_invalid(self, vat):
        assert not validate_nie(vat), f"Should NOT validate: {vat}"


class TestValidateCIF:
    @pytest.mark.parametrize("vat", [
        "B12345674",   # B (digit control), control = 4
        "A28015865",   # Telefonica historica (publica)
        "K1234567D",   # K (letter control), table[4] = D
    ])
    def test_valid(self, vat):
        assert validate_cif(vat), f"Should validate: {vat}"

    @pytest.mark.parametrize("vat", [
        "B12345670",   # B with wrong digit
        "I12345674",   # I not in valid CIF prefix list
        "B1234567",    # too short
        "1234567A8",   # starts with digit
    ])
    def test_invalid(self, vat):
        assert not validate_cif(vat), f"Should NOT validate: {vat}"


class TestValidateESVat:
    @pytest.mark.parametrize("vat,expected_kind", [
        ("ES12345678Z", "DNI"),
        ("12345678Z", "DNI"),
        ("X1234567L", "NIE"),
        ("ESX1234567L", "NIE"),
        ("B12345674", "CIF"),
    ])
    def test_classify_valid(self, vat, expected_kind):
        ok, kind = validate_es_vat(vat)
        assert ok and kind == expected_kind

    @pytest.mark.parametrize("vat", [
        "",
        "INVALID",
        "12345678",
        "ES",
    ])
    def test_invalid(self, vat):
        ok, _ = validate_es_vat(vat)
        assert not ok
