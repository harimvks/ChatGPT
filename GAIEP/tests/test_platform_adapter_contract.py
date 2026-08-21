from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from platform_vnext.compat.platform_adapter import AdapterRequest, GreenZPlatformAdapter


@dataclass(frozen=True)
class FakeOptions:
    model: str = "qwen3.6:27b"


@dataclass(frozen=True)
class FakeTiming:
    total_duration_ns: int = 2_500_000_000


@dataclass(frozen=True)
class FakeProviderResponse:
    output_text: str = "implemented"
    options: FakeOptions = FakeOptions()
    timing: FakeTiming = FakeTiming()


@dataclass(frozen=True)
class FakeGatewayResponse:
    provider_name: str = "local_qwen"
    provider_response: FakeProviderResponse = FakeProviderResponse()
    execution_id: str = "exec-1"
    failed_over_from: tuple[str, ...] = ()


class FakeGateway:
    def __init__(self) -> None:
        self.calls: list[object] = []

    def reason(self, **kwargs: object) -> FakeGatewayResponse:
        self.calls.append(kwargs)
        return FakeGatewayResponse()


def test_adapter_delegates_to_existing_gateway() -> None:
    gateway = FakeGateway()
    adapter = GreenZPlatformAdapter(gateway)
    request = AdapterRequest(
        capability_name="python-implementation",
        capability_version="1",
        capability_tag="coding",
        template="Implement the requested change.",
        context_manifest=object(),
        context_id="ctx-1",
        context_hash="hash-1",
        classification="INTERNAL",
    )

    response = adapter.generate(request)

    assert response.text == "implemented"
    assert response.model == "qwen3.6:27b"
    assert response.provider_name == "local_qwen"
    assert response.elapsed_seconds == 2.5
    assert response.execution_id == "exec-1"
    assert response.failed_over_from == ()
    assert len(gateway.calls) == 1

    reasoning_request = gateway.calls[0]["request"]
    assert reasoning_request.capability_tag == "coding"
    assert reasoning_request.manifest is request.context_manifest
    assert gateway.calls[0]["template"] == request.template
