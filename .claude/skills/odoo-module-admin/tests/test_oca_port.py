"""Tests para wrappers de oca_port.py: construccion de comando y errores."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from _common import OdooError
import oca_port


class TestCheckOcaPortAvailable:
    def test_not_installed(self):
        with patch.object(subprocess, "run", side_effect=FileNotFoundError):
            with pytest.raises(OdooError) as exc:
                oca_port.check_oca_port_available()
            assert "no esta instalado" in str(exc.value)

    def test_installed(self):
        ok = subprocess.CompletedProcess(
            args=["oca-port"], returncode=0, stdout="oca-port 1.2.3\n", stderr=""
        )
        with patch.object(subprocess, "run", return_value=ok):
            v = oca_port.check_oca_port_available()
            assert v == "oca-port 1.2.3"

    def test_command_failed(self):
        bad = subprocess.CompletedProcess(
            args=["oca-port"], returncode=1, stdout="", stderr="boom"
        )
        with patch.object(subprocess, "run", return_value=bad):
            with pytest.raises(OdooError) as exc:
                oca_port.check_oca_port_available()
            assert "boom" in str(exc.value)


class TestRunOcaPort:
    def test_aborts_on_missing_repo(self, tmp_path):
        bad = tmp_path / "nope"
        with pytest.raises(OdooError):
            oca_port.run_oca_port(bad, "mod", "18.0", "19.0")

    def test_constructs_basic_command(self, tmp_path):
        good = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr=""
        )
        with patch.object(subprocess, "run", return_value=good) as fake:
            oca_port.run_oca_port(tmp_path, "l10n_es", "18.0", "19.0")
            fake.assert_called_once()
            call_args = fake.call_args
            cmd = call_args[0][0] if call_args[0] else call_args.kwargs["args"]
            assert cmd[:4] == ["oca-port", "18.0", "19.0", "l10n_es"]

    def test_list_pending_adds_non_interactive(self, tmp_path):
        good = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch.object(subprocess, "run", return_value=good) as fake:
            oca_port.run_oca_port(
                tmp_path, "m", "18.0", "19.0", list_pending=True
            )
            cmd = fake.call_args[0][0]
            assert "--non-interactive" in cmd

    def test_fork_remote_passed(self, tmp_path):
        good = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch.object(subprocess, "run", return_value=good) as fake:
            oca_port.run_oca_port(
                tmp_path, "m", "18.0", "19.0", fork_remote="myfork"
            )
            cmd = fake.call_args[0][0]
            assert "--fork" in cmd
            assert "myfork" in cmd
