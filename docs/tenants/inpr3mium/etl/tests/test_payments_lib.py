"""Tests offline para `_payments_lib.py` (loader 7 payments)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from _payments_lib import (
    BANK_TO_JOURNAL,
    SUPPORTED_DOC_TYPES_FULL,
    SUPPORTED_DOC_TYPES_MVP,
    _xmlid_for_target,
    build_payment_vals,
    derive_partner_type,
    derive_payment_type,
    load_payments,
)


class FakeOdoo:
    def __init__(self, *, partners=None, moves=None):
        self.partners = partners or {}        # {holded_contact_id: partner_id}
        self.moves = moves or {}              # {xmlid: move_id}
        self.payments: dict[int, dict] = {}
        self.imd: list[dict] = []
        self.next_id = 7000
        for hid, pid in self.partners.items():
            self.imd.append({"module": "__holded__", "name": f"contact_{hid}",
                            "model": "res.partner", "res_id": pid})
        for xmlid, mid in self.moves.items():
            _, nm = xmlid.split(".", 1)
            self.imd.append({"module": "__holded__", "name": nm,
                            "model": "account.move", "res_id": mid})

    def _next(self):
        n = self.next_id; self.next_id += 1; return n

    def call(self, model, method, args=None, kwargs=None):
        args = args or []; kwargs = kwargs or {}
        if model == "ir.model.data" and method == "search_read":
            domain = args[0]
            mod = next((t[2] for t in domain if t[0] == "module"), None)
            model_f = next((t[2] for t in domain if t[0] == "model"), None)
            name_in = next((t[2] for t in domain if t[0] == "name" and t[1] == "in"), None)
            name_eq = next((t[2] for t in domain if t[0] == "name" and t[1] == "="), None)
            fields_req = kwargs.get("fields", ["res_id"])
            out = []
            for e in self.imd:
                if mod and e["module"] != mod: continue
                if model_f and e["model"] != model_f: continue
                if name_in and e["name"] not in name_in: continue
                if name_eq and e["name"] != name_eq: continue
                out.append({f: e.get(f) for f in fields_req})
            if kwargs.get("limit"): out = out[:kwargs["limit"]]
            return out
        if model == "account.payment" and method == "create":
            vals = args[0]
            pid = self._next()
            self.payments[pid] = dict(vals)
            return pid
        if model == "ir.model.data" and method == "create":
            vals = args[0]
            e = {"id": self._next(), **vals}
            self.imd.append(e)
            return e["id"]
        raise NotImplementedError(f"{model}.{method}")


def _make_dump(tmp_path, payments):
    dd = tmp_path / "dump"
    dd.mkdir()
    with (dd / "payments.jsonl").open("w") as f:
        for r in payments:
            f.write(json.dumps(r) + "\n")
    return dd


class TestDerivePaymentType:
    def test_positive_inbound(self):
        assert derive_payment_type("invoice", 100.0) == "inbound"

    def test_negative_outbound(self):
        assert derive_payment_type("invoice", -100.0) == "outbound"

    def test_creditnote_positive(self):
        assert derive_payment_type("creditnote", 50.0) == "inbound"

    def test_purchase_negative(self):
        assert derive_payment_type("purchase", -200.0) == "outbound"


class TestDerivePartnerType:
    def test_invoice(self):
        assert derive_partner_type("invoice") == "customer"

    def test_creditnote(self):
        assert derive_partner_type("creditnote") == "customer"

    def test_purchase(self):
        assert derive_partner_type("purchase") == "supplier"

    def test_purchaserefund(self):
        assert derive_partner_type("purchaserefund") == "supplier"


class TestXmlidForTarget:
    @pytest.mark.parametrize("dt,did,expected", [
        ("invoice", "abc", "__holded__.invoice_abc"),
        ("creditnote", "xyz", "__holded__.creditnote_xyz"),
        ("purchase", "p1", "__holded__.purchase_p1"),
        ("purchaserefund", "pr1", "__holded__.purchaserefund_pr1"),
        ("trans", "t1", None),
        ("payroll", "py1", None),
    ])
    def test_mapping(self, dt, did, expected):
        assert _xmlid_for_target(dt, did) == expected


class TestBuildPaymentVals:
    def test_basic_inbound(self):
        doc = {"id": "p1", "amount": 121.0, "date": 1656540000,
               "documentType": "invoice", "documentId": "inv1",
               "desc": "Pago F. A-001"}
        v = build_payment_vals(doc, partner_id=10, journal_id=19, target_move_id=100)
        assert v["amount"] == 121.0
        assert v["payment_type"] == "inbound"
        assert v["partner_type"] == "customer"
        assert v["partner_id"] == 10
        assert v["journal_id"] == 19
        assert "ref" not in v  # Odoo 19: account.payment NO tiene ref
        assert "Pago F. A-001" in v["memo"]
        assert "[holded:p1]" in v["memo"]  # holded_id en memo
        assert "inv1" in v["memo"]

    def test_outbound_negative_amount(self):
        doc = {"id": "p1", "amount": -50.0, "documentType": "invoice", "date": 1}
        v = build_payment_vals(doc, partner_id=1, journal_id=1)
        assert v["amount"] == 50.0  # abs
        assert v["payment_type"] == "outbound"

    def test_memo_contains_holded_id_when_no_desc(self):
        # Aunque no haya desc ni target_move, el holded_id va siempre al memo
        doc = {"id": "p1", "amount": 10, "documentType": "invoice", "date": 1}
        v = build_payment_vals(doc, partner_id=1, journal_id=1)
        assert "[holded:p1]" in v["memo"]


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------


class TestLoadPaymentsDryRun:
    def test_basic(self, tmp_path):
        payments = [{
            "id": "pay1", "documentType": "invoice", "documentId": "inv1",
            "contactId": "c1", "amount": 121.0,
            "bankId": list(BANK_TO_JOURNAL)[0],
            "date": 1656540000, "desc": "Pago A-100",
        }]
        dd = _make_dump(tmp_path, payments)
        bank0_jid = list(BANK_TO_JOURNAL.values())[0]
        c = FakeOdoo(partners={"c1": 10},
                     moves={"__holded__.invoice_inv1": 200})
        stats = load_payments(c, dd, dry_run=True, report_dir=tmp_path / "r")
        assert stats.total == 1
        assert stats.would_create == 1
        assert stats.errors == 0

    def test_skip_unsupported_doctype(self, tmp_path):
        payments = [{
            "id": "p1", "documentType": "trans", "documentId": "x",
            "contactId": "c1", "amount": 100, "bankId": list(BANK_TO_JOURNAL)[0],
            "date": 1,
        }]
        dd = _make_dump(tmp_path, payments)
        c = FakeOdoo()
        stats = load_payments(c, dd, dry_run=True, report_dir=tmp_path / "r")
        assert stats.skip_doc_type_unsupported == 1
        assert stats.would_create == 0

    def test_skip_no_contact(self, tmp_path):
        payments = [{"id": "p1", "documentType": "invoice", "documentId": "i",
                     "contactId": "", "amount": 10, "bankId": list(BANK_TO_JOURNAL)[0],
                     "date": 1}]
        dd = _make_dump(tmp_path, payments)
        c = FakeOdoo()
        stats = load_payments(c, dd, dry_run=True, report_dir=tmp_path / "r")
        assert stats.skip_no_contact == 1

    def test_skip_bank_unmapped(self, tmp_path):
        payments = [{"id": "p1", "documentType": "invoice", "documentId": "i",
                     "contactId": "c1", "amount": 10, "bankId": "BANK_RARO",
                     "date": 1}]
        dd = _make_dump(tmp_path, payments)
        c = FakeOdoo(partners={"c1": 10})
        stats = load_payments(c, dd, dry_run=True, report_dir=tmp_path / "r")
        assert stats.skip_bank_unmapped == 1

    def test_skip_move_unresolved(self, tmp_path):
        payments = [{"id": "p1", "documentType": "invoice", "documentId": "inv_no_carga",
                     "contactId": "c1", "amount": 10, "bankId": list(BANK_TO_JOURNAL)[0],
                     "date": 1}]
        dd = _make_dump(tmp_path, payments)
        # Move no esta en imd
        c = FakeOdoo(partners={"c1": 10})
        stats = load_payments(c, dd, dry_run=True, report_dir=tmp_path / "r")
        assert stats.skip_move_unresolved == 1

    def test_skip_purchase_in_mvp(self, tmp_path):
        # documentType=purchase NO se procesa en MVP (include_purchases=False)
        payments = [{"id": "p1", "documentType": "purchase", "documentId": "pu1",
                     "contactId": "c1", "amount": 10, "bankId": list(BANK_TO_JOURNAL)[0],
                     "date": 1}]
        dd = _make_dump(tmp_path, payments)
        c = FakeOdoo(partners={"c1": 10}, moves={"__holded__.purchase_pu1": 300})
        stats = load_payments(c, dd, dry_run=True, report_dir=tmp_path / "r",
                              include_purchases=False)
        assert stats.skip_doc_type_unsupported == 1

    def test_include_purchases(self, tmp_path):
        payments = [{"id": "p1", "documentType": "purchase", "documentId": "pu1",
                     "contactId": "c1", "amount": -100, "bankId": list(BANK_TO_JOURNAL)[0],
                     "date": 1}]
        dd = _make_dump(tmp_path, payments)
        c = FakeOdoo(partners={"c1": 10}, moves={"__holded__.purchase_pu1": 300})
        stats = load_payments(c, dd, dry_run=True, report_dir=tmp_path / "r",
                              include_purchases=True)
        assert stats.would_create == 1


class TestLoadPaymentsReal:
    def test_creates_payment(self, tmp_path, monkeypatch):
        import sys, types
        def fake_upsert(client, xmlid, model, vals, noupdate=True):
            rid = client.call(model, "create", [vals])
            module, name = xmlid.split(".", 1)
            client.call("ir.model.data", "create",
                       [{"module": module, "name": name, "model": model,
                         "res_id": rid, "noupdate": noupdate}])
            return (rid, "created")
        mod = types.ModuleType("ext_id_upsert"); mod.upsert = fake_upsert
        monkeypatch.setitem(sys.modules, "ext_id_upsert", mod)

        payments = [{
            "id": "pay1", "documentType": "invoice", "documentId": "inv1",
            "contactId": "c1", "amount": 121.0,
            "bankId": list(BANK_TO_JOURNAL)[0],
            "date": 1656540000, "desc": "Pago A-100",
        }]
        dd = _make_dump(tmp_path, payments)
        c = FakeOdoo(partners={"c1": 10}, moves={"__holded__.invoice_inv1": 200})
        stats = load_payments(c, dd, report_dir=tmp_path / "r")
        assert stats.created == 1
        assert stats.errors == 0
        pay = list(c.payments.values())[0]
        assert pay["partner_id"] == 10
        assert pay["amount"] == 121.0
        assert pay["payment_type"] == "inbound"
        assert pay["partner_type"] == "customer"
        assert pay["journal_id"] == list(BANK_TO_JOURNAL.values())[0]


class TestBankToJournalConstants:
    def test_four_productive_banks(self):
        # Snapshot Fase 5.0: 4 bank journals productivos
        assert len(BANK_TO_JOURNAL) == 4
        assert set(BANK_TO_JOURNAL.values()) == {19, 20, 21, 22}

    def test_mvp_subset_of_full(self):
        assert SUPPORTED_DOC_TYPES_MVP.issubset(SUPPORTED_DOC_TYPES_FULL)
        assert "purchase" in SUPPORTED_DOC_TYPES_FULL
        assert "purchase" not in SUPPORTED_DOC_TYPES_MVP
