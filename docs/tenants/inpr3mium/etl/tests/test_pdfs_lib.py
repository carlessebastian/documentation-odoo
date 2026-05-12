"""Tests offline para `_pdfs_lib.py` (loader 9 PDFs)."""
from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from _pdfs_lib import (
    DOCTYPE_TO_EXTID_PREFIX,
    EXT_MODULE,
    MAX_PDF_SIZE_BYTES,
    attachment_exists,
    build_attachment_vals,
    find_move_by_holded_id,
    load_pdfs_for_doctype,
)


# ---------------------------------------------------------------------------
# Fake
# ---------------------------------------------------------------------------


class FakeOdoo:
    def __init__(self):
        self.imd: list[dict] = []          # ir.model.data
        self.moves: dict[int, dict] = {}    # account.move
        self.attachments: list[dict] = []  # ir.attachment
        self.next_id = 10000

    def _next(self):
        n = self.next_id
        self.next_id += 1
        return n

    def add_move(self, holded_id: str, doctype: str, *, ref: str, name=False) -> int:
        rid = self._next()
        self.moves[rid] = {"id": rid, "ref": ref, "name": name or "/"}
        self.imd.append({"module": EXT_MODULE, "name": f"{doctype}_{holded_id}",
                        "model": "account.move", "res_id": rid})
        return rid

    def call(self, model, method, args=None, kwargs=None):
        args = args or []
        kwargs = kwargs or {}
        if model == "ir.model.data" and method == "search_read":
            domain = args[0]
            mod = next((t[2] for t in domain if t[0] == "module"), None)
            name_eq = next((t[2] for t in domain if t[0] == "name" and t[1] == "="), None)
            for e in self.imd:
                if mod and e["module"] != mod:
                    continue
                if name_eq and e["name"] != name_eq:
                    continue
                fields = kwargs.get("fields", [])
                return [{f: e.get(f) for f in fields}]
            return []
        if model == "account.move" and method == "read":
            ids = args[0]
            fields = args[1] if len(args) > 1 else None
            return [{f: self.moves.get(i, {}).get(f, False) for f in fields} | {"id": i}
                    for i in ids if i in self.moves]
        if model == "ir.attachment" and method == "search_count":
            domain = args[0]
            d = dict((t[0], t[2]) for t in domain)
            cnt = 0
            for a in self.attachments:
                if (a.get("res_model") == d.get("res_model")
                        and a.get("res_id") == d.get("res_id")
                        and a.get("name") == d.get("name")):
                    cnt += 1
            return cnt
        if model == "ir.attachment" and method == "create":
            vals = args[0]
            aid = self._next()
            self.attachments.append({"id": aid, **vals})
            return aid
        raise NotImplementedError(f"{model}.{method}")


# ---------------------------------------------------------------------------
# build_attachment_vals
# ---------------------------------------------------------------------------


class TestBuildAttachmentVals:
    def test_basic(self):
        v = build_attachment_vals(b"PDF-DATA", move_id=42, attachment_name="X.pdf")
        assert v["res_model"] == "account.move"
        assert v["res_id"] == 42
        assert v["name"] == "X.pdf"
        assert v["mimetype"] == "application/pdf"
        assert v["type"] == "binary"
        assert v["datas"] == base64.b64encode(b"PDF-DATA").decode("ascii")


# ---------------------------------------------------------------------------
# find_move_by_holded_id
# ---------------------------------------------------------------------------


class TestFindMove:
    def test_returns_move(self):
        c = FakeOdoo()
        rid = c.add_move("hid1", "invoice", ref="A-001", name="A-001")
        res = find_move_by_holded_id(c, "hid1", "invoice")
        assert res == (rid, "A-001")

    def test_no_ext_id(self):
        c = FakeOdoo()
        assert find_move_by_holded_id(c, "hid_inexistente", "invoice") is None

    def test_name_slash_fallback_to_ref(self):
        # Si move.name='/' (draft sin name explicito), usa ref
        c = FakeOdoo()
        rid = c.add_move("hid1", "invoice", ref="A-001", name="/")
        res = find_move_by_holded_id(c, "hid1", "invoice")
        assert res == (rid, "A-001")


# ---------------------------------------------------------------------------
# attachment_exists (idempotencia)
# ---------------------------------------------------------------------------


