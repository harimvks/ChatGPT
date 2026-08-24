"""
greenz-ai-engineering

Module:        Runner / Config
Purpose:       Load harness settings — where to reach the local Ollama server, request timeouts,
               the context budget — so the runner never hardcodes them.

               CORRECTED during the port from GreenZAlgoV3's scripts/geos/config.py: V3's version
               read ``ollama.model``/``ollama.fallback_model`` out of configs/ai/ai.yaml — the
               exact defect this port exists to fix (ai.yaml still named qwen3:14b/qwen3:8b,
               neither installed, confirmed live against V3 HEAD 56cacc5 before this port). Under
               the Gateway, which model runs is a consequence of the capability tag and the
               certified provider registry (see runner/gateway_client.py), never a config value
               this harness owns — so ``model``/``fallback_model`` are gone from GeosConfig
               entirely, not renamed or defaulted. What's left is genuinely this harness's own
               environment concern: where the local Ollama server is, how long to wait, and the
               context budget — none of that is a Gateway/registry question.
Owner:         Runner
Public:        No
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNNER_CONFIG = REPO_ROOT / "runner" / "config" / "runner.yaml"


class ConfigError(RuntimeError):
    """Raised when the runner config file is missing or malformed."""


@dataclass(frozen=True)
class GeosConfig:
    """Resolved harness configuration (bounded, immutable). No model name lives here — see
    module docstring."""

    base_url: str
    request_timeout_seconds: int
    max_context_tokens: int
    input_headroom_tokens: int = 16384
    gaiep_provenance_enabled: bool = False
    gaiep_provenance_fail_closed: bool = True

    @property
    def chat_url(self) -> str:
        """The Ollama /api/generate endpoint for this base URL."""
        return f"{self.base_url.rstrip('/')}/api/generate"


def _require(mapping: dict[str, Any], key: str, source: Path) -> Any:
    if key not in mapping:
        raise ConfigError(f"{source}: missing required key '{key}'")
    return mapping[key]


def load_config(path: Path | None = None) -> GeosConfig:
    """Load and validate the runner config from a runner.yaml file.

    Raises ConfigError with an actionable message if the file is missing or a required
    section/key is absent."""
    source = path or DEFAULT_RUNNER_CONFIG
    if not source.is_file():
        raise ConfigError(
            f"Runner config not found at {source}. Restore runner/config/runner.yaml."
        )
    # Each `cast` below follows a runtime isinstance check that has ALREADY established the shape
    # -- it narrows the static type from dict[Unknown, Unknown] to something usable and asserts
    # nothing the line above has not just verified. The cast cannot replace the check: a bare
    # re-annotation would make the isinstance look redundant to pyright (reportUnnecessaryIsInstance)
    # while the check is exactly what makes a malformed runner.yaml an actionable ConfigError
    # rather than an AttributeError three frames later. Same idiom greenz-ai-platform settled on
    # for its own YAML loaders.
    loaded: Any = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ConfigError(f"{source}: top level must be a YAML mapping.")
    raw = cast(dict[str, Any], loaded)

    ollama_section = _require(raw, "ollama", source)
    if not isinstance(ollama_section, dict):
        raise ConfigError(f"{source}: 'ollama' section must be a mapping.")
    ollama = cast(dict[str, Any], ollama_section)

    # `: Any` on these two is load-bearing, not decoration: the `or {}` fallback makes the
    # expression `Any | dict[Unknown, Unknown]` (the empty literal has no element types), and the
    # union is what pyright reports as partially unknown. Declaring the intermediate Any lets the
    # isinstance below do the narrowing, exactly as it does for the two sections above.
    context_builder_section: Any = raw.get("context_builder") or {}
    if not isinstance(context_builder_section, dict):
        raise ConfigError(f"{source}: 'context_builder' section must be a mapping.")
    context_builder = cast(dict[str, Any], context_builder_section)

    provenance_section: Any = raw.get("gaiep_provenance") or {}
    if not isinstance(provenance_section, dict):
        raise ConfigError(f"{source}: 'gaiep_provenance' section must be a mapping.")
    provenance = cast(dict[str, Any], provenance_section)

    return GeosConfig(
        base_url=str(_require(ollama, "base_url", source)),
        request_timeout_seconds=int(ollama.get("request_timeout_seconds", 120)),
        max_context_tokens=int(context_builder.get("max_context_tokens", 12000)),
        input_headroom_tokens=int(context_builder.get("input_headroom_tokens", 16384)),
        gaiep_provenance_enabled=bool(provenance.get("enabled", False)),
        gaiep_provenance_fail_closed=bool(provenance.get("fail_closed", True)),
    )
