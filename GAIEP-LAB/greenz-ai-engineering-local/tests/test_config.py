"""
greenz-ai-engineering

Module:        Tests / Config
Purpose:       Regression tests for runner/config.py's load_config()/GeosConfig. Loads the real
               runner/config/runner.yaml shipped in this repo (per this repo's CLAUDE.md
               "prefer real data" testing philosophy) rather than a fabricated fixture, and
               guards the CORRECTED-during-port fact that GeosConfig carries no model/
               fallback_model field -- see config.py's own module docstring for why that field
               was removed rather than renamed or defaulted.
Owner:         Tests
Public:        No
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from runner.config import DEFAULT_RUNNER_CONFIG, ConfigError, GeosConfig, load_config


def test_load_config_reads_real_runner_yaml() -> None:
    """Loads runner/config/runner.yaml -- the actual file in this repo, not a fabricated one."""
    assert DEFAULT_RUNNER_CONFIG.is_file(), "runner/config/runner.yaml must exist for this test"
    config = load_config()

    assert config.base_url == "http://localhost:11434"
    assert config.request_timeout_seconds == 120
    assert config.max_context_tokens == 12000
    assert config.gaiep_provenance_enabled is False
    assert config.gaiep_provenance_fail_closed is True


def test_load_config_explicit_default_path_matches_no_arg() -> None:
    """Passing the default path explicitly must be equivalent to omitting it."""
    assert load_config(DEFAULT_RUNNER_CONFIG) == load_config()


def test_chat_url_derives_from_base_url() -> None:
    config = load_config()
    assert config.chat_url == "http://localhost:11434/api/generate"


def test_chat_url_strips_trailing_slash(tmp_path: Path) -> None:
    source = tmp_path / "runner.yaml"
    source.write_text(
        """
ollama:
  base_url: "http://example.local:11434/"
""",
        encoding="utf-8",
    )
    config = load_config(source)
    assert config.chat_url == "http://example.local:11434/api/generate"


def test_geos_config_has_no_model_field() -> None:
    """CORRECTED during the V3 port: model/fallback_model must never live on GeosConfig again --
    which model runs is a Gateway/registry concern, not this harness's config. This test exists
    to catch a regression if someone re-adds the field."""
    field_names = {f.name for f in dataclasses.fields(GeosConfig)}
    assert "model" not in field_names
    assert "fallback_model" not in field_names
    # [removed 2026-08-12] prompts_version was a repo-wide config value recording
    # ONE version for four prompts that version independently. It was recorded into
    # every response log while implementation.md declared a different number, and
    # once run_task started reading the prompt's own version it became dead config
    # still asserting "v1". A value nothing reads cannot be wrong quietly enough.
    assert "prompts_version" not in field_names
    assert field_names == {
        "base_url",
        "request_timeout_seconds",
        "max_context_tokens",
        # [added 2026-08-18] A CAPACITY FIGURE, NOT A MODEL IDENTITY, which is the distinction
        # this test actually protects. ~16384 is where the MODEL runs out of input room (a 32768
        # window with 16384 reserved for output); it says nothing about WHICH model runs, which
        # stays a Gateway/registry concern. It is deliberately NOT named `model_*`: the first
        # draft was, and reading it back it invited exactly the confusion this test guards.
        #
        # It exists because the over-budget warning was miscalibrated twice in one day -- first
        # claiming truncation at 12000 when real headroom is 16384, then, after that correction,
        # reassuring "nothing has been truncated" on a P-D30-06 run that assembled 23481 tokens
        # and made qwen3.6:27b fail all three iterations. Two different claims need two
        # thresholds, and a threshold asserted in a log string cannot be one of them.
        "input_headroom_tokens",
        "gaiep_provenance_enabled",
        "gaiep_provenance_fail_closed",
    }

    config = load_config()
    assert not hasattr(config, "model")
    assert not hasattr(config, "fallback_model")


def test_geos_config_is_frozen() -> None:
    config = load_config()
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.base_url = "http://elsewhere:11434"  # type: ignore[misc]


def test_missing_config_file_raises_config_error(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.yaml"
    with pytest.raises(ConfigError, match="Runner config not found"):
        load_config(missing)


def test_missing_ollama_section_raises_config_error(tmp_path: Path) -> None:
    source = tmp_path / "runner.yaml"
    source.write_text("context_builder:\n  max_context_tokens: 1000\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="missing required key 'ollama'"):
        load_config(source)


def test_missing_base_url_raises_config_error(tmp_path: Path) -> None:
    source = tmp_path / "runner.yaml"
    source.write_text("ollama:\n  request_timeout_seconds: 30\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="missing required key 'base_url'"):
        load_config(source)


def test_non_mapping_top_level_raises_config_error(tmp_path: Path) -> None:
    source = tmp_path / "runner.yaml"
    source.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="top level must be a YAML mapping"):
        load_config(source)


def test_load_config_reads_gaiep_provenance_flags(tmp_path: Path) -> None:
    source = tmp_path / "runner.yaml"
    source.write_text(
        """
ollama:
  base_url: "http://localhost:9999"
gaiep_provenance:
  enabled: true
  fail_closed: false
""",
        encoding="utf-8",
    )

    config = load_config(source)

    assert config.gaiep_provenance_enabled is True
    assert config.gaiep_provenance_fail_closed is False


def test_non_mapping_gaiep_provenance_section_raises_config_error(tmp_path: Path) -> None:
    source = tmp_path / "runner.yaml"
    source.write_text(
        'ollama:\n  base_url: "http://localhost:9999"\ngaiep_provenance:\n  - bad\n',
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="'gaiep_provenance' section must be a mapping"):
        load_config(source)


def test_optional_sections_fall_back_to_defaults(tmp_path: Path) -> None:
    """context_builder/prompts are optional -- only 'ollama.base_url' is truly required."""
    source = tmp_path / "runner.yaml"
    source.write_text('ollama:\n  base_url: "http://localhost:9999"\n', encoding="utf-8")
    config = load_config(source)

    assert config.base_url == "http://localhost:9999"
    assert config.request_timeout_seconds == 120  # default
    assert config.max_context_tokens == 12000  # default
