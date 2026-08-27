"""Adapt the existing governed rollout boundary to ModelRunner.

This module intentionally does not select providers, call MCP directly, or own
authorization. A caller supplies the already-governed rollout callable.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from time import monotonic

from .model_runner import ModelRequest, ModelResult, ModelRunner


GovernedRollout = Callable[[ModelRequest], object]


class GovernedModelRunner:
    """ModelRunner adapter for an externally governed rollout callable."""

    def __init__(
        self,
        rollout: GovernedRollout,
        *,
        model_name: str,
        endpoint_model: str | None = None,
    ) -> None:
        self._rollout = rollout
        self._model_name = model_name
        self._endpoint_model = endpoint_model

    def run(self, request: ModelRequest) -> ModelResult:
        started = monotonic()
        artifact = self._rollout(request)
        return ModelResult(
            artifact=artifact,
            model_name=self._model_name,
            endpoint_model=self._endpoint_model,
            latency_s=monotonic() - started,
        )


def model_runner_metadata(result: ModelResult) -> Mapping[str, object]:
    """Return stable metadata suitable for rollout provenance."""

    return {
        "model_name": result.model_name,
        "endpoint_model": result.endpoint_model,
        "latency_s": result.latency_s,
        "usage": dict(result.usage),
    }
