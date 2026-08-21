"""Bootstrap the real GreenZ engineering Gateway without duplicating its composition root.

The engineering repository already owns the production composition in ``runner.gateway_client``:
load registry -> resolve certification -> load models -> build Gateway. This module discovers that
composition by explicit dotted-path configuration and hands the resulting Gateway to GAIEP-LAB.
No provider, registry, or Ollama client is constructed here.
"""
from __future__ import annotations

from dataclasses import dataclass
import importlib
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, cast

from platform_vnext.compat.gateway_protocol import GreenZGateway, ReasoningRequestFactory
from platform_vnext.compat.platform_adapter import GreenZPlatformAdapter


@dataclass(frozen=True)
class GatewayCompositionSpec:
    module: str = "runner.gateway_client"
    build_registry: str = "build_registry"
    build_models: str = "build_models"
    build_gateway: str = "build_gateway"
    reasoning_request: str = "gateway.ReasoningRequest"


@dataclass(frozen=True)
class GatewayRuntime:
    gateway: GreenZGateway
    adapter: GreenZPlatformAdapter


def _load_module(path: str) -> ModuleType:
    try:
        return importlib.import_module(path)
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            f"GreenZ engineering Gateway module {path!r} is unavailable; "
            "activate the environment containing greenz-ai-engineering and greenz-ai-platform"
        ) from exc


def _load_attr(path: str) -> Any:
    module_name, separator, attr_name = path.rpartition(".")
    if not separator:
        raise ValueError(f"dotted path required: {path!r}")
    return getattr(_load_module(module_name), attr_name)


def _callable(module: ModuleType, name: str) -> Callable[..., Any]:
    value = getattr(module, name, None)
    if not callable(value):
        raise RuntimeError(f"Gateway composition member {module.__name__}.{name} is not callable")
    return cast(Callable[..., Any], value)


def build_existing_gateway(
    *,
    registry_path: Path,
    certifications_dir: Path,
    base_url: str,
    spec: GatewayCompositionSpec = GatewayCompositionSpec(),
    observability_dir: Path | None = None,
) -> GatewayRuntime:
    """Use the existing engineering composition root and adapt its Gateway to VNext."""
    engineering = _load_module(spec.module)
    build_registry = _callable(engineering, spec.build_registry)
    build_models = _callable(engineering, spec.build_models)
    build_gateway = _callable(engineering, spec.build_gateway)

    registry = build_registry(
        registry_path=registry_path,
        certifications_dir=certifications_dir,
    )
    models = build_models(registry_path=registry_path)
    gateway = build_gateway(
        registry=registry,
        models=models,
        base_url=base_url,
        observability_dir=observability_dir,
    )
    reasoning_request = cast(ReasoningRequestFactory, _load_attr(spec.reasoning_request))
    adapter = GreenZPlatformAdapter(cast(GreenZGateway, gateway), reasoning_request)
    return GatewayRuntime(gateway=cast(GreenZGateway, gateway), adapter=adapter)
