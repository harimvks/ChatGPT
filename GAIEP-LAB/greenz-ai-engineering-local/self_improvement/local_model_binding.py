"""Thin local-backend binding for the governed research runner.

The backend is injected by the application. This module does not select a
provider, call a provider SDK, or bypass the governed rollout boundary.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from .gateway_rollout import GatewayResearchRollout
from .model_runner import ModelResult
from .runner_adapter import GovernedModelRunner


class LocalModelBackend(Protocol):
    """Minimal callable contract for an already configured local backend."""

    def __call__(self, system: str, user: str) -> Any: ...


class LocalGovernedModelRunner(GovernedModelRunner):
    """Bind an injected local backend to the existing governed rollout path."""

    def __init__(
        self,
        backend: LocalModelBackend,
        *,
        model_name: str,
        endpoint_model: str | None = None,
        scaffold_name: str = "inspect-plan-implement-test",
    ) -> None:
        rollout = GatewayResearchRollout(
            backend,
            model_name=model_name,
            endpoint_model=endpoint_model,
            scaffold_name=scaffold_name,
        )
        super().__init__(
            lambda request: rollout.run(request.task),
            model_name=model_name,
            endpoint_model=endpoint_model,
        )


def local_backend_metadata(result: ModelResult) -> Mapping[str, object]:
    """Return provider-neutral metadata for reports and provenance."""

    return {
        "model_name": result.model_name,
        "endpoint_model": result.endpoint_model,
        "latency_s": result.latency_s,
        "usage": dict(result.usage),
    }
