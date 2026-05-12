"""Tests offline para `_invoices_lib.py` (loader 3 invoices out_invoice)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from _invoices_lib import (
    SALES_PREFIXES,
    STATUS_CANCELLED,
    STATUS_DRAFT,
    STATUS_POSTED,
    build_invoice_header_vals,
    build_invoice_line_vals,
    extract_item_tax_key,
    load_invoices,
    parse_doc_prefix,
    should_skip_doc,
)
from holded_resolvers import HoldedResolvers


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeOdoo:
    """Stub minimo para load_invoices.

    Models en memoria:
      - account.tax: {description_pattern: tax_id}
      - account.account: {code: id}
      - account.move: {id: vals (incluye state='draft')}
      - account.journal: {code: id}
      - product.template: {id: variant_id}
      - imd: list of {module, name, model, res_id}
    Bot uid asumido OK para todos los modelos.
    """

    def __init__(self, *, taxes=None, accounts=None, journals=None,
                 partners=None, templates=None):
        self.taxes = taxes or {}
        self.accounts = accounts or {}
        self.journals = journals or {}      # {code: journal_id}
        self.partners = partners or {}      # {holded_id: res.partner.id}
        self.templates = templates or {}    # {template_id: variant_id}
        self.moves: dict[int, dict] = {}
        self.imd: list[dict] = []
        self.next_id = 5000
        self.calls = []
        # Pre-popular imd con partners y templates
        for hid, pid in self.partners.items():
            self.imd.append({"module": "__holded__", "name": f"contact_{hid}",
                            "model": "res.partner", "res_id": pid})
        for hid, vid in self.templates.items():
            # name puede ser product_<hid> o service_<hid>; aceptamos ambos
            self.imd.append({"module": "__holded__", "name": f"product_{hid}",
                            "model": "product.template", "res_id": hid})

    def _next(self):
        n = self.next_id
        self.next_id += 1
        return n

    def call(self, model, method, args=None, kwargs=None):
        self.calls.append((model, method, args, kwargs))
        args = args or []
        kwargs = kwargs or {}

        if model == "account.tax" and method == "search_read":
            domain = args[0]
            for t in domain:
                if t[0] == "description" and t[1] == "ilike":
                    p = t[2]
                    if p in self.taxes:
                        return [{"id": self.taxes[p]}]
                    return []
            return []

        if model == "account.account" and method == "search_read":
            domain = args[0]
            for t in domain:
                if t[0] == "code" and t[1] == "=":
                    c = t[2]
                    if c in self.accounts:
                        return [{"id": self.accounts[c], "account_type": "income"}]
                    return []
            return []

        if model == "account.journal" and method == "search_read":
            domain = args[0]
            for t in domain:
                if t[0] == "code" and t[1] == "in":
                    return [{"code": c, "id": self.journals[c]}
                            for c in t[2] if c in self.journals]
            return []

        if model == "ir.model.data" and method == "search_read":
            domain = args[0]
            mod = next((t[2] for t in domain if t[0] == "module"), None)
            model_f = next((t[2] for t in domain if t[0] == "model"), None)
            # Soporta "name = X" y "name in [X,...]"
            name_eq = next((t[2] for t in domain if t[0] == "name" and t[1] == "="), None)
            name_in = next((t[2] for t in domain if t[0] == "name" and t[1] == "in"), None)
            fields_req = kwargs.get("fields", ["res_id"])
            out = []
            for e in self.imd:
                if mod and e["module"] != mod:
                    continue
                if model_f and e["model"] != model_f:
                    continue
                if name_eq and e["name"] != name_eq:
                    continue
                if name_in and e["name"] not in name_in:
                    continue
                out.append({f: e.get(f) for f in fields_req})
            if kwargs.get("limit"):
                out = out[:kwargs["limit"]]
            return out

        if model == "ir.model.data" and method == "create":
            vals = args[0]
            e = {"id": self._next(), **vals}
            self.imd.append(e)
            return e["id"]

        if model == "product.template" and method == "read":
            ids, fields = args[0], args[1] if len(args) > 1 else None
            out = []
            for i in ids:
                if i in self.templates:
                    out.append({"id": i, "product_variant_id": [self.templates[i], f"var{i}"]})
            return out

        if model == "account.move" and method == "read":
            ids = args[0]
            fields = args[1] if len(args) > 1 else None
            out = []
            for i in ids:
                if i in self.moves:
                    rec = dict(self.moves[i])
                    rec["id"] = i
                    if fields:
                        rec = {f: rec.get(f, False) for f in fields}
                        rec["id"] = i
                    out.append(rec)
            return out

        if model == "account.move" and method == "create":
            vals = args[0]
            i = self._next()
            self.moves[i] = dict(vals)
            self.moves[i]["state"] = "draft"
            return i

        if model == "account.move" and method == "write":
            ids, vals = args
            for i in ids:
                self.moves[i].update(vals)
            return True

        if model == "account.move" and method == "action_post":
            ids = args[0]
            for i in ids:
                self.moves[i]["state"] = "posted"
            return True

        raise NotImplementedError(f"{model}.{method}({args!r}, {kwargs!r})")


def _write_jsonl(path: Path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _make_dump(tmp_path, invoices=None, saleschannels=None):
    dump_dir = tmp_path / "dump"
    (dump_dir / "documents").mkdir(parents=True)
    _write_jsonl(dump_dir / "documents" / "invoice.jsonl", invoices or [])
    _write_jsonl(dump_dir / "saleschannels.jsonl", saleschannels or [])
    return dump_dir


# ---------------------------------------------------------------------------
# parse_doc_prefix
# ---------------------------------------------------------------------------


class TestParseDocPrefix:
    @pytest.mark.parametrize("doc,expected", [
        ("A-007566", "A-"),
        ("AC-0001", "AC-"),
        ("L-0001", "L-"),
        ("FVU-25-7", "FVU-"),
        ("PB-/2025/01/0001", "PB-"),
        ("a-007", "A-"),
        ("", None),
        (None, None),
        ("12345", None),
    ])
    def test_parses(self, doc, expected):
        assert parse_doc_prefix(doc) == expected


# ---------------------------------------------------------------------------
# should_skip_doc
# ---------------------------------------------------------------------------


class TestShouldSkipDoc:
    def test_ok_invoice(self):
        d = {"contact": "abc", "docNumber": "A-001", "status": 1}
        assert should_skip_doc(d) == (False, "")

    def test_skip_status_cancelled(self):
        d = {"contact": "abc", "docNumber": "A-001", "status": STATUS_CANCELLED}
        assert should_skip_doc(d) == (True, "cancelled")

    def test_skip_no_contact(self):
        d = {"contact": "", "docNumber": "A-001", "status": 1}
        assert should_skip_doc(d) == (True, "no_contact")

    def test_skip_r_prefix(self):
        # R- no esta en SALES_PREFIXES
        d = {"contact": "abc", "docNumber": "R-000005", "status": 1}
        assert should_skip_doc(d) == (True, "unmapped_prefix")

    def test_skip_no_dash(self):
        d = {"contact": "abc", "docNumber": "12345", "status": 1}
        assert should_skip_doc(d) == (True, "unmapped_prefix")

    def test_status_0_draft_not_skipped(self):
        d = {"contact": "abc", "docNumber": "A-001", "status": STATUS_DRAFT}
        assert should_skip_doc(d) == (False, "")


# ---------------------------------------------------------------------------
# extract_item_tax_key
# ---------------------------------------------------------------------------


class TestExtractItemTaxKey:
    def test_single(self):
        assert extract_item_tax_key({"taxes": ["s_iva_21"]}) == ("s_iva_21", 1)

    def test_empty(self):
        assert extract_item_tax_key({"taxes": []}) == (None, 0)
        assert extract_item_tax_key({}) == (None, 0)

    def test_multi(self):
        assert extract_item_tax_key({"taxes": ["s_iva_21", "re_5_2"]}) == (None, 2)


# ---------------------------------------------------------------------------
# build_invoice_header_vals
# ---------------------------------------------------------------------------


class TestBuildHeaderVals:
    def test_minimal(self):
        doc = {"id": "x", "contact": "c", "docNumber": "A-001",
               "date": 1546210800, "status": 1}
        v = build_invoice_header_vals(doc, partner_id=10, journal_id=7)
        assert v["move_type"] == "out_invoice"
        assert v["partner_id"] == 10
        assert v["journal_id"] == 7
        assert v["ref"] == "A-001"
        assert v["invoice_date"] == "2018-12-31"
        assert v["date"] == "2018-12-31"  # accountingDate ausente -> usa date
        assert "invoice_date_due" not in v

    def test_with_due_and_accounting(self):
        doc = {"id": "x", "contact": "c", "docNumber": "A-002",
               "date": 1546210800, "dueDate": 1551398400,
               "accountingDate": 1548979200, "status": 1}
        v = build_invoice_header_vals(doc, partner_id=10, journal_id=7)
        assert v["invoice_date"] == "2018-12-31"
        assert v["date"] == "2019-02-01"  # accountingDate
        assert v["invoice_date_due"] == "2019-03-01"

    def test_narration_from_desc_notes(self):
        doc = {"id": "x", "contact": "c", "docNumber": "A-001",
               "date": 1546210800, "status": 1,
               "desc": "Factura X", "notes": "Notas extra"}
        v = build_invoice_header_vals(doc, partner_id=1, journal_id=1)
        assert "Factura X" in v["narration"]
        assert "Notas extra" in v["narration"]

    def test_narration_omits_if_equal_to_ref(self):
        doc = {"id": "x", "contact": "c", "docNumber": "A-001",
               "date": 1546210800, "status": 1, "desc": "A-001", "notes": ""}
        v = build_invoice_header_vals(doc, partner_id=1, journal_id=1)
        assert "narration" not in v

    def test_company_id(self):
        doc = {"id": "x", "contact": "c", "docNumber": "A-001",
               "date": 1546210800, "status": 1}
        v = build_invoice_header_vals(doc, partner_id=10, journal_id=7, company_id=3)
        assert v["company_id"] == 3

    def test_name_preserves_holded_docnumber(self):
        # Politica operador inpr3mium 2026-05-12: name = docNumber Holded
        # literal para preservar correlatividad AEAT.
        doc = {"id": "x", "contact": "c", "docNumber": "A-007566",
               "date": 1546210800, "status": 1}
        v = build_invoice_header_vals(doc, partner_id=10, journal_id=7)
        assert v["name"] == "A-007566"
        assert v["ref"] == "A-007566"

    def test_use_holded_number_false_omits_name(self):
        doc = {"id": "x", "contact": "c", "docNumber": "A-007566",
               "date": 1546210800, "status": 1}
        v = build_invoice_header_vals(doc, partner_id=10, journal_id=7,
                                      use_holded_number=False)
        assert "name" not in v
        assert v["ref"] == "A-007566"

    def test_duplicate_omits_name_adds_narration_warn(self):
        doc = {"id": "loser_id", "contact": "c", "docNumber": "L-000719",
               "date": 1546210800, "status": 1}
        v = build_invoice_header_vals(doc, partner_id=10, journal_id=7,
                                      duplicate_alt_id="winner_id")
        assert "name" not in v
        assert v["ref"] == "L-000719"
        assert "WARN duplicado" in v["narration"]
        assert "winner_id" in v["narration"]


# ---------------------------------------------------------------------------
# build_invoice_line_vals
# ---------------------------------------------------------------------------


class TestBuildLineVals:
    def test_minimal(self):
        item = {"name": "X", "units": 1, "price": 100.0, "taxes": ["s_iva_21"]}
        v = build_invoice_line_vals(item, product_id=None, account_id=None, tax_id=6)
        assert v["quantity"] == 1.0
        assert v["price_unit"] == 100.0
        assert v["tax_ids"] == [(6, 0, [6])]
        assert v["discount"] == 0.0
        assert "product_id" not in v
        assert "account_id" not in v

    def test_negative_units_preserved(self):
        item = {"name": "Discount", "units": -1, "price": 50.0,
                "desc": "Descuento"}
        v = build_invoice_line_vals(item, product_id=None, account_id=None, tax_id=None)
        assert v["quantity"] == -1.0
        assert v["price_unit"] == 50.0
        # tax_id None: tax_ids = [(6,0,[])] para NO heredar default
        assert v["tax_ids"] == [(6, 0, [])]

    def test_with_product_account_tax(self):
        item = {"desc": "Line", "units": 2, "price": 25.0, "discount": 10.0}
        v = build_invoice_line_vals(item, product_id=42, account_id=551, tax_id=6)
        assert v["product_id"] == 42
        assert v["account_id"] == 551
        assert v["tax_ids"] == [(6, 0, [6])]
        assert v["discount"] == 10.0

    def test_name_from_desc_priority(self):
        item = {"name": "Header repetido", "desc": "Descripcion linea",
                "units": 1, "price": 10}
        v = build_invoice_line_vals(item, product_id=None, account_id=None, tax_id=None)
        assert v["name"] == "Descripcion linea"

    def test_name_fallback_slash(self):
        item = {"name": "", "desc": "", "units": 1, "price": 10}
        v = build_invoice_line_vals(item, product_id=None, account_id=None, tax_id=None)
        assert v["name"] == "/"


# ---------------------------------------------------------------------------
# Integration: load_invoices con FakeOdoo
# ---------------------------------------------------------------------------


class TestLoadInvoicesDryRun:
    def test_basic(self, tmp_path):
        invoices = [{
            "id": "doc1",
            "contact": "c1",
            "docNumber": "A-100",
            "date": 1546210800,
            "status": 1,
            "total": 121.0, "tax": 21.0,
            "products": [{"name": "X", "desc": "X", "units": 1, "price": 100.0,
                          "taxes": ["s_iva_21"], "account": "sc1", "productId": "p1"}],
        }]
        saleschannels = [{"id": "sc1", "name": "C", "accountNum": 70500130001}]
        dump_dir = _make_dump(tmp_path, invoices=invoices, saleschannels=saleschannels)

        client = FakeOdoo(
            taxes={"[holded: s_iva_21]": 6},
            accounts={"70500130001": 551},
            journals={"A-": 7},
            partners={"c1": 100},
            templates={"p1": 200},  # template id=p1, variant id=200
        )
        resolvers = HoldedResolvers(client=client, tax_rules={})

        stats = load_invoices(
            client, resolvers, dump_dir, dry_run=True,
            report_dir=tmp_path / "reports",
        )

        assert stats.total == 1
        assert stats.would_create == 1
        assert stats.errors == 0
        assert stats.items_total == 1

    def test_skips(self, tmp_path):
        invoices = [
            # status cancelled
            {"id": "d_c", "contact": "c1", "docNumber": "A-1", "status": 2,
             "date": 1, "products": []},
            # no contact
            {"id": "d_nc", "contact": "", "docNumber": "A-2", "status": 1,
             "date": 1, "products": []},
            # unmapped prefix R-
            {"id": "d_r", "contact": "c1", "docNumber": "R-1", "status": 1,
             "date": 1, "products": []},
        ]
        dump_dir = _make_dump(tmp_path, invoices=invoices)
        client = FakeOdoo(partners={"c1": 100})
        resolvers = HoldedResolvers(client=client, tax_rules={})
        stats = load_invoices(client, resolvers, dump_dir, dry_run=True,
                              report_dir=tmp_path / "reports")
        assert stats.skip_cancelled == 1
        assert stats.skip_no_contact == 1
        assert stats.skip_unmapped_prefix == 1
        assert stats.would_create == 0
        assert stats.errors == 0

    def test_journal_not_found_errors(self, tmp_path):
        invoices = [{"id": "d", "contact": "c1", "docNumber": "AC-1", "status": 1,
                     "date": 1, "products": [{"units": 1, "price": 1,
                                              "taxes": ["s_iva_21"], "account": ""}]}]
        dump_dir = _make_dump(tmp_path, invoices=invoices)
        # journal AC- no en FakeOdoo
        client = FakeOdoo(taxes={"[holded: s_iva_21]": 6}, partners={"c1": 100}, journals={"A-": 7})
        resolvers = HoldedResolvers(client=client, tax_rules={})
        stats = load_invoices(client, resolvers, dump_dir, dry_run=True,
                              report_dir=tmp_path / "reports")
        assert stats.journal_unresolved == 1
        assert stats.errors == 1

    def test_partner_unknown_fallback(self, tmp_path):
        # Contact c_x no en partners; debe caer a unknown placeholder
        invoices = [{"id": "d", "contact": "c_x", "docNumber": "A-1", "status": 1,
                     "date": 1, "products": [{"units": 1, "price": 1,
                                              "taxes": ["s_iva_21"], "account": ""}]}]
        dump_dir = _make_dump(tmp_path, invoices=invoices)
        client = FakeOdoo(taxes={"[holded: s_iva_21]": 6}, partners={}, journals={"A-": 7})
        # Crear placeholder manualmente
        client.imd.append({"module": "__holded__", "name": "contact__unknown",
                          "model": "res.partner", "res_id": 999})
        resolvers = HoldedResolvers(client=client, tax_rules={})
        stats = load_invoices(client, resolvers, dump_dir, dry_run=True,
                              report_dir=tmp_path / "reports")
        # Doc no aborta porque cae al placeholder
        assert stats.would_create == 1
        assert stats.errors == 0

    def test_orphan_saleschannel(self, tmp_path):
        invoices = [{"id": "d", "contact": "c1", "docNumber": "A-1", "status": 1,
                     "date": 1, "products": [{"units": 1, "price": 1,
                                              "taxes": ["s_iva_21"],
                                              "account": "sc_orphan"}]}]
        dump_dir = _make_dump(tmp_path, invoices=invoices, saleschannels=[])
        client = FakeOdoo(taxes={"[holded: s_iva_21]": 6}, partners={"c1": 100}, journals={"A-": 7})
        resolvers = HoldedResolvers(client=client, tax_rules={})
        stats = load_invoices(client, resolvers, dump_dir, dry_run=True,
                              report_dir=tmp_path / "reports")
        assert stats.items_orphan_channel == 1
        assert stats.would_create == 1  # doc se carga aunque la line cae al default
        assert stats.errors == 0

    def test_line_without_product_id(self, tmp_path):
        invoices = [{"id": "d", "contact": "c1", "docNumber": "A-1", "status": 1,
                     "date": 1, "products": [{"units": 1, "price": 1,
                                              "taxes": ["s_iva_21"], "account": "sc1",
                                              "desc": "Ad-hoc line"}]}]
        dump_dir = _make_dump(tmp_path, invoices=invoices,
                              saleschannels=[{"id": "sc1", "accountNum": 70500130001}])
        client = FakeOdoo(taxes={"[holded: s_iva_21]": 6},
                          accounts={"70500130001": 551},
                          partners={"c1": 100}, journals={"A-": 7})
        resolvers = HoldedResolvers(client=client, tax_rules={})
        stats = load_invoices(client, resolvers, dump_dir, dry_run=True,
                              report_dir=tmp_path / "reports")
        assert stats.items_no_product == 1
        assert stats.would_create == 1
        assert stats.errors == 0

    def test_line_without_tax_loads_ok(self, tmp_path):
        # 165 items en el dump real estan sin tax: no abortan
        invoices = [{"id": "d", "contact": "c1", "docNumber": "A-1", "status": 1,
                     "date": 1, "products": [{"units": 1, "price": 1, "taxes": [], "account": "sc1"}]}]
        dump_dir = _make_dump(tmp_path, invoices=invoices,
                              saleschannels=[{"id": "sc1", "accountNum": 70500130001}])
        client = FakeOdoo(accounts={"70500130001": 551},
                          partners={"c1": 100}, journals={"A-": 7})
        resolvers = HoldedResolvers(client=client, tax_rules={})
        stats = load_invoices(client, resolvers, dump_dir, dry_run=True,
                              report_dir=tmp_path / "reports")
        assert stats.would_create == 1
        assert stats.errors == 0

    def test_default_income_fallback(self, tmp_path):
        # Item sin productId y con saleschannel huerfano debe usar default
        # income (705000 -> id=551). Sin esto Odoo aborta con
        # "Missing required account on accountable line".
        invoices = [{"id": "d", "contact": "c1", "docNumber": "A-1", "status": 1,
                     "date": 1, "products": [{"units": 1, "price": 1,
                                              "taxes": ["s_iva_21"],
                                              "account": "sc_orphan",
                                              "productId": None,
                                              "desc": "Campania huerfana"}]}]
        dump_dir = _make_dump(tmp_path, invoices=invoices, saleschannels=[])
        client = FakeOdoo(taxes={"[holded: s_iva_21]": 6},
                          accounts={"705000": 551},
                          partners={"c1": 100}, journals={"A-": 7})
        resolvers = HoldedResolvers(client=client, tax_rules={})
        # Pasamos por modo real para que el lookup de default_income haga el call
        import sys, types
        def fake_upsert(client, xmlid, model, vals, noupdate=True):
            rid = client.call(model, "create", [vals])
            return (rid, "created")
        mod = types.ModuleType("ext_id_upsert")
        mod.upsert = fake_upsert
        sys.modules["ext_id_upsert"] = mod
        stats = load_invoices(client, resolvers, dump_dir,
                              report_dir=tmp_path / "reports")
        assert stats.created == 1
        assert stats.errors == 0
        move = list(client.moves.values())[0]
        line = move["invoice_line_ids"][0][2]
        assert line.get("account_id") == 551  # fallback aplicado

    def test_multi_tax_aborts_doc(self, tmp_path):
        invoices = [{"id": "d", "contact": "c1", "docNumber": "A-1", "status": 1,
                     "date": 1, "products": [{"units": 1, "price": 1,
                                              "taxes": ["s_iva_21", "re_5"], "account": ""}]}]
        dump_dir = _make_dump(tmp_path, invoices=invoices)
        client = FakeOdoo(partners={"c1": 100}, journals={"A-": 7})
        resolvers = HoldedResolvers(client=client, tax_rules={})
        stats = load_invoices(client, resolvers, dump_dir, dry_run=True,
                              report_dir=tmp_path / "reports")
        assert stats.multi_tax_lines == 1
        assert stats.errors == 1


class TestLoadInvoicesReal:
    def test_creates_with_lines(self, tmp_path, monkeypatch):
        import sys, types

        def fake_upsert(client, xmlid, model, vals, noupdate=True):
            rid = client.call(model, "create", [vals])
            module, name = xmlid.split(".", 1)
            client.call("ir.model.data", "create",
                       [{"module": module, "name": name, "model": model,
                         "res_id": rid, "noupdate": noupdate}])
            return (rid, "created")

        mod = types.ModuleType("ext_id_upsert")
        mod.upsert = fake_upsert
        monkeypatch.setitem(sys.modules, "ext_id_upsert", mod)

        invoices = [{
            "id": "doc1", "contact": "c1", "docNumber": "A-100",
            "date": 1546210800, "status": 1, "total": 121.0, "tax": 21.0,
            "products": [{"desc": "L", "units": 1, "price": 100,
                          "taxes": ["s_iva_21"], "account": "sc1", "productId": "p1"}],
        }]
        dump_dir = _make_dump(tmp_path, invoices=invoices,
                              saleschannels=[{"id": "sc1", "accountNum": 70500130001}])
        client = FakeOdoo(
            taxes={"[holded: s_iva_21]": 6},
            accounts={"70500130001": 551},
            journals={"A-": 7},
            partners={"c1": 100},
            templates={"p1": 200},
        )
        resolvers = HoldedResolvers(client=client, tax_rules={})

        stats = load_invoices(client, resolvers, dump_dir,
                              report_dir=tmp_path / "reports")
        assert stats.created == 1
        assert stats.errors == 0
        # Inspeccion del move creado
        move = list(client.moves.values())[0]
        assert move["move_type"] == "out_invoice"
        assert move["partner_id"] == 100
        assert move["journal_id"] == 7
        assert move["ref"] == "A-100"
        assert move["state"] == "draft"  # sin --post
        lines = move["invoice_line_ids"]
        assert len(lines) == 1
        assert lines[0][0] == 0
        line_vals = lines[0][2]
        assert line_vals["quantity"] == 1.0
        assert line_vals["price_unit"] == 100.0
        assert line_vals["product_id"] == 200
        assert line_vals["account_id"] == 551
        assert line_vals["tax_ids"] == [(6, 0, [6])]

    def test_post_flag_posts_status_1(self, tmp_path, monkeypatch):
        import sys, types

        def fake_upsert(client, xmlid, model, vals, noupdate=True):
            rid = client.call(model, "create", [vals])
            module, name = xmlid.split(".", 1)
            client.call("ir.model.data", "create",
                       [{"module": module, "name": name, "model": model,
                         "res_id": rid, "noupdate": noupdate}])
            return (rid, "created")
        mod = types.ModuleType("ext_id_upsert")
        mod.upsert = fake_upsert
        monkeypatch.setitem(sys.modules, "ext_id_upsert", mod)

        invoices = [{
            "id": "d1", "contact": "c1", "docNumber": "A-1",
            "date": 1546210800, "status": 1, "total": 121, "tax": 21,
            "products": [{"desc": "L", "units": 1, "price": 100,
                          "taxes": ["s_iva_21"], "account": ""}],
        }]
        dump_dir = _make_dump(tmp_path, invoices=invoices)
        client = FakeOdoo(taxes={"[holded: s_iva_21]": 6}, partners={"c1": 100}, journals={"A-": 7})
        resolvers = HoldedResolvers(client=client, tax_rules={})
        stats = load_invoices(client, resolvers, dump_dir, post=True,
                              report_dir=tmp_path / "reports")
        assert stats.created == 1
        assert stats.posted == 1
        move = list(client.moves.values())[0]
        assert move["state"] == "posted"

    def test_idempotent_existing_draft_rewrites(self, tmp_path, monkeypatch):
        import sys, types

        def fake_upsert(client, xmlid, model, vals, noupdate=True):
            rid = client.call(model, "create", [vals])
            module, name = xmlid.split(".", 1)
            client.call("ir.model.data", "create",
                       [{"module": module, "name": name, "model": model,
                         "res_id": rid, "noupdate": noupdate}])
            return (rid, "created")
        mod = types.ModuleType("ext_id_upsert")
        mod.upsert = fake_upsert
        monkeypatch.setitem(sys.modules, "ext_id_upsert", mod)

        invoices = [{
            "id": "d1", "contact": "c1", "docNumber": "A-1",
            "date": 1546210800, "status": 0,  # draft Holded -> NO post
            "total": 121, "tax": 21,
            "products": [{"desc": "L", "units": 1, "price": 100,
                          "taxes": ["s_iva_21"], "account": ""}],
        }]
        dump_dir = _make_dump(tmp_path, invoices=invoices)
        client = FakeOdoo(taxes={"[holded: s_iva_21]": 6}, partners={"c1": 100}, journals={"A-": 7})
        resolvers = HoldedResolvers(client=client, tax_rules={})

        # 1er run: create
        stats1 = load_invoices(client, resolvers, dump_dir, report_dir=tmp_path / "reports")
        assert stats1.created == 1
        # 2do run: existing draft -> updated
        stats2 = load_invoices(client, resolvers, dump_dir, report_dir=tmp_path / "reports")
        assert stats2.updated == 1
        assert stats2.created == 0

    def test_idempotent_existing_posted_skips(self, tmp_path, monkeypatch):
        import sys, types

        def fake_upsert(client, xmlid, model, vals, noupdate=True):
            rid = client.call(model, "create", [vals])
            module, name = xmlid.split(".", 1)
            client.call("ir.model.data", "create",
                       [{"module": module, "name": name, "model": model,
                         "res_id": rid, "noupdate": noupdate}])
            return (rid, "created")
        mod = types.ModuleType("ext_id_upsert")
        mod.upsert = fake_upsert
        monkeypatch.setitem(sys.modules, "ext_id_upsert", mod)

        invoices = [{
            "id": "d1", "contact": "c1", "docNumber": "A-1",
            "date": 1546210800, "status": 1, "total": 121, "tax": 21,
            "products": [{"desc": "L", "units": 1, "price": 100,
                          "taxes": ["s_iva_21"], "account": ""}],
        }]
        dump_dir = _make_dump(tmp_path, invoices=invoices)
        client = FakeOdoo(taxes={"[holded: s_iva_21]": 6}, partners={"c1": 100}, journals={"A-": 7})
        resolvers = HoldedResolvers(client=client, tax_rules={})

        # 1er run con post: create + post
        stats1 = load_invoices(client, resolvers, dump_dir, post=True,
                               report_dir=tmp_path / "reports")
        assert stats1.posted == 1
        # 2do run: ya posted -> skip
        stats2 = load_invoices(client, resolvers, dump_dir, post=True,
                               report_dir=tmp_path / "reports")
        assert stats2.skip_existing_posted == 1
        assert stats2.created == 0
        assert stats2.posted == 0


# ---------------------------------------------------------------------------
# SALES_PREFIXES coverage
# ---------------------------------------------------------------------------


class TestSalesPrefixes:
    def test_contains_expected(self):
        assert SALES_PREFIXES == {"A-", "AC-", "AF-", "KD-", "FVU-", "L-"}

    def test_r_not_included(self):
        assert "R-" not in SALES_PREFIXES
        assert "PB-" not in SALES_PREFIXES  # purchase
