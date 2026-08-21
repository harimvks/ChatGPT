"""Thin compatibility adapter over the existing GreenZ AI Platform Gateway."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import importlib
from typing import Any, Protocol


@dataclass(frozen=True)
class AdapterRequest:
    capability_name: str
    capability_version: str
    capability_tag: str
    template: str
    context_manifest: Any
    context_id: str
    context_hash: str
    classification: str


@dataclass(frozen=True)
class AdapterResponse:
    text: str
    model: str
    provider_name: str
    elapsed_seconds: float
    execution_id: str | None
    failed_over_from: tuple[str, ...]


class PlatformAdapter(Protocol):
    def generate(self, request: AdapterRequest) -> AdapterResponse: ...


class GreenZPlatformAdapter:
    """Translate VNext requests to the existing Gateway; do not duplicate platform policy."""

    def __init__(self, gateway: Any) -> None:
        self._gateway = gateway

    def generate(self, request: AdapterRequest) -> AdapterResponse:
        gateway_module = importlib.import_module("gateway.gateway")
        reasoning_request_type = getattr(gateway_module, "ReasoningRequest")
        response = self._gateway.reason(
            request=reasoning_request_type(
                capability_name=request.capability_name,
                capability_version=request.capability_version,
                capability_tag=request.capability_tag,
                manifest=request.context_manifest,
            ),
            template=request.template,
            selected_at=datetime.now(UTC),
        )
        timing = response.provider_response.timing
        elapsed = timing.total_duration_ns / 1e9 if timing and timing.total_duration_ns else 0.0
        return AdapterResponse(
            text=response.provider_response.output_text,
            model=response.provider_response.options.model,
            provider_name=response.provider_name,
            elapsed_seconds=elapsed,
            execution_id=response.execution_id,
            failed_over_from=response.failed_over_from,
        )


class NotWiredPlatformAdapter:
    """Fail-closed placeholder for environments without the platform installed."""

    def generate(self, request: AdapterRequest) -> AdapterResponse:
        del request
        raise RuntimeError("GAIEP platform compatibility adapter is not wired")
