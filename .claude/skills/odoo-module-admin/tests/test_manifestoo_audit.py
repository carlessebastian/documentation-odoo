"""Tests para wrappers de manifestoo_audit.py."""
from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from _common import OdooError
import manifestoo_audit


class TestCheckManifestooAvailable:
    def test_not_installed(self):
        with patch.object(subprocess, "run", side_effect=FileNotFoundError):
            with pytest.raises(OdooError) as exc:
                manifestoo_audit.check_manifestoo_available()
            assert "no esta instalado" in str(exc.value)

    def test_installed(self):
        ok = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="manifestoo 1.0.0\n", stderr=""
        )
        with patch.object(subprocess, "run", return_value=ok):
            v = manifestoo_audit.check_manifestoo_available()
            assert "manifestoo" in v


class TestRunManifestoo:
    def test_basic_command(self, tmp_path):
        good = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="m1\nm2\n", stderr=""
        )
        with patch.object(subprocess, "run", return_value=good) as fake:
            manifestoo_audit.run_manifestoo(
                tmp_path, "list", None, "19.0"
            )
            cmd = fake.call_args[0][0]
            assert cmd[0] == "manifestoo"
            assert "--addons-dir" in cmd
            assert str(tmp_path) in cmd
            assert "--odoo-series" in cmd
            assert "19.0" in cmd
            assert cmd[-1] == "list"

    def test_select_csv(self, tmp_path):
        good = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch.object(subprocess, "run", return_value=good) as fake:
            manifestoo_audit.run_manifestoo(
                tmp_path, "list-depends", ["a", "b"], "19.0"
            )
            cmd = fake.call_args[0][0]
            assert "--select" in cmd
            assert "a,b" in cmd

    def test_action_check(self, tmp_path):
        good = subprocess.CompletedProcess(args=[], returncode=2, stdout="", stderr="")
        with patch.object(subprocess, "run", return_value=good):
            rc, _, _ = manifestoo_audit.run_manifestoo(
                tmp_path, "check", None, "19.0"
            )
            assert rc == 2


class TestValidActions:
    def test_includes_canonical_actions(self):
        for action in ("list", "list-depends", "check", "tree"):
            assert action in manifestoo_audit.VALID_ACTIONS
