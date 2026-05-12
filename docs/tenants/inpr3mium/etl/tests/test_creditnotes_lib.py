"""Tests offline para `_creditnotes_lib.py` (loader 5 out_refund)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from _creditnotes_lib import (
    REFUND_PREFIXES,
    STATUS_REVIEW,
    build_refund_header_vals,
    load_creditnotes,
    should_skip_refund,
)
from holded_resolvers import HoldedResolvers


# Reuso FakeOdoo del test_invoices_lib via copy (no podemos importar de
# tests entre si limpio sin shenanigans).
class FakeOdoo:
    def __init__(self, *, taxes=None, accounts=None, journals=None,
                 partners=None, templates=None, invoice_moves=None):
        self.taxes = taxes or {}
        self.accounts = accounts or {}
        self.journals = journals or {}
        self.partners = partners or {}
        self.templates = templates or {}
        self.invoice_moves = invoice_moves or {}  # {holded_invoice_id: move_id}
        self.moves: dict[int, dict] = {}
        self.imd: list[dict] = []
        self.next_id = 5000
        self.calls = []
        for hid, pid in self.partners.items():
            self.imd.append({"module": "__holded__", "name": f"contact_{hid}",
                            "model": "res.partner", "res_id": pid})
        for hid, vid in self.templates.items():
            self.imd.append({"module": "__holded__", "name": f"product_{hid}",
                            "model": "product.template", "res_id": hid})
        for hid, mid in self.invoice_moves.items():
            self.imd.append({"module": "__holded__", "name": f"invoice_{hid}",
                            "model": "account.move", "res_id": mid})

    def _next(self):
        n = self.next_id; self.next_id += 1; return n

    def call(self, model, method, args=None, kwargs=None):
        self.calls.append((model, method, args, kwargs))
        args = args or []; kwargs = kwargs or {}
        if model == "account.tax" and method == "search_read":
            for t in args[0]:
                if t[0] == "description" and t[1] == "ilike":
                    if t[2] in self.taxes:
                        return [{"id": self.taxes[t[2]]}]
                    return []
            return []
        if model == "account.account" and method == "search_read":
            for t in args[0]:
                if t[0] == "code" and t[1] == "=":
                    if t[2] in self.accounts:
                        return [{"id": self.accounts[t[2]], "account_type": "income"}]
                    return []
            return []
        if model == "account.journal" and method == "search_read":
            for t in args[0]:
                if t[0] == "code" and t[1] == "in":
                    return [{"code": c, "id": self.journals[c]}
                            for c in t[2] if c in self.journals]
            return []
        if model == "ir.model.data" and method == "search_read":
            domain = args[0]
            mod = next((t[2] for t in domain if t[0] == "module"), None)
            model_f = next((t[2] for t in domain if t[0] == "model"), None)
            name_eq = next((t[2] for t in domain if t[0] == "name" and t[1] == "="), None)
            name_in = next((t[2] for t in domain if t[0] == "name" and t[1] == "in"), None)
            fields_req = kwargs.get("fields", ["res_id"])
            out = []
            for e in self.imd:
                if mod and e["module"] != mod: continue
                if model_f and e["model"] != model_f: continue
                if name_eq and e["name"] != name_eq: continue
                if name_in and e["name"] not in name_in: continue
                out.append({f: e.get(f) for f in fields_req})
            if kwargs.get("limit"): out = out[:kwargs["limit"]]
            return out
        if model == "ir.model.data" and method == "create":
            vals = args[0]
            e = {"id": self._next(), **vals}
            self.imd.append(e)
            return e["id"]
        if model == "product.template" and method == "read":
            ids = args[0]
            return [{"id": i, "product_variant_id": [self.templates[i], f"v{i}"]}
                    for i in ids if i in self.templates]
        if model == "account.move" and method == "read":
            ids = args[0]
            fields = args[1] if len(args) > 1 else None
            out = []
            for i in ids:
                if i in self.moves:
                    rec = dict(self.moves[i]); rec["id"] = i
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
            for i in args[0]:
                self.moves[i].update(args[1])
            return True
        if model == "account.move" and method == "action_post":
            for i in args[0]:
                self.moves[i]["state"] = "posted"
            return True
        raise NotImplementedError(f"{model}.{method}")


def _make_dump(tmp_path, creditnotes=None, saleschannels=None):
    dump_dir = tmp_path / "dump"
    (dump_dir / "documents").mkdir(parents=True)
    with (dump_dir / "documents" / "creditnote.jsonl").open("w") as f:
        for r in creditnotes or []:
            f.write(json.dumps(r) + "\n")
    with (dump_dir / "saleschannels.jsonl").open("w") as f:
        for r in saleschannels or []:
            f.write(json.dumps(r) + "\n")
    return dump_dir


# ---------------------------------------------------------------------------
# should_skip_refund
# ---------------------------------------------------------------------------


class TestShouldSkipRefund:
    def test_ok_AC(self):
        d = {"contact": "c", "docNumber": "AC-001", "status": 1}
        assert should_skip_refund(d) == (False, "")

    def test_skip_cancelled(self):
        d = {"contact": "c", "docNumber": "AC-001", "status": 2}
        assert should_skip_refund(d) == (True, "cancelled")

    def test_skip_no_contact(self):
        d = {"contact": "", "docNumber": "AC-001", "status": 1}
        assert should_skip_refund(d) == (True, "no_contact")

    def test_skip_unmapped_prefix(self):
        # A- (out_invoice) NO debe entrar a creditnotes
        d = {"contact": "c", "docNumber": "A-001", "status": 1}
        assert should_skip_refund(d) == (True, "unmapped_prefix")

    def test_review_not_skipped(self):
        # status=3 NO se salta (se carga draft, no se postea)
        d = {"contact": "c", "docNumber": "AC-001", "status": STATUS_REVIEW}
        assert should_skip_refund(d) == (False, "")


# ---------------------------------------------------------------------------
# build_refund_header_vals
# ---------------------------------------------------------------------------


class TestBuildRefundHeader:
    def test_basic(self):
        d = {"id": "x", "contact": "c", "docNumber": "AC-001133",
             "date": 1656540000, "status": 1}
        v = build_refund_header_vals(d, partner_id=10, journal_id=13)
        assert v["move_type"] == "out_refund"
        assert v["name"] == "AC-001133"
        assert v["ref"] == "AC-001133"
        assert v["partner_id"] == 10
        assert v["journal_id"] == 13

    def test_reversed_entry(self):
        d = {"id": "x", "contact": "c", "docNumber": "AC-001", "date": 1, "status": 1}
        v = build_refund_header_vals(d, partner_id=1, journal_id=1, reversed_entry_id=42)
        assert v["reversed_entry_id"] == 42

    def test_status_review_adds_narration(self):
        d = {"id": "x", "contact": "c", "docNumber": "AC-1", "date": 1, "status": STATUS_REVIEW}
        v = build_refund_header_vals(d, partner_id=1, journal_id=1)
        assert "STATUS HOLDED=3" in v["narration"]

    def test_duplicate_drops_name_and_warns(self):
        d = {"id": "loser", "contact": "c", "docNumber": "AC-DUP", "date": 1, "status": 1}
        v = build_refund_header_vals(d, partner_id=1, journal_id=1, duplicate_alt_id="winner")
        assert "name" not in v
        assert "winner" in v["narration"]


# ---------------------------------------------------------------------------
# Integration: load_creditnotes
# ---------------------------------------------------------------------------


class TestLoadCreditnotesDryRun:
    def test_basic(self, tmp_path):
        cns = [{
            "id": "cn1", "contact": "c1", "docNumber": "AC-100",
            "date": 1656540000, "status": 1, "total": 576.36, "tax": 100.03,
            "from": {"docType": "invoice", "id": "inv1"},
            "products": [{"desc": "L", "units": 1, "price": 476.33,
                          "taxes": ["s_iva_21"], "account": "sc1", "productId": "p1"}],
        }]
        dump_dir = _make_dump(tmp_path, creditnotes=cns,
                              saleschannels=[{"id": "sc1", "accountNum": 70500130001}])
        client = FakeOdoo(
            taxes={"[holded: s_iva_21]": 6},
            accounts={"70500130001": 551},
            journals={"AC-": 13}, partners={"c1": 100},
            templates={"p1": 200}, invoice_moves={"inv1": 999},
        )
        resolvers = HoldedResolvers(client=client, tax_rules={})
        stats = load_creditnotes(client, resolvers, dump_dir, dry_run=True,
                                  report_dir=tmp_path / "reports")
        assert stats.total == 1
        assert stats.would_create == 1
        assert stats.reversed_entry_linked == 1
        assert stats.errors == 0

    def test_standalone_no_from(self, tmp_path):
        cns = [{"id": "cn1", "contact": "c1", "docNumber": "AC-1",
                "date": 1, "status": 1,
                "products": [{"units": 1, "price": 1, "taxes": ["s_iva_21"], "account": ""}]}]
        dump_dir = _make_dump(tmp_path, creditnotes=cns)
        client = FakeOdoo(taxes={"[holded: s_iva_21]": 6},
                          journals={"AC-": 13}, partners={"c1": 100})
        resolvers = HoldedResolvers(client=client, tax_rules={})
        stats = load_creditnotes(client, resolvers, dump_dir, dry_run=True,
                                  report_dir=tmp_path / "reports")
        assert stats.standalone_refunds == 1
        assert stats.reversed_entry_linked == 0
        assert stats.errors == 0

    def test_orphan_from_invoice(self, tmp_path):
        # from.id no resoluble -> orphan, no aborta
        cns = [{"id": "cn1", "contact": "c1", "docNumber": "AC-1",
                "date": 1, "status": 1,
                "from": {"docType": "invoice", "id": "inv_inexistente"},
                "products": [{"units": 1, "price": 1, "taxes": ["s_iva_21"], "account": ""}]}]
        dump_dir = _make_dump(tmp_path, creditnotes=cns)
        client = FakeOdoo(taxes={"[holded: s_iva_21]": 6},
                          journals={"AC-": 13}, partners={"c1": 100})
        resolvers = HoldedResolvers(client=client, tax_rules={})
        stats = load_creditnotes(client, resolvers, dump_dir, dry_run=True,
                                  report_dir=tmp_path / "reports")
        assert stats.reversed_entry_orphan == 1
        assert stats.errors == 0


class TestLoadCreditnotesReal:
    def test_creates_with_reversed_entry(self, tmp_path, monkeypatch):
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

        cns = [{"id": "cn1", "contact": "c1", "docNumber": "AC-100",
                "date": 1, "status": 1, "total": 121, "tax": 21,
                "from": {"docType": "invoice", "id": "inv1"},
                "products": [{"units": 1, "price": 100, "taxes": ["s_iva_21"], "account": ""}]}]
        dump_dir = _make_dump(tmp_path, creditnotes=cns)
        client = FakeOdoo(taxes={"[holded: s_iva_21]": 6},
                          journals={"AC-": 13}, partners={"c1": 100},
                          invoice_moves={"inv1": 999})
        resolvers = HoldedResolvers(client=client, tax_rules={})
        stats = load_creditnotes(client, resolvers, dump_dir,
                                  report_dir=tmp_path / "reports")
        assert stats.created == 1
        move = list(client.moves.values())[0]
        assert move["move_type"] == "out_refund"
        assert move["name"] == "AC-100"
        assert move["reversed_entry_id"] == 999
        assert move["state"] == "draft"

    def test_post_only_status_1(self, tmp_path, monkeypatch):
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

        cns = [
            {"id": "cn_1", "contact": "c1", "docNumber": "AC-1", "date": 1, "status": 1,
             "products": [{"units": 1, "price": 1, "taxes": ["s_iva_21"], "account": ""}]},
            {"id": "cn_3", "contact": "c1", "docNumber": "AC-2", "date": 1, "status": STATUS_REVIEW,
             "products": [{"units": 1, "price": 1, "taxes": ["s_iva_21"], "account": ""}]},
        ]
        dump_dir = _make_dump(tmp_path, creditnotes=cns)
        client = FakeOdoo(taxes={"[holded: s_iva_21]": 6},
                          journals={"AC-": 13}, partners={"c1": 100})
        resolvers = HoldedResolvers(client=client, tax_rules={})
        stats = load_creditnotes(client, resolvers, dump_dir, post=True,
                                  report_dir=tmp_path / "reports")
        assert stats.created == 2
        assert stats.posted == 1  # solo status=1 posteado
        # Find the cn_3 move (status=3) — should be draft
        # AC-1 status=1 -> posted; AC-2 status=3 -> draft
        states = [m.get("state") for m in client.moves.values()]
        assert sorted(states) == ["draft", "posted"]


class TestRefundPrefixes:
    def test_only_AC(self):
        assert REFUND_PREFIXES == {"AC-"}
