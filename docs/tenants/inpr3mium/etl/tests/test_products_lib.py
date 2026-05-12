"""Tests offline para `_products_lib.py` (loader 2 products + services)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from _products_lib import (
    build_product_vals,
    build_service_vals,
    extract_tax_key,
    index_by_id,
    load_products_and_services,
)
from holded_resolvers import HoldedResolvers


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeOdoo:
    """Stub minimo para load_products_and_services.

    Tablas en memoria:
      - account_tax: {description_pattern: tax_id}
      - account_account: {code: id}
      - product_template: {id: vals}
      - imd: list of {module, name, model, res_id}
    """

    def __init__(self, taxes=None, accounts=None):
        self.taxes = taxes or {}      # {"[holded: s_iva_21]": 6}
        self.accounts = accounts or {}  # {"705000": 551}
        self.products: dict[int, dict] = {}
        self.imd: list[dict] = []
        self.next_id = 1000
        self.calls = []

    def call(self, model, method, args=None, kwargs=None):
        self.calls.append((model, method, args, kwargs))
        args = args or []
        kwargs = kwargs or {}

        if model == "account.tax" and method == "search_read":
            domain = args[0]
            for t in domain:
                if t[0] == "description" and t[1] == "ilike":
                    pattern = t[2]
                    if pattern in self.taxes:
                        return [{"id": self.taxes[pattern]}]
                    return []
            return []

        if model == "account.account" and method == "search_read":
            domain = args[0]
            for t in domain:
                if t[0] == "code" and t[1] == "=":
                    code = t[2]
                    if code in self.accounts:
                        return [{"id": self.accounts[code], "account_type": "income"}]
                    return []
            return []

        if model == "product.template" and method == "create":
            vals = args[0]
            pid = self.next_id
            self.next_id += 1
            self.products[pid] = dict(vals)
            return pid

        if model == "product.template" and method == "write":
            ids, vals = args
            for i in ids:
                self.products[i].update(vals)
            return True

        if model == "ir.model.data" and method == "search_read":
            domain = args[0]
            mod = next((t[2] for t in domain if t[0] == "module"), None)
            nm = next((t[2] for t in domain if t[0] == "name"), None)
            for entry in self.imd:
                if entry["module"] == mod and entry["name"] == nm:
                    fields_req = kwargs.get("fields", ["res_id"])
                    return [{f: entry.get(f) for f in fields_req}]
            return []

        if model == "ir.model.data" and method == "create":
            vals = args[0]
            entry = {"id": self.next_id, **vals}
            self.imd.append(entry)
            self.next_id += 1
            return entry["id"]

        raise NotImplementedError(f"{model}.{method}")


def _write_jsonl(path: Path, records):
    with path.open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _make_dump(tmp_path, products=None, services=None, saleschannels=None, expensesaccount=None):
    dump_dir = tmp_path / "dump"
    dump_dir.mkdir()
    _write_jsonl(dump_dir / "products.jsonl", products or [])
    _write_jsonl(dump_dir / "services.jsonl", services or [])
    _write_jsonl(dump_dir / "saleschannels.jsonl", saleschannels or [])
    _write_jsonl(dump_dir / "expensesaccount.jsonl", expensesaccount or [])
    return dump_dir


# ---------------------------------------------------------------------------
# extract_tax_key
# ---------------------------------------------------------------------------


class TestExtractTaxKey:
    def test_single_key(self):
        assert extract_tax_key({"taxes": ["s_iva_21"]}) == ("s_iva_21", 1)

    def test_empty(self):
        assert extract_tax_key({"taxes": []}) == (None, 0)

    def test_missing(self):
        assert extract_tax_key({}) == (None, 0)

    def test_none(self):
        assert extract_tax_key({"taxes": None}) == (None, 0)

    def test_multi(self):
        assert extract_tax_key({"taxes": ["s_iva_21", "re_5_2"]}) == (None, 2)

    def test_strips(self):
        assert extract_tax_key({"taxes": ["  s_iva_21 "]}) == ("s_iva_21", 1)


# ---------------------------------------------------------------------------
# index_by_id
# ---------------------------------------------------------------------------


class TestIndexById:
    def test_basic(self):
        records = iter([
            {"id": "sc1", "name": "Canal A", "accountNum": 70500130001},
            {"id": "sc2", "name": "Canal B", "accountNum": 70500130002},
        ])
        assert index_by_id(records) == {"sc1": "70500130001", "sc2": "70500130002"}

    def test_skips_missing_accountnum(self):
        records = iter([
            {"id": "sc1", "name": "X"},
            {"id": "sc2", "accountNum": 70500130001},
        ])
        assert index_by_id(records) == {"sc2": "70500130001"}

    def test_skips_missing_id(self):
        records = iter([{"name": "X", "accountNum": 70500000000}])
        assert index_by_id(records) == {}

    def test_strips_int_to_str(self):
        # accountNum viene como int en dump real; debe stringificarse
        records = iter([{"id": "a", "accountNum": 70500000000}])
        out = index_by_id(records)
        assert out == {"a": "70500000000"}
        assert isinstance(out["a"], str)


# ---------------------------------------------------------------------------
# build_product_vals
# ---------------------------------------------------------------------------


class TestBuildProductVals:
    def test_minimal(self):
        record = {"id": "p1", "name": "Widget", "price": 10.0, "cost": 5.0}
        vals = build_product_vals(record, tax_id=None, income_account_id=None, expense_account_id=None)
        assert vals["name"] == "Widget"
        assert vals["type"] == "consu"
        assert vals["list_price"] == 10.0
        assert vals["standard_price"] == 5.0
        assert vals["sale_ok"] is True
        assert vals["purchase_ok"] is True
        assert "taxes_id" not in vals
        assert "property_account_income_id" not in vals
        assert "default_code" not in vals

    def test_full(self):
        record = {
            "id": "p1",
            "name": "Widget",
            "desc": "Mi widget mejor",
            "price": 10.0,
            "cost": 5.0,
            "sku": "WIDG-001",
            "barcode": "8412345678901",
            "weight": 2.5,
            "forSale": 1,
            "forPurchase": 1,
        }
        vals = build_product_vals(
            record,
            tax_id=6,
            income_account_id=551,
            expense_account_id=600,
        )
        assert vals["default_code"] == "WIDG-001"
        assert vals["barcode"] == "8412345678901"
        assert vals["weight"] == 2.5
        assert vals["taxes_id"] == [(6, 0, [6])]
        assert vals["property_account_income_id"] == 551
        assert vals["property_account_expense_id"] == 600
        assert vals["description_sale"] == "Mi widget mejor"

    def test_desc_same_as_name_omitted(self):
        record = {"name": "Widget", "desc": "Widget"}
        vals = build_product_vals(record, tax_id=None, income_account_id=None, expense_account_id=None)
        assert "description_sale" not in vals

    def test_no_sale_no_purchase(self):
        record = {"name": "X", "forSale": 0, "forPurchase": 0}
        vals = build_product_vals(record, tax_id=None, income_account_id=None, expense_account_id=None)
        assert vals["sale_ok"] is False
        assert vals["purchase_ok"] is False

    def test_empty_name_fallback(self):
        record = {"name": ""}
        vals = build_product_vals(record, tax_id=None, income_account_id=None, expense_account_id=None)
        assert vals["name"] == "(sin nombre)"

    def test_name_none_fallback(self):
        record = {"name": None}
        vals = build_product_vals(record, tax_id=None, income_account_id=None, expense_account_id=None)
        assert vals["name"] == "(sin nombre)"

    def test_weight_invalid_skipped(self):
        record = {"name": "X", "weight": "not-a-number"}
        vals = build_product_vals(record, tax_id=None, income_account_id=None, expense_account_id=None)
        assert "weight" not in vals

    def test_empty_sku_skipped(self):
        record = {"name": "X", "sku": "  "}
        vals = build_product_vals(record, tax_id=None, income_account_id=None, expense_account_id=None)
        assert "default_code" not in vals

    def test_zero_price_ok(self):
        record = {"name": "X", "price": 0}
        vals = build_product_vals(record, tax_id=None, income_account_id=None, expense_account_id=None)
        assert vals["list_price"] == 0.0


# ---------------------------------------------------------------------------
# build_service_vals
# ---------------------------------------------------------------------------


class TestBuildServiceVals:
    def test_minimal(self):
        record = {"id": "s1", "name": "Consultoria", "price": 100.0}
        vals = build_service_vals(record, tax_id=None, income_account_id=None)
        assert vals["name"] == "Consultoria"
        assert vals["type"] == "service"
        assert vals["list_price"] == 100.0
        assert "default_code" not in vals  # services no tienen sku
        assert "weight" not in vals

    def test_with_tax_and_account(self):
        record = {"id": "s1", "name": "Consultoria", "price": 100.0}
        vals = build_service_vals(record, tax_id=6, income_account_id=551)
        assert vals["taxes_id"] == [(6, 0, [6])]
        assert vals["property_account_income_id"] == 551


# ---------------------------------------------------------------------------
# Integration: load_products_and_services (dry-run + real con FakeOdoo)
# ---------------------------------------------------------------------------


class TestLoadProductsDryRun:
    def test_basic_dry_run(self, tmp_path):
        dump_dir = _make_dump(
            tmp_path,
            products=[
                {
                    "id": "p1",
                    "name": "Widget",
                    "price": 10,
                    "cost": 5,
                    "sku": "W1",
                    "taxes": ["s_iva_21"],
                    "salesChannelId": "sc1",
                    "expAccountId": "",
                    "forSale": 1,
                    "forPurchase": 1,
                },
            ],
            services=[
                {
                    "id": "s1",
                    "name": "Consultoria",
                    "price": 100,
                    "cost": 0,
                    "taxes": ["s_iva_21"],
                    "salesChannelId": "sc1",
                },
            ],
            saleschannels=[{"id": "sc1", "name": "Canal A", "accountNum": 70500130001}],
            expensesaccount=[],
        )
        client = FakeOdoo(
            taxes={"[holded: s_iva_21]": 6},
            accounts={"70500130001": 551},
        )
        resolvers = HoldedResolvers(client=client, tax_rules={})

        stats = load_products_and_services(
            client, resolvers, dump_dir, dry_run=True,
            report_dir=tmp_path / "reports",
        )

        assert stats.total_products == 1
        assert stats.total_services == 1
        assert stats.would_create == 2
        assert stats.would_update == 0
        assert stats.errors == 0
        assert stats.tax_unresolved == 0
        assert stats.no_income_account == 0
        # CSV emitido
        reports = list((tmp_path / "reports").glob("products_dryrun_*.csv"))
        assert len(reports) == 1

    def test_tax_unresolved_aborts_record(self, tmp_path):
        dump_dir = _make_dump(
            tmp_path,
            products=[{
                "id": "p1", "name": "X", "taxes": ["s_iva_inventada"],
                "salesChannelId": "", "expAccountId": "",
            }],
        )
        client = FakeOdoo(taxes={})  # tax no resoluble
        resolvers = HoldedResolvers(client=client, tax_rules={})

        stats = load_products_and_services(
            client, resolvers, dump_dir, dry_run=True,
            report_dir=tmp_path / "reports",
        )

        assert stats.tax_unresolved == 1
        assert stats.errors == 1
        assert stats.would_create == 0

    def test_no_tax_ok(self, tmp_path):
        # Los 33 products sin tax no abortan; se cargan sin taxes_id
        dump_dir = _make_dump(
            tmp_path,
            products=[{
                "id": "p1", "name": "X", "taxes": [],
                "salesChannelId": "", "expAccountId": "",
            }],
        )
        client = FakeOdoo()
        resolvers = HoldedResolvers(client=client, tax_rules={})

        stats = load_products_and_services(
            client, resolvers, dump_dir, dry_run=True,
            report_dir=tmp_path / "reports",
        )

        assert stats.no_tax == 1
        assert stats.errors == 0
        assert stats.would_create == 1

    def test_multi_tax_aborts(self, tmp_path):
        dump_dir = _make_dump(
            tmp_path,
            products=[{
                "id": "p1", "name": "X", "taxes": ["s_iva_21", "re_5_2"],
                "salesChannelId": "", "expAccountId": "",
            }],
        )
        client = FakeOdoo()
        resolvers = HoldedResolvers(client=client, tax_rules={})

        stats = load_products_and_services(
            client, resolvers, dump_dir, dry_run=True,
            report_dir=tmp_path / "reports",
        )

        assert stats.multi_tax == 1
        assert stats.errors == 1

    def test_income_account_not_in_index(self, tmp_path):
        # salesChannelId apunta a un sc que NO esta en saleschannels.jsonl
        dump_dir = _make_dump(
            tmp_path,
            products=[{
                "id": "p1", "name": "X", "taxes": ["s_iva_21"],
                "salesChannelId": "sc_inexistente", "expAccountId": "",
            }],
            saleschannels=[],
        )
        client = FakeOdoo(taxes={"[holded: s_iva_21]": 6})
        resolvers = HoldedResolvers(client=client, tax_rules={})

        stats = load_products_and_services(
            client, resolvers, dump_dir, dry_run=True,
            report_dir=tmp_path / "reports",
        )

        # No bloquea: el product se carga sin income account; se cuenta.
        assert stats.no_income_account == 1
        assert stats.would_create == 1
        assert stats.errors == 0

    def test_expense_account_resolved(self, tmp_path):
        dump_dir = _make_dump(
            tmp_path,
            products=[{
                "id": "p1", "name": "X", "taxes": ["s_iva_21"],
                "salesChannelId": "sc1", "expAccountId": "ea1",
            }],
            saleschannels=[{"id": "sc1", "name": "C", "accountNum": 70500130001}],
            expensesaccount=[{"id": "ea1", "name": "E", "accountNum": 62100000001}],
        )
        client = FakeOdoo(
            taxes={"[holded: s_iva_21]": 6},
            accounts={"70500130001": 551, "62100000001": 600},
        )
        resolvers = HoldedResolvers(client=client, tax_rules={})

        stats = load_products_and_services(
            client, resolvers, dump_dir, dry_run=True,
            report_dir=tmp_path / "reports",
        )

        assert stats.no_expense_account == 0
        assert stats.would_create == 1

    def test_limit(self, tmp_path):
        dump_dir = _make_dump(
            tmp_path,
            products=[
                {"id": f"p{i}", "name": f"X{i}", "taxes": ["s_iva_21"], "salesChannelId": "", "expAccountId": ""}
                for i in range(5)
            ],
            services=[
                {"id": f"s{i}", "name": f"S{i}", "taxes": ["s_iva_21"], "salesChannelId": ""}
                for i in range(3)
            ],
        )
        client = FakeOdoo(taxes={"[holded: s_iva_21]": 6})
        resolvers = HoldedResolvers(client=client, tax_rules={})

        stats = load_products_and_services(
            client, resolvers, dump_dir, dry_run=True, limit=2,
            report_dir=tmp_path / "reports",
        )

        # limit aplica a CADA archivo por separado
        assert stats.total_products == 2
        assert stats.total_services == 2

    def test_sku_collision_detected(self, tmp_path):
        dump_dir = _make_dump(
            tmp_path,
            products=[
                {"id": "p1", "name": "A", "sku": "DUP", "taxes": ["s_iva_21"], "salesChannelId": "", "expAccountId": ""},
                {"id": "p2", "name": "B", "sku": "DUP", "taxes": ["s_iva_21"], "salesChannelId": "", "expAccountId": ""},
            ],
        )
        client = FakeOdoo(taxes={"[holded: s_iva_21]": 6})
        resolvers = HoldedResolvers(client=client, tax_rules={})

        stats = load_products_and_services(
            client, resolvers, dump_dir, dry_run=True,
            report_dir=tmp_path / "reports",
        )

        assert stats.sku_collision == 1
        assert stats.would_create == 2  # ambos se cargan, no abortamos


class TestLoadProductsReal:
    def test_creates_via_ext_id(self, tmp_path, monkeypatch):
        # Inyectamos un fake `ext_id_upsert.upsert` en sys.modules ANTES de
        # llamar a load_products_and_services (importlib lazy import).
        import sys
        import types

        def fake_upsert(client, xmlid, model, vals, noupdate=True):
            # Crea + linka ext_id, retorna (res_id, "created")
            res_id = client.call(model, "create", [vals])
            module, name = xmlid.split(".", 1)
            client.call(
                "ir.model.data", "create",
                [{"module": module, "name": name, "model": model,
                  "res_id": res_id, "noupdate": noupdate}],
            )
            return (res_id, "created")

        mod = types.ModuleType("ext_id_upsert")
        mod.upsert = fake_upsert
        monkeypatch.setitem(sys.modules, "ext_id_upsert", mod)

        dump_dir = _make_dump(
            tmp_path,
            products=[
                {"id": "p1", "name": "Widget", "price": 10, "cost": 5,
                 "taxes": ["s_iva_21"], "salesChannelId": "sc1",
                 "expAccountId": "", "sku": "W1"},
            ],
            services=[
                {"id": "s1", "name": "Hours", "price": 50,
                 "taxes": ["s_iva_21"], "salesChannelId": "sc1"},
            ],
            saleschannels=[{"id": "sc1", "name": "C", "accountNum": 70500130001}],
        )
        client = FakeOdoo(
            taxes={"[holded: s_iva_21]": 6},
            accounts={"70500130001": 551},
        )
        resolvers = HoldedResolvers(client=client, tax_rules={})

        stats = load_products_and_services(
            client, resolvers, dump_dir, dry_run=False,
            report_dir=tmp_path / "reports",
        )

        assert stats.product_create == 1
        assert stats.service_create == 1
        assert stats.errors == 0
        # Verifica vals reales
        assert len(client.products) == 2
        pvals = next(v for v in client.products.values() if v["type"] == "consu")
        svals = next(v for v in client.products.values() if v["type"] == "service")
        assert pvals["taxes_id"] == [(6, 0, [6])]
        assert pvals["property_account_income_id"] == 551
        assert pvals["default_code"] == "W1"
        assert svals["taxes_id"] == [(6, 0, [6])]
        assert svals["property_account_income_id"] == 551
        assert "default_code" not in svals
