"""Tests para helpers puros de company_setup.py."""
from __future__ import annotations

import pytest

from _common import OdooError
from company_setup import detect_parent_cycle, normalize_vat


class TestNormalizeVat:
    def test_uppercases_and_strips(self):
        assert normalize_vat(" esB12345678 ") == "ESB12345678"

    def test_strips_dashes(self):
        assert normalize_vat("ES-B-12345678") == "ESB12345678"

    def test_rejects_no_country_code(self):
        with pytest.raises(OdooError):
            normalize_vat("12345678")

    def test_rejects_lowercase_only(self):
        # despues de upper queda valido si lleva codigo de pais
        assert normalize_vat("frb12345678") == "FRB12345678"

    def test_rejects_empty(self):
        with pytest.raises(OdooError):
            normalize_vat("")

    def test_rejects_with_special_chars(self):
        with pytest.raises(OdooError):
            normalize_vat("ES@B12345678")


class TestDetectParentCycle:
    """Mock OdooClient.read; cycle detection es logica pura."""

    class _StubClient:
        def __init__(self, parents: dict[int, int | None]) -> None:
            self.parents = parents

        def call(self, model, method, args, kwargs=None):
            assert model == "res.company"
            assert method == "read"
            ids = args[0]
            return [
                {
                    "id": i,
                    "parent_id": (
                        [self.parents[i], "X"] if self.parents.get(i) else False
                    ),
                }
                for i in ids
            ]

    def test_self_is_cycle(self):
        client = self._StubClient({})
        assert detect_parent_cycle(client, 1, 1) is True

    def test_no_cycle_simple_chain(self):
        # 3 -> 2 -> 1 -> None; poner 4 como parent de 5 no crea ciclo
        client = self._StubClient({1: None, 2: 1, 3: 2, 4: None, 5: None})
        assert detect_parent_cycle(client, 5, 4) is False

    def test_detects_cycle_via_chain(self):
        # 2 es padre de 1; intentar poner 1 como padre de 2 cierra ciclo
        client = self._StubClient({1: 2, 2: None})
        assert detect_parent_cycle(client, 2, 1) is True

    def test_long_chain_no_cycle(self):
        # 1 <- 2 <- 3 <- 4 <- 5; queremos meter 6 bajo 5
        client = self._StubClient({1: None, 2: 1, 3: 2, 4: 3, 5: 4, 6: None})
        assert detect_parent_cycle(client, 6, 5) is False

    def test_indirect_cycle(self):
        # 1 <- 2 <- 3; intentar poner 1 como padre de 3 (3 ya descendiente de 1)
        client = self._StubClient({1: None, 2: 1, 3: 2})
        assert detect_parent_cycle(client, 3, 1) is False
        # pero poner 3 como padre de 1 si crea ciclo
        assert detect_parent_cycle(client, 1, 3) is True
