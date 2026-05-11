"""Tests para utilidades de holded_export.py (manifest, write_atomic, jsonl)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import holded_export


def test_load_manifest_missing(tmp_path):
    m = holded_export._load_manifest(tmp_path / "no.json")
    assert m == {"version": 1, "resources": {}, "pdfs": {}}


def test_load_manifest_invalid_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json {{{")
    m = holded_export._load_manifest(p)
    assert m == {"version": 1, "resources": {}, "pdfs": {}}


def test_save_manifest_atomic(tmp_path):
    p = tmp_path / "manifest.json"
    holded_export._save_manifest(p, {"version": 1, "resources": {"a": {"items": 5}}})
    data = json.loads(p.read_text())
    assert data["resources"]["a"]["items"] == 5
    assert "updated_at" in data


def test_append_jsonl_iter(tmp_path):
    path = tmp_path / "out.jsonl"
    n = holded_export._append_jsonl_iter(
        path,
        iter([{"id": "a"}, {"id": "b"}, {"id": "c"}]),
    )
    assert n == 3
    lines = path.read_text().splitlines()
    assert len(lines) == 3
    assert json.loads(lines[0]) == {"id": "a"}


def test_append_jsonl_iter_limit(tmp_path):
    path = tmp_path / "out.jsonl"
    n = holded_export._append_jsonl_iter(
        path,
        iter([{"id": i} for i in range(100)]),
        limit=3,
    )
    assert n == 3
    assert len(path.read_text().splitlines()) == 3


def test_append_jsonl_iter_records_errors(tmp_path):
    """Si el generator falla, el error queda en error_log."""
    err_log = tmp_path / "errors.jsonl"
    out = tmp_path / "out.jsonl"

    def fail_after(n):
        for i in range(n):
            yield {"id": i}
        raise RuntimeError("simulated")

    with pytest.raises(RuntimeError):
        holded_export._append_jsonl_iter(
            out, fail_after(2), error_log=err_log, resource_label="contacts"
        )
    err_lines = err_log.read_text().splitlines()
    assert len(err_lines) == 1
    err = json.loads(err_lines[0])
    assert err["resource"] == "contacts"
    assert err["at_item"] == 2
    assert "simulated" in err["error"]


def test_sha256_file(tmp_path):
    p = tmp_path / "x.txt"
    p.write_bytes(b"hello")
    h = holded_export._sha256_file(p)
    # sha256("hello")
    assert h == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_write_atomic(tmp_path):
    p = tmp_path / "subdir" / "file.bin"
    holded_export._write_atomic(p, b"abc")
    assert p.read_bytes() == b"abc"
    # No tmp left over
    assert not (tmp_path / "subdir" / "file.bin.tmp").exists()


def test_date_to_ts():
    assert holded_export._date_to_ts(None) is None
    # 1970-01-01 UTC
    assert holded_export._date_to_ts("1970-01-01") == 0
    # Sanity: 2024 > 0
    assert holded_export._date_to_ts("2024-01-01") > 0


class TestDumpSummary:
    def test_count_jsonl(self, tmp_path):
        import dump_summary  # via conftest path injection
        p = tmp_path / "x.jsonl"
        p.write_text("a\nb\nc\n")
        assert dump_summary.count_jsonl(p) == 3

    def test_fmt_bytes(self):
        import dump_summary
        assert dump_summary.fmt_bytes(0) == "0.0 B"
        assert dump_summary.fmt_bytes(1024) == "1.0 KB"
        assert dump_summary.fmt_bytes(1024 * 1024) == "1.0 MB"
