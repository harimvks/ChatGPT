"""Small protocol for adapting the existing GreenZ Gateway without importing it at module load."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class GatewayTiming:
    total_duration_ns: int | None = None


@dataclass(frozen=True)
class GatewayProviderOptions:
    model: str


@dataclass(frozen=True)
class GatewayProviderResponse:
    output_text: str
    options: GatewayProviderOptions
    timing: GatewayTiming | None = None


@dataclass(frozen=True)
class GatewayResponse:
    provider_response: GatewayProviderResponse
    provider_name: str
    execution_id: str | None = None
    failed_over_from: tuple[str, ...] = ()


class GreenZGateway(Protocol):
    def reason(self, *, request: Any, template: str, selected_at: datetime) -> GatewayResponse: ...


class ReasoningRequestFactory(Protocol):
    def __call__(self, *, capability_name: str, capability_version: str, capability_tag: str, manifest: Any) -> Any: ...