class TestAttachmentExists:
    def test_false_when_none(self):
        assert attachment_exists(FakeOdoo(), 1, "X.pdf") is False

    def test_true_when_exists(self):
        c = FakeOdoo()
        c.attachments.append({"res_model": "account.move", "res_id": 1, "name": "X.pdf"})
        assert attachment_exists(c, 1, "X.pdf") is True

    def test_false_diff_move(self):
        c = FakeOdoo()
        c.attachments.append({"res_model": "account.move", "res_id": 99, "name": "X.pdf"})
        assert attachment_exists(c, 1, "X.pdf") is False


# ---------------------------------------------------------------------------
# Integration: load_pdfs_for_doctype
# ---------------------------------------------------------------------------


def _make_pdf_dump(tmp_path: Path, doctype: str, files: dict[str, bytes]) -> Path:
    """tmp_path/dump/pdfs/<doctype>/<holded_id>.pdf con content."""
    dump_dir = tmp_path / "dump"
    pdf_dir = dump_dir / "pdfs" / doctype
    pdf_dir.mkdir(parents=True)
    for hid, content in files.items():
        (pdf_dir / f"{hid}.pdf").write_bytes(content)
    return dump_dir


class TestLoadPdfsForDoctype:
    def test_creates_attachment(self, tmp_path):
        dump_dir = _make_pdf_dump(tmp_path, "invoice", {
            "hid1": b"PDF1", "hid2": b"PDF2",
        })
        c = FakeOdoo()
        c.add_move("hid1", "invoice", ref="A-001")
        c.add_move("hid2", "invoice", ref="A-002")

        stats = load_pdfs_for_doctype(c, dump_dir, doctype="invoice",
                                       report_dir=tmp_path / "reports")
        assert stats.created == 2
        assert stats.errors == 0
        # Verifica vals
        names = sorted(a["name"] for a in c.attachments)
        assert names == ["A-001.pdf", "A-002.pdf"]

    def test_dry_run_no_writes(self, tmp_path):
        dump_dir = _make_pdf_dump(tmp_path, "invoice", {"hid1": b"PDF1"})
        c = FakeOdoo()
        c.add_move("hid1", "invoice", ref="A-001")
        stats = load_pdfs_for_doctype(c, dump_dir, doctype="invoice",
                                       dry_run=True,
                                       report_dir=tmp_path / "reports")
        assert stats.created == 0
        assert len(c.attachments) == 0

    def test_idempotent_skip_existing(self, tmp_path):
        dump_dir = _make_pdf_dump(tmp_path, "invoice", {"hid1": b"PDF1"})
        c = FakeOdoo()
        c.add_move("hid1", "invoice", ref="A-001")
        # Pre-populate attachment
        c.attachments.append({"res_model": "account.move", "res_id": 10000,
                              "name": "A-001.pdf"})
        stats = load_pdfs_for_doctype(c, dump_dir, doctype="invoice",
                                       report_dir=tmp_path / "reports")
        assert stats.skipped_existing == 1
        assert stats.created == 0

    def test_skip_no_move(self, tmp_path):
        # PDF presente pero NO existe ext_id para el holded_id
        dump_dir = _make_pdf_dump(tmp_path, "invoice", {"hid_no_loaded": b"PDF"})
        c = FakeOdoo()
        stats = load_pdfs_for_doctype(c, dump_dir, doctype="invoice",
                                       report_dir=tmp_path / "reports")
        assert stats.skipped_no_move == 1
        assert stats.created == 0

    def test_skip_too_large(self, tmp_path):
        big = b"X" * (MAX_PDF_SIZE_BYTES + 1)
        dump_dir = _make_pdf_dump(tmp_path, "invoice", {"hid_big": big})
        c = FakeOdoo()
        c.add_move("hid_big", "invoice", ref="A-001")
        stats = load_pdfs_for_doctype(c, dump_dir, doctype="invoice",
                                       report_dir=tmp_path / "reports")
        assert stats.skipped_too_large == 1
        assert stats.created == 0

    def test_limit(self, tmp_path):
        files = {f"hid{i}": b"PDF" for i in range(5)}
        dump_dir = _make_pdf_dump(tmp_path, "invoice", files)
        c = FakeOdoo()
        for hid in files:
            c.add_move(hid, "invoice", ref=f"A-{hid}")
        stats = load_pdfs_for_doctype(c, dump_dir, doctype="invoice", limit=2,
                                       report_dir=tmp_path / "reports")
        assert stats.total_pdfs == 2
        assert stats.created == 2


class TestDoctypePrefix:
    def test_all_four_supported(self):
        assert set(DOCTYPE_TO_EXTID_PREFIX) == {
            "invoice", "purchase", "creditnote", "purchaserefund",
        }
