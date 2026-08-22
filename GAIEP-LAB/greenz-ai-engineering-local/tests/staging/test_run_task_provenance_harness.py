from pathlib import Path

import pytest

from runner.gateway_client import ChatResult
from staging.run_task_provenance_harness import ProvenanceSettings, build_model_call


def _result(text: str = "staged") -> ChatResult:
    return ChatResult(
        text=text,
        model="test-model",
        provider_name="test-provider",
        execution_id="exec-1",
        context_id="ctx-1",
        context_hash="hash-1",
        elapsed_seconds=0.01,
        failed_over_from=(),
    )


def test_disabled_flag_preserves_original_callable(tmp_path: Path) -> None:
    original = lambda _s, _u: _result()
    wrapped = build_model_call(
        original,
        settings=ProvenanceSettings(enabled=False),
        repo_root=tmp_path,
        run_id="run-1",
    )
    assert wrapped is original


def test_enabled_flag_adds_provenance(tmp_path: Path) -> None:
    original = lambda _s, _u: _result("enabled")
    wrapped = build_model_call(
        original,
        settings=ProvenanceSettings(enabled=True),
        repo_root=tmp_path,
        run_id="run-2",
    )

    result = wrapped("s", "u")
    assert result.text == "enabled"
    artifacts = tmp_path / "artifacts"
    assert (artifacts / "index.db").exists()
    assert any(path.is_file() for path in (artifacts / "sha256").rglob("*"))


def test_enabled_path_propagates_provider_failure(tmp_path: Path) -> None:
    def failing(_s: str, _u: str) -> ChatResult:
        raise RuntimeError("provider failed")

    wrapped = build_model_call(
        failing,
        settings=ProvenanceSettings(enabled=True),
        repo_root=tmp_path,
        run_id="run-3",
    )
    with pytest.raises(RuntimeError, match="provider failed"):
        wrapped("s", "u")

    artifacts = tmp_path / "artifacts"
    if (artifacts / "sha256").exists():
        assert not any(path.is_file() for path in (artifacts / "sha256").rglob("*"))
