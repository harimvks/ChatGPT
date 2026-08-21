from dataclasses import dataclass
from datetime import datetime

from platform_vnext.compat.platform_adapter import AdapterRequest, GreenZPlatformAdapter


@dataclass(frozen=True)
class Timing:
    total_duration_ns: int = 1_500_000_000


@dataclass(frozen=True)
class Options:
    model: str = "qwen3.6:27b"


@dataclass(frozen=True)
class ProviderResponse:
    output_text: str = "implemented"
    options: Options = Options()
    timing: Timing = Timing()


@dataclass(frozen=True)
class GatewayResponse:
    provider_response: ProviderResponse = ProviderResponse()
    provider_name: str = "ollama"
    execution_id: str = "exec-1"
    failed_over_from: tuple[str, ...] = ()


class Gateway:
    def __init__(self):
        self.calls = []

    def reason(self, *, request, template: str, selected_at: datetime):
        self.calls.append((request, template, selected_at))
        return GatewayResponse()


def test_adapter_delegates_to_injected_gateway():
    gateway = Gateway()
    factory_calls = []

    def factory(**kwargs):
        factory_calls.append(kwargs)
        return {"request": kwargs}

    adapter = GreenZPlatformAdapter(gateway, factory)
    result = adapter.generate(
        AdapterRequest("python", "1", "CODING", "do task", "manifest", "ctx", "hash", "INTERNAL")
    )

    assert result.text == "implemented"
    assert result.model == "qwen3.6:27b"
    assert result.provider_name == "ollama"
    assert result.elapsed_seconds == 1.5
    assert result.execution_id == "exec-1"
    assert factory_calls[0]["capability_name"] == "python"
    assert gateway.calls[0][1] == "do task"
