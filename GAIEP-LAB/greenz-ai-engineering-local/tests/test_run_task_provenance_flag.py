"""Coverage for GAIEP provenance feature flag wiring in _default_model_call()."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from providers.provider import AIModelOptions

from runner import run_task as rt
from runner.config import GeosConfig
from runner.gateway_client import ChatResult

_OPTS = AIModelOptions(
    provider="ollama",
    model="qwen3.6:27b",
    model_version="27b",
    quantization="Q4_K_M",
    temperature=Decimal("0.1"),
    seed=None,
    context_window=32768,
    runtime_version="ollama-0.31.1",
    max_output_tokens=16384,
)


def _chat_result() -> ChatResult:
    return ChatResult(
        text="model output",
        model="qwen3.6:27b",
        elapsed_seconds=0.01,
        provider_name="fake_provider",
        options=_OPTS,
        context_id="ctx-fake",
        context_hash="deadbeef",
        execution_id="exec-fake",
    )


def _patch_gateway_plumbing(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_build_registry(**_kwargs: object) -> object:
        return object()

    def fake_build_models(**_kwargs: object) -> object:
        return object()

    def fake_build_gateway(**_kwargs: object) -> object:
        return object()

    def fake_chat(**_kwargs: Any) -> ChatResult:
        return _chat_result()

    monkeypatch.setattr(rt, "build_registry", fake_build_registry)
    monkeypatch.setattr(rt, "build_models", fake_build_models)
    monkeypatch.setattr(rt, "build_gateway", fake_build_gateway)
    monkeypatch.setattr(rt, "chat", fake_chat)


def test_default_model_call_is_unwrapped_when_gaiep_provenance_is_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = {"log_response": 0}

    def fake_log_response(**_kwargs: object) -> None:
        calls["log_response"] += 1

    _patch_gateway_plumbing(monkeypatch)
    monkeypatch.setattr("runner.model_provenance.log_response", fake_log_response)

    model_call = rt._default_model_call(
        GeosConfig("http://local", 30, 1000),
        repo_root=tmp_path,
    )

    assert model_call("system", "user").execution_id == "exec-fake"
    assert calls["log_response"] == 0


def test_default_model_call_wraps_when_gaiep_provenance_is_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict[str, object]] = []

    def fake_log_response(**kwargs: object) -> None:
        calls.append(kwargs)

    def fake_prompt_version(_root: Path) -> str:
        return "v2"

    _patch_gateway_plumbing(monkeypatch)
    monkeypatch.setattr(rt.ctx, "load_system_prompt_version", fake_prompt_version)
    monkeypatch.setattr("runner.model_provenance.log_response", fake_log_response)

    model_call = rt._default_model_call(
        GeosConfig(
            "http://local",
            30,
            1000,
            gaiep_provenance_enabled=True,
            gaiep_provenance_fail_closed=True,
        ),
        repo_root=tmp_path,
    )

    assert model_call("system", "user").execution_id == "exec-fake"
    assert len(calls) == 1
    assert calls[0]["execution_id"] == "exec-fake"
    assert calls[0]["context_hash"] == "deadbeef"
    assert calls[0]["prompt_version"] == "v2"
