"""Environment-driven bindings for the controlled GAIEP pilot."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelBinding:
    logical_name: str
    endpoint_model: str


def load_model_binding(logical_name: str) -> ModelBinding:
    """Resolve a logical experiment model without hard-coding a provider."""
    key = "GAIEP_MODEL_" + "".join(ch if ch.isalnum() else "_" for ch in logical_name.upper())
    endpoint_model = os.getenv(key)
    if not endpoint_model:
        raise RuntimeError(f"missing experiment model binding: {key}")
    return ModelBinding(logical_name=logical_name, endpoint_model=endpoint_model)
