"""Compatibility adapter boundary for GAIEP Runtime VNext.

This module intentionally defines only the contract and a thin adapter shape. It does not
reimplement the upstream Gateway, ContextBuilderBase, certification gate, or provider registry.
Those remain the compatibility baseline until contract parity is demonstrated.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class AdapterRequest:
    """Normalized request entering the VNext compatibility boundary."""

    capability_tag: str
    prompt: str
    context_id: str
    context_hash: str
    classification: str


@dataclass(frozen=True)
class AdapterResponse:
    """Normalized response leaving the compatibility boundary."""

    text: str
    model: str
    provider_name: str
    elapsed_seconds: float


class PlatformAdapter(Protocol):
    """Bridge VNext runtime contracts to the existing platform runtime."""

    def generate(self, request: AdapterRequest) -> AdapterResponse:
        """Execute one request through the existing platform selection path."""
        ...


class NotWiredPlatformAdapter:
    """Explicit placeholder until the real upstream composition root is wired.

    Raising here is intentional: VNext must not silently fall back to a duplicate or fake
    provider implementation while compatibility work is incomplete.
    """

    def generate(self, request: AdapterRequest) -> AdapterResponse:
        del request
        raise RuntimeError("GAIEP platform compatibility adapter is not wired yet")
