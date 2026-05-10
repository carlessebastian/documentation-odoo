"""Tests para manifest_lint.py: parser puro y deteccion de errores."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from manifest_lint import ManifestError, lint_one, parse_manifest


def write_module(tmp: Path, name: str, manifest_src: str) -> Path:
    mod = tmp / name
    mod.mkdir()
    (mod / "__manifest__.py").write_text(manifest_src, encoding="utf-8")
    (mod / "__init__.py").write_text("", encoding="utf-8")
    return mod


class TestParseManifest:
    def test_basic_dict(self, tmp_path):
        p = tmp_path / "m.py"
        p.write_text(
            textwrap.dedent("""\
                {
                    'name': 'X',
                    'version': '19.0.1.0.0',
                    'depends': ['base'],
                    'license': 'LGPL-3',
                }
            """),
            encoding="utf-8",
        )
        d = parse_manifest(p)
        assert d["name"] == "X"
        assert d["version"] == "19.0.1.0.0"

    def test_syntax_error(self, tmp_path):
        p = tmp_path / "broken.py"
        p.write_text("{ 'name': 'X' ", encoding="utf-8")
        with pytest.raises(ManifestError) as exc:
            parse_manifest(p)
        assert "SyntaxError" in str(exc.value)

    def test_non_literal(self, tmp_path):
        p = tmp_path / "nl.py"
        p.write_text(
            "{'name': 'X', 'version': '19.0.' + str(1)}", encoding="utf-8"
        )
        with pytest.raises(ManifestError):
            parse_manifest(p)

    def test_not_a_dict(self, tmp_path):
        p = tmp_path / "list.py"
        p.write_text("['name', 'X']", encoding="utf-8")
        with pytest.raises(ManifestError):
            parse_manifest(p)


class TestLintOne:
    def _good(self) -> str:
        return textwrap.dedent("""\
            {
                'name': 'My Module',
                'version': '19.0.1.0.0',
                'depends': ['base'],
                'license': 'LGPL-3',
                'category': 'Tools',
                'summary': 'Doc',
                'author': 'Me',
                'installable': True,
            }
        """)

    def test_ok(self, tmp_path):
        mod = write_module(tmp_path, "good_one", self._good())
        r = lint_one(mod)
        assert r["status"] == "ok"
        assert not r["errors"]
        assert not r["warnings"]

    def test_missing_required(self, tmp_path):
        src = "{'name': 'X', 'depends': []}"
        mod = write_module(tmp_path, "bad_one", src)
        r = lint_one(mod)
        assert r["status"] == "error"
        # falta version y license
        assert any("version" in e for e in r["errors"])
        assert any("license" in e for e in r["errors"])

    def test_wrong_version_prefix_warns(self, tmp_path):
        src = textwrap.dedent("""\
            {'name': 'X', 'version': '18.0.1.0.0',
             'depends': ['base'], 'license': 'LGPL-3'}
        """)
        mod = write_module(tmp_path, "old_ver", src)
        r = lint_one(mod)
        assert r["status"] == "warn"
        assert any("19.0." in w for w in r["warnings"])

    def test_installable_false_warns(self, tmp_path):
        src = textwrap.dedent("""\
            {'name': 'X', 'version': '19.0.1.0.0',
             'depends': ['base'], 'license': 'LGPL-3',
             'installable': False}
        """)
        mod = write_module(tmp_path, "not_inst", src)
        r = lint_one(mod)
        assert any("installable=False" in w for w in r["warnings"])

    def test_legacy_openerp(self, tmp_path):
        mod = tmp_path / "legacy"
        mod.mkdir()
        (mod / "__openerp__.py").write_text("{}", encoding="utf-8")
        r = lint_one(mod)
        assert r["status"] == "error"
        assert any("__openerp__.py" in e for e in r["errors"])

    def test_no_manifest_skip(self, tmp_path):
        d = tmp_path / "nope"
        d.mkdir()
        r = lint_one(d)
        assert r["status"] == "skip"

    def test_empty_depends_warns(self, tmp_path):
        src = textwrap.dedent("""\
            {'name': 'X', 'version': '19.0.1.0.0',
             'depends': [], 'license': 'LGPL-3'}
        """)
        mod = write_module(tmp_path, "no_deps", src)
        r = lint_one(mod)
        assert any("depends" in w and "vacio" in w for w in r["warnings"])

    def test_unknown_license_warns(self, tmp_path):
        src = textwrap.dedent("""\
            {'name': 'X', 'version': '19.0.1.0.0',
             'depends': ['base'], 'license': 'WTFPL'}
        """)
        mod = write_module(tmp_path, "weird_lic", src)
        r = lint_one(mod)
        assert any("WTFPL" in w for w in r["warnings"])
