"""Tests para helpers puros de checksum_track.py."""
from __future__ import annotations

import checksum_track


class TestParseChecksumOutput:
    def test_two_modules(self):
        out = checksum_track.parse_checksum_output(
            "mod_a " + "a" * 64 + "\nmod_b " + "b" * 64 + "\n"
        )
        assert out == {"mod_a": "a" * 64, "mod_b": "b" * 64}

    def test_skips_invalid_lines(self):
        out = checksum_track.parse_checksum_output(
            "mod_a " + "a" * 64 + "\n"
            "garbage line\n"
            "mod_b shortsha\n"
            "\n"
            "  \n"
            "mod_c " + "c" * 64 + "\n"
        )
        assert set(out) == {"mod_a", "mod_c"}

    def test_empty(self):
        assert checksum_track.parse_checksum_output("") == {}


class TestDiffChecksums:
    def test_no_change(self):
        cur = {"a": "x" * 64, "b": "y" * 64}
        sto = {"a": "x" * 64, "b": "y" * 64}
        d = checksum_track.diff_checksums(cur, sto, ["a", "b"])
        assert d == {"changed": [], "new": [], "gone": []}

    def test_one_changed(self):
        cur = {"a": "x" * 64, "b": "y" * 64}
        sto = {"a": "z" * 64, "b": "y" * 64}
        d = checksum_track.diff_checksums(cur, sto, ["a", "b"])
        assert d["changed"] == ["a"]
        assert d["new"] == []
        assert d["gone"] == []

    def test_new_module_only_if_installed(self):
        cur = {"a": "x" * 64, "b": "y" * 64}  # b is new in code
        sto = {"a": "x" * 64}
        # b NOT in installed yet -> not reported as new
        d = checksum_track.diff_checksums(cur, sto, ["a"])
        assert d["new"] == []
        # b IS installed -> reported as new (worth upgrading)
        d2 = checksum_track.diff_checksums(cur, sto, ["a", "b"])
        assert d2["new"] == ["b"]

    def test_gone(self):
        cur = {"a": "x" * 64}
        sto = {"a": "x" * 64, "b": "y" * 64}
        d = checksum_track.diff_checksums(cur, sto, ["a"])
        assert d["gone"] == ["b"]

    def test_results_sorted(self):
        cur = {"z": "1" * 64, "a": "2" * 64, "m": "3" * 64}
        sto = {}
        d = checksum_track.diff_checksums(cur, sto, ["z", "a", "m"])
        assert d["new"] == ["a", "m", "z"]


class TestParamKey:
    def test_uses_custom_namespace(self):
        # Documenta el contrato implicito con otros scripts/tools
        assert checksum_track.CHECKSUM_PARAM_KEY == "__custom__.module_checksums"
