"""Tests para ssh_runner.py: construccion de comandos y --dry-run."""
from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from _common import OdooEnvError
import ssh_runner


@pytest.fixture
def ssh_env(monkeypatch):
    monkeypatch.setenv("DOODBA_SSH_HOST", "odoo@example.com")
    monkeypatch.setenv("DOODBA_PROJECT_DIR", "/opt/doodba/test")
    monkeypatch.setenv("DOODBA_DB_NAME", "testdb")
    monkeypatch.setenv("DOODBA_COMPOSE_SERVICE", "odoo")


class TestGetSshConfig:
    def test_reads_env(self, ssh_env):
        cfg = ssh_runner.get_ssh_config()
        assert cfg["host"] == "odoo@example.com"
        assert cfg["project_dir"] == "/opt/doodba/test"
        assert cfg["compose_service"] == "odoo"
        assert cfg["db_name"] == "testdb"

    def test_aborts_when_host_missing(self, monkeypatch):
        monkeypatch.delenv("DOODBA_SSH_HOST", raising=False)
        with pytest.raises(OdooEnvError) as exc:
            ssh_runner.get_ssh_config()
        assert "DOODBA_SSH_HOST" in str(exc.value)

    def test_compose_service_default(self, monkeypatch):
        monkeypatch.setenv("DOODBA_SSH_HOST", "h")
        monkeypatch.delenv("DOODBA_COMPOSE_SERVICE", raising=False)
        cfg = ssh_runner.get_ssh_config()
        assert cfg["compose_service"] == "odoo"


class TestBuildSshCmd:
    def test_basic(self):
        cmd = ssh_runner.build_ssh_cmd("user@host", "ls /tmp")
        assert cmd[0] == "ssh"
        assert "-o" in cmd
        assert "BatchMode=yes" in cmd
        assert cmd[-2:] == ["user@host", "ls /tmp"]

    def test_extra(self):
        cmd = ssh_runner.build_ssh_cmd(
            "user@host", "ls", ssh_extra=["-i", "/tmp/key"]
        )
        assert "-i" in cmd
        assert "/tmp/key" in cmd


class TestQuoteRemote:
    def test_quotes_spaces(self):
        out = ssh_runner.quote_remote(["odoo", "-d", "my db"])
        assert "'my db'" in out

    def test_quotes_special(self):
        out = ssh_runner.quote_remote(["echo", "$HOME"])
        assert "'$HOME'" in out


class TestRunDryRun:
    def test_dry_run_does_not_call_subprocess(self, ssh_env):
        with patch.object(subprocess, "run") as fake:
            result = ssh_runner.run("ls /tmp", dry_run=True)
            fake.assert_not_called()
        assert result.returncode == 0
        assert "DRY RUN" in result.stdout
        assert result.cmd[0] == "ssh"

    def test_real_run_calls_subprocess(self, ssh_env):
        completed = subprocess.CompletedProcess(
            args=["ssh"], returncode=0, stdout="ok\n", stderr=""
        )
        with patch.object(subprocess, "run", return_value=completed) as fake:
            result = ssh_runner.run("echo ok", dry_run=False)
            fake.assert_called_once()
        assert result.returncode == 0
        assert result.stdout == "ok\n"


class TestIsTransportFailure:
    def test_255_is_transport(self):
        r = ssh_runner.SshResult(returncode=255, stdout="", stderr="", cmd=[])
        assert ssh_runner.is_transport_failure(r)

    def test_other_codes_arent(self):
        for code in (0, 1, 2, 130, 137):
            r = ssh_runner.SshResult(returncode=code, stdout="", stderr="", cmd=[])
            assert not ssh_runner.is_transport_failure(r)


class TestDockerComposeRun:
    def test_dry_run_builds_docker_compose_command(self, ssh_env):
        result = ssh_runner.docker_compose_run(
            ["odoo", "--stop-after-init", "-d", "testdb", "-i", "l10n_es"],
            dry_run=True,
        )
        assert "docker compose run --rm -T odoo" in result.stdout
        assert "/opt/doodba/test" in result.stdout
        assert "l10n_es" in result.stdout

    def test_includes_extra_compose_args(self, ssh_env):
        result = ssh_runner.docker_compose_run(
            ["echo", "x"],
            dry_run=True,
            extra_compose_args=("-e", "FOO=bar"),
        )
        assert "FOO=bar" in result.stdout


class TestDockerComposeRestart:
    def test_dry_run_uses_configured_service(self, monkeypatch):
        monkeypatch.setenv("DOODBA_SSH_HOST", "h")
        monkeypatch.setenv("DOODBA_PROJECT_DIR", "/p")
        monkeypatch.setenv("DOODBA_COMPOSE_SERVICE", "odooweb")
        result = ssh_runner.docker_compose_restart(dry_run=True)
        assert "docker compose restart odooweb" in result.stdout
