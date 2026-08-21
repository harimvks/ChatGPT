from pathlib import Path

import pytest

from platform_vnext.skills.validation.command_runner import ValidationCommand, ValidationCommandRunner


def test_allowlisted_command_runs(tmp_path: Path):
    runner = ValidationCommandRunner(workspace=tmp_path, allowed_commands=("python",))
    result = runner.run(ValidationCommand("python-version", ("python", "-c", "print('ok')")))
    assert result.passed
    assert result.return_code == 0
    assert "ok" in result.stdout


def test_non_allowlisted_command_is_rejected(tmp_path: Path):
    runner = ValidationCommandRunner(workspace=tmp_path, allowed_commands=("python",))
    with pytest.raises(PermissionError):
        runner.run(ValidationCommand("shell", ("bash", "-lc", "echo unsafe")))


def test_timeout_is_recorded(tmp_path: Path):
    runner = ValidationCommandRunner(workspace=tmp_path, allowed_commands=("python",))
    result = runner.run(ValidationCommand("timeout", ("python", "-c", "import time; time.sleep(2)"), timeout_seconds=1))
    assert result.timed_out
    assert not result.passed
