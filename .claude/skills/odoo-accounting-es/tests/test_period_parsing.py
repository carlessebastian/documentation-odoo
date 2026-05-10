"""Tests para los parsers de periodos: run_aeat_report, recurring_invoice, vat_book."""
from __future__ import annotations

from datetime import date

import pytest

from _common import OdooError
from recurring_invoice import _next_period_label, _period_dates
from run_aeat_report import _period_to_dates as aeat_period
from vat_book import _period_to_oca as vat_book_period


class TestAeatPeriodToDates:
    def test_quarter(self):
        assert aeat_period("2026Q1") == ("2026-01-01", "2026-03-31", "1T")
        assert aeat_period("2026Q2") == ("2026-04-01", "2026-06-30", "2T")
        assert aeat_period("2026Q4") == ("2026-10-01", "2026-12-31", "4T")

    def test_month(self):
        assert aeat_period("2026-05") == ("2026-05-01", "2026-05-31", "05")
        assert aeat_period("2026-02") == ("2026-02-01", "2026-02-28", "02")
        # Bisiesto
        assert aeat_period("2024-02") == ("2024-02-01", "2024-02-29", "02")

    def test_year(self):
        assert aeat_period("2026") == ("2026-01-01", "2026-12-31", "0A")

    def test_invalid(self):
        with pytest.raises(OdooError):
            aeat_period("invalid")
        with pytest.raises(OdooError):
            aeat_period("2026Q5")
        with pytest.raises(OdooError):
            aeat_period("2026-13")


class TestVatBookPeriod:
    def test_quarter(self):
        assert vat_book_period("2026Q3") == (2026, "3T")

    def test_month(self):
        assert vat_book_period("2026-07") == (2026, "07")

    def test_year(self):
        assert vat_book_period("2026") == (2026, "0A")

    def test_invalid(self):
        with pytest.raises(OdooError):
            vat_book_period("malformed")


class TestRecurringInvoiceLabels:
    def test_monthly_label(self):
        assert _next_period_label(date(2026, 5, 10), "monthly") == "2026-05"

    def test_quarterly_label(self):
        assert _next_period_label(date(2026, 1, 10), "quarterly") == "2026Q1"
        assert _next_period_label(date(2026, 4, 1), "quarterly") == "2026Q2"
        assert _next_period_label(date(2026, 12, 31), "quarterly") == "2026Q4"

    def test_yearly_label(self):
        assert _next_period_label(date(2026, 6, 1), "yearly") == "2026"

    def test_invalid_freq(self):
        with pytest.raises(OdooError):
            _next_period_label(date(2026, 1, 1), "weekly")


class TestRecurringInvoiceDates:
    def test_monthly_dates(self):
        assert _period_dates(date(2026, 5, 10), "monthly") == (
            date(2026, 5, 1), date(2026, 5, 31)
        )

    def test_monthly_february_leap(self):
        assert _period_dates(date(2024, 2, 15), "monthly") == (
            date(2024, 2, 1), date(2024, 2, 29)
        )

    def test_quarterly_dates(self):
        assert _period_dates(date(2026, 5, 10), "quarterly") == (
            date(2026, 4, 1), date(2026, 6, 30)
        )
        assert _period_dates(date(2026, 11, 30), "quarterly") == (
            date(2026, 10, 1), date(2026, 12, 31)
        )

    def test_yearly_dates(self):
        assert _period_dates(date(2026, 7, 1), "yearly") == (
            date(2026, 1, 1), date(2026, 12, 31)
        )
