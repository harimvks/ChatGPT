"""Tests for the optional GAIEP ModelCall provenance wrapper."""

from __future__ import annotations

from decimal import Decimal
from typing import NoReturn

import pytest
from providers.provider import AIModelOptions

from runner.gateway_client import ChatResult, GatewayClientError
from runner.model_provenance import with_provenance

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


def _chat_result(
    text: str = "model output", *, failed_over_from: tuple[str, ...] = ()
) -> ChatResult:
    return ChatResult(
        text=text,
        model="qwen3.6:27b",
        elapsed_seconds=0.25,
        provider_name="qwen_primary",
        options=_OPTS,
        context_id="ctx-1",
        context_hash="hash-1",
        execution_id="exec-1",
        failed_over_from=failed_over_from,
    )


def test_with_provenance_persists_success_and_returns_original_chat_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    result = _chat_result("hello from model", failed_over_from=("qwen_timeout",))

    def fake_log_response(**kwargs: object) -> object:
        calls.append(kwargs)
        return object()

    monkeypatch.setattr("runner.model_provenance.log_response", fake_log_response)

    wrapped = with_provenance(
        lambda _system, _user: result,
        capability_name="coding",
        prompt_id="implementation",
        prompt_version="v2",
    )

    returned = wrapped("system text", "user text")

    assert returned is result
    assert returned.failed_over_from == ("qwen_timeout",)
    assert len(calls) == 1
    call = calls[0]
    assert call["output_text"] == "hello from model"
    assert call["options"] is _OPTS
    assert call["provider_name"] == "qwen_primary"
    assert call["capability_name"] == "coding"
    assert call["context_id"] == "ctx-1"
    assert call["context_hash"] == "hash-1"
    assert call["prompt_id"] == "implementation"
    assert call["prompt_version"] == "v2"
    assert call["input_token_estimate"] == 4
    assert call["output_token_estimate"] == 3
    assert call["execution_id"] == "exec-1"


def test_provider_failure_propagates_without_successful_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_log_response(**_kwargs: object) -> NoReturn:
        raise AssertionError("provider failures must not be logged as successful completions")

    def failing_model_call(_system: str, _user: str) -> NoReturn:
        raise GatewayClientError("provider failed")

    monkeypatch.setattr("runner.model_provenance.log_response", fake_log_response)
    wrapped = with_provenance(
        failing_model_call,
        capability_name="coding",
        prompt_id="implementation",
        prompt_version="v2",
    )

    with pytest.raises(GatewayClientError, match="provider failed"):
        wrapped("system", "user")


def test_artifact_failure_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing_log_response(**_kwargs: object) -> NoReturn:
        raise OSError("artifact store unavailable")

    monkeypatch.setattr("runner.model_provenance.log_response", failing_log_response)
    wrapped = with_provenance(
        lambda _system, _user: _chat_result(),
        capability_name="coding",
        prompt_id="implementation",
        prompt_version="v2",
        fail_closed=True,
    )

    with pytest.raises(OSError, match="artifact store unavailable"):
        wrapped("system", "user")


def test_artifact_failure_can_fail_open_when_explicitly_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_log_response(**_kwargs: object) -> NoReturn:
        raise OSError("artifact store unavailable")

    result = _chat_result()
    monkeypatch.setattr("runner.model_provenance.log_response", failing_log_response)
    wrapped = with_provenance(
        lambda _system, _user: result,
        capability_name="coding",
        prompt_id="implementation",
        prompt_version="v2",
        fail_closed=False,
    )

    assert wrapped("system", "user") is result
