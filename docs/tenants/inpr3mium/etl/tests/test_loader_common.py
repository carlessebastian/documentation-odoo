"""Tests offline para `_loader_common.py`.

Usan un FakeClient en memoria para simular `account.account` +
`ir.model.data`. No tocan red ni filesystem mas alla de un tmp_path.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from _loader_common import LoadStats, iter_jsonl, load_accounts


# ---------------------------------------------------------------------------
# Fake Odoo client en memoria
# ---------------------------------------------------------------------------


class FakeOdoo:
    """Stub minimo que cubre los calls de _loader_common.

    Mantiene dos "tablas":
      - account_account: {code: {id, code, name, account_type}}
      - ir_model_data:   [{module, name, model, res_id}, ...]
    """

    def __init__(self, seed_accounts: list[dict]) -> None:
        self.accounts: dict[str, dict] = {}
        self.next_id = 1000
        for acc in seed_accounts:
            self.accounts[acc["code"]] = {**acc, "id": self.next_id}
            self.next_id += 1
        self.imd: list[dict] = []
        self.calls: list[tuple] = []

    def call(self, model, method, args=None, kwargs=None):
        self.calls.append((model, method, args, kwargs))
        args = args or []
        kwargs = kwargs or {}

        if model == "account.account" and method == "search_read":
            domain = args[0]
            fields = kwargs.get("fields", [])
            # Solo soportamos [('code', 'in', [...])] y [('code', '=', X)]
            for tup in domain:
                if tup[0] == "code" and tup[1] == "in":
                    codes = tup[2]
                    return [
                        {f: self.accounts[c].get(f) for f in fields}
                        for c in codes
                        if c in self.accounts
                    ]
                if tup[0] == "code" and tup[1] == "=":
                    c = tup[2]
                    if c in self.accounts:
                        return [{f: self.accounts[c].get(f) for f in fields}]
                    return []
            return []

        if model == "account.account" and method == "create":
            vals = args[0]
            self.accounts[vals["code"]] = {**vals, "id": self.next_id}
            self.next_id += 1
            return self.accounts[vals["code"]]["id"]

        if model == "account.account" and method == "write":
            ids, vals = args
            for code, acc in self.accounts.items():
                if acc["id"] in ids:
                    acc.update(vals)
            return True

        if model == "ir.model.data" and method == "search_read":
            domain = args[0]
            mod = next(t[2] for t in domain if t[0] == "module")
            nm = next(t[2] for t in domain if t[0] == "name")
            for entry in self.imd:
                if entry["module"] == mod and entry["name"] == nm:
                    fields = kwargs.get("fields", ["res_id"])
                    return [{f: entry.get(f) for f in fields}]
            return []

        if model == "ir.model.data" and method == "create":
            vals = args[0]
            entry = {"id": self.next_id, **vals}
            self.imd.append(entry)
            self.next_id += 1
            return entry["id"]

        raise NotImplementedError(f"{model}.{method}({args!r}, {kwargs!r})")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _make_dump(tmp_path: Path, source: str, records: list[dict]) -> Path:
    dump_dir = tmp_path / "dump"
    dump_dir.mkdir()
    _write_jsonl(dump_dir / f"{source}.jsonl", records)
    return dump_dir


def _seed_pgce_parents() -> list[dict]:
    """Padres PGCE Pymes minimos para los tests."""
    return [
        {"code": "600000", "name": "Compras", "account_type": "expense"},
        {"code": "621000", "name": "Arrendamientos", "account_type": "expense"},
        {"code": "623000", "name": "Servicios profesionales", "account_type": "expense"},
        {"code": "630000", "name": "Impuesto beneficios", "account_type": "expense"},
        {"code": "700000", "name": "Ventas mercaderias", "account_type": "income"},
        {"code": "705000", "name": "Prestaciones servicios", "account_type": "income"},
        {"code": "708000", "name": "Devoluciones ventas", "account_type": "income"},
    ]


# ---------------------------------------------------------------------------
# iter_jsonl
# ---------------------------------------------------------------------------


class TestIterJsonl:
    def test_reads_all(self, tmp_path):
        p = tmp_path / "x.jsonl"
        _write_jsonl(p, [{"a": 1}, {"a": 2}])
        assert list(iter_jsonl(p)) == [{"a": 1}, {"a": 2}]

    def test_skips_blank_lines(self, tmp_path):
        p = tmp_path / "x.jsonl"
        p.write_text('{"a":1}\n\n  \n{"a":2}\n')
        assert list(iter_jsonl(p)) == [{"a": 1}, {"a": 2}]

    def test_limit(self, tmp_path):
        p = tmp_path / "x.jsonl"
        _write_jsonl(p, [{"a": i} for i in range(10)])
        assert list(iter_jsonl(p, limit=3)) == [{"a": 0}, {"a": 1}, {"a": 2}]


# ---------------------------------------------------------------------------
# load_accounts (dry-run y real)
# ---------------------------------------------------------------------------


class TestLoadAccountsDryRun:
    def test_all_would_create(self, tmp_path):
        records = [
            {"id": "h1", "name": " Alquiler", "accountNum": 62100000001, "color": "#fff"},
            {"id": "h2", "name": " Asesoria", "accountNum": 62300000010, "color": "#fff"},
            {"id": "h3", "name": " IS diferido", "accountNum": 63010000002, "color": "#fff"},
        ]
        dump_dir = _make_dump(tmp_path, "expensesaccount", records)
        client = FakeOdoo(_seed_pgce_parents())

        stats = load_accounts(
            client, dump_dir, "expensesaccount", dry_run=True,
            report_dir=tmp_path / "reports",
        )
        assert stats.total == 3
        assert stats.would_create == 3
        assert stats.would_update == 0
        assert stats.errors == 0

    def test_existing_ext_id_would_update(self, tmp_path):
        records = [{"id": "h1", "name": "Alq", "accountNum": 62100000001}]
        dump_dir = _make_dump(tmp_path, "expensesaccount", records)
        client = FakeOdoo(_seed_pgce_parents())
        # Simular que ya existe el ext_id (run anterior).
        client.imd.append({
            "module": "__holded__",
            "name": "account_62100000001",
            "model": "account.account",
            "res_id": 999,
        })

        stats = load_accounts(
            client, dump_dir, "expensesaccount", dry_run=True,
            report_dir=tmp_path / "reports",
        )
        assert stats.would_create == 0
        assert stats.would_update == 1

    def test_unresolvable_parent_chapter(self, tmp_path):
        # Chapter 1XX no esta en PGCE_FALLBACK_CHAPTERS
        records = [{"id": "h1", "name": "Capital", "accountNum": 10000000001}]
        dump_dir = _make_dump(tmp_path, "expensesaccount", records)
        client = FakeOdoo(_seed_pgce_parents())

        stats = load_accounts(
            client, dump_dir, "expensesaccount", dry_run=True,
            report_dir=tmp_path / "reports",
        )
        assert stats.errors == 1
        assert stats.error_details[0][0] == "10000000001"
        assert "derive_pgce_parent" in stats.error_details[0][1]

    def test_parent_missing_in_odoo(self, tmp_path):
        # 65X mapea a 650000 via fallback, pero el seed no incluye 650000
        records = [{"id": "h1", "name": "Incobrables", "accountNum": 65000000001}]
        dump_dir = _make_dump(tmp_path, "expensesaccount", records)
        client = FakeOdoo(_seed_pgce_parents())  # no incluye 650000

        stats = load_accounts(
            client, dump_dir, "expensesaccount", dry_run=True,
            report_dir=tmp_path / "reports",
        )
        assert stats.errors == 1
        assert "650000" in stats.error_details[0][1]

    def test_limit(self, tmp_path):
        records = [
            {"id": f"h{i}", "name": "x", "accountNum": 62100000000 + i}
            for i in range(10)
        ]
        dump_dir = _make_dump(tmp_path, "expensesaccount", records)
        client = FakeOdoo(_seed_pgce_parents())

        stats = load_accounts(
            client, dump_dir, "expensesaccount", dry_run=True, limit=3,
            report_dir=tmp_path / "reports",
        )
        assert stats.total == 3

    def test_emits_csv_report(self, tmp_path):
        records = [{"id": "h1", "name": "x", "accountNum": 62100000001}]
        dump_dir = _make_dump(tmp_path, "expensesaccount", records)
        report_dir = tmp_path / "reports"
        client = FakeOdoo(_seed_pgce_parents())

        load_accounts(
            client, dump_dir, "expensesaccount", dry_run=True,
            report_dir=report_dir,
        )
        csvs = list(report_dir.glob("expensesaccount_dryrun_*.csv"))
        assert len(csvs) == 1
        content = csvs[0].read_text()
        assert "accountNum" in content
        assert "62100000001" in content
        assert "would_create" in content

    def test_saleschannels_source_works(self, tmp_path):
        records = [
            {"id": "s1", "name": "Cuota FT", "accountNum": 70800111902},
            {"id": "s2", "name": "Servicios", "accountNum": 70500000001},
        ]
        dump_dir = _make_dump(tmp_path, "saleschannels", records)
        client = FakeOdoo(_seed_pgce_parents())

        stats = load_accounts(
            client, dump_dir, "saleschannels", dry_run=True,
            report_dir=tmp_path / "reports",
        )
        assert stats.total == 2
        assert stats.would_create == 2


class TestLoadAccountsErrors:
    def test_missing_source_file(self, tmp_path):
        dump_dir = tmp_path / "empty"
        dump_dir.mkdir()
        client = FakeOdoo([])
        with pytest.raises(FileNotFoundError):
            load_accounts(client, dump_dir, "expensesaccount", dry_run=True)
