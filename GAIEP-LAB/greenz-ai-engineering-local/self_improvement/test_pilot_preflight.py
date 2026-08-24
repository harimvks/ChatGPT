import pytest

from self_improvement.pilot_preflight import (
    assert_preflight,
    check_required_environment,
)


def test_preflight_reads_required_bindings(monkeypatch):
    monkeypatch.setenv("GAIEP_MODEL_SMALL_PYTHON_CODER", "candidate-model")
    monkeypatch.setenv("GAIEP_MODEL_QWEN3_6_27B", "qwen3.6:27b")
    checks = check_required_environment(("small-python-coder", "qwen3.6-27b"))
    assert all(check.passed for check in checks)


def test_preflight_fails_closed(monkeypatch):
    monkeypatch.delenv("GAIEP_MODEL_SMALL_PYTHON_CODER", raising=False)
    with pytest.raises(RuntimeError, match="pilot preflight failed"):
        assert_preflight(check_required_environment(("small-python-coder",)))
