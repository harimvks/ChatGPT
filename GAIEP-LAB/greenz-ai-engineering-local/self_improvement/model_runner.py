"""Provider-neutral model execution contracts for research rollouts.

The self-improvement layer depends on this interface rather than Ollama, MLX,
llama.cpp, or any particular model provider. Concrete adapters remain outside
the research policy boundary.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from .task_factory import EngineeringTask


@dataclass(frozen=True)
class ModelRequest:
    task: EngineeringTask
    prompt: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelResult:
    artifact: object
    model_name: str
    endpoint_model: str | None = None
    latency_s: float | None = None
    usage: Mapping[str, object] = field(default_factory=dict)
    metadata: Mapping[str, object] = field(default_factory=dict)


class ModelRunner(Protocol):
    """Minimal provider-neutral contract for one research model invocation."""

    def run(self, request: ModelRequest) -> ModelResult:
        ...


class CallableModelRunner:
    """Adapt a deterministic Python callable to the ModelRunner contract."""

    def __init__(self, fn, *, model_name: str, endpoint_model: str | None = None) -> None:
        self._fn = fn
        self._model_name = model_name
        self._endpoint_model = endpoint_model

    def run(self, request: ModelRequest) -> ModelResult:
        return ModelResult(
            artifact=self._fn(request.task),
            model_name=self._model_name,
            endpoint_model=self._endpoint_model,
        )
