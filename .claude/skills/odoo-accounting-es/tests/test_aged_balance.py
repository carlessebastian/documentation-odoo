"""Tests para la funcion _bucket de aged_balance.py."""
from __future__ import annotations

from datetime import date

import pytest

from aged_balance import _bucket


class TestBucket:
    @pytest.fixture
    def today(self):
        return date(2026, 5, 10)

    @pytest.mark.parametrize("due,expected", [
        ("2026-05-15", "not_due"),    # vence en el futuro
        ("2026-05-10", "not_due"),    # vence hoy
        ("2026-05-05", "1-30"),       # 5 dias vencido
        ("2026-04-10", "1-30"),       # 30 dias vencido
        ("2026-04-09", "31-60"),      # 31 dias
        ("2026-03-11", "31-60"),      # 60 dias
        ("2026-03-10", "61-90"),      # 61 dias
        ("2026-02-09", "61-90"),      # 90 dias
        ("2026-02-08", "+90"),        # 91 dias
        ("2025-01-01", "+90"),        # muy viejo
    ])
    def test_buckets(self, due, expected, today):
        assert _bucket(due, today) == expected

    def test_none_means_not_due(self, today):
        assert _bucket(None, today) == "not_due"

    def test_accepts_iso_with_time(self, today):
        assert _bucket("2026-04-10T15:00:00", today) == "1-30"
