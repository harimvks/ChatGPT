"""Pure Context Engine contracts for GAIEP Runtime VNext.

These immutable types define the SELECT/BUDGET/COMPRESS/MANIFEST vocabulary.
They intentionally perform no filesystem reads, Gateway calls, retrieval, or legacy
builder adaptation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any


class ContextValidationError(ValueError):
    """Raised when a Context Engine contract invariant is violated."""


class ContextItemKind(StrEnum):
    INSTRUCTION = "instruction"
    PROJECT_INSTRUCTION = "project_instruction"
    TASK = "task"
    SOURCE = "source"
    TOOL_SCHEMA = "tool_schema"
    SKILL = "skill"
    MEMORY = "memory"
    PRIOR_OUTPUT = "prior_output"


class SelectionReason(StrEnum):
    MANDATORY = "mandatory"
    EXPLICIT_REFERENCE = "explicit_reference"
    LEGACY_BASELINE = "legacy_baseline"
    SUPPORTING_CONTEXT = "supporting_context"


class CompressionStrategy(StrEnum):
    NONE = "none"
    TRUNCATE_OPTIONAL = "truncate_optional"
    SUMMARIZE_DETERMINISTIC = "summarize_deterministic"


def _require_non_empty(label: str, value: str) -> None:
    if not value.strip():
        raise ContextValidationError(f"{label} cannot be empty")


def _require_utc(label: str, value: datetime) -> None:
    if value.utcoffset() != timedelta(0):
        raise ContextValidationError(f"{label} must be timezone-aware UTC")


def _dedupe_sorted(values: tuple[str, ...], *, label: str) -> tuple[str, ...]:
    cleaned = tuple(str(value).strip() for value in values if str(value).strip())
    if len(set(cleaned)) != len(cleaned):
        raise ContextValidationError(f"{label} cannot contain duplicates")
    return tuple(sorted(cleaned))


def _normalize_ref(value: str, *, label: str) -> str:
    _require_non_empty(label, value)
    normalized = str(PurePosixPath(value.replace("\\", "/")))
    if normalized in {".", ""} or normalized.startswith("../") or "/../" in normalized:
        raise ContextValidationError(f"{label} escapes the context envelope: {value!r}")
    return normalized.lstrip("/")


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _hash_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ContextItem:
    item_id: str
    kind: ContextItemKind
    source_ref: str
    token_estimate: int
    mandatory: bool
    selection_reason: SelectionReason
    content_hash: str
    redaction_checked: bool = False

    def __post_init__(self) -> None:
        _require_non_empty("ContextItem.item_id", self.item_id)
        object.__setattr__(
            self, "source_ref", _normalize_ref(self.source_ref, label="ContextItem.source_ref")
        )
        if self.token_estimate < 0:
            raise ContextValidationError("ContextItem.token_estimate cannot be negative")
        _require_non_empty("ContextItem.content_hash", self.content_hash)

    def canonical(self) -> dict[str, Any]:
        return {
            "content_hash": self.content_hash,
            "item_id": self.item_id,
            "kind": self.kind.value,
            "mandatory": self.mandatory,
            "redaction_checked": self.redaction_checked,
            "selection_reason": self.selection_reason.value,
            "source_ref": self.source_ref,
            "token_estimate": self.token_estimate,
        }


@dataclass(frozen=True)
class ContextBudget:
    input_token_limit: int
    output_token_reserve: int
    mandatory_token_estimate: int = 0
    optional_token_estimate: int = 0

    def __post_init__(self) -> None:
        values = (
            self.input_token_limit,
            self.output_token_reserve,
            self.mandatory_token_estimate,
            self.optional_token_estimate,
        )
        if any(value < 0 for value in values):
            raise ContextValidationError("ContextBudget token values cannot be negative")
        if self.output_token_reserve > self.input_token_limit:
            raise ContextValidationError("output reserve cannot exceed input token limit")
        if self.mandatory_token_estimate > self.available_input_tokens:
            raise ContextValidationError("mandatory context exceeds available input budget")

    @property
    def available_input_tokens(self) -> int:
        return self.input_token_limit - self.output_token_reserve

    @property
    def total_token_estimate(self) -> int:
        return self.mandatory_token_estimate + self.optional_token_estimate


@dataclass(frozen=True)
class CompressionRecord:
    record_id: str
    item_id: str
    strategy: CompressionStrategy
    before_tokens: int
    after_tokens: int
    content_hash_before: str
    content_hash_after: str

    def __post_init__(self) -> None:
        _require_non_empty("CompressionRecord.record_id", self.record_id)
        _require_non_empty("CompressionRecord.item_id", self.item_id)
        if self.before_tokens < 0 or self.after_tokens < 0:
            raise ContextValidationError("compression token values cannot be negative")
        if self.after_tokens > self.before_tokens:
            raise ContextValidationError("compression cannot increase token estimate")
        _require_non_empty("CompressionRecord.content_hash_before", self.content_hash_before)
        _require_non_empty("CompressionRecord.content_hash_after", self.content_hash_after)

    def canonical(self) -> dict[str, Any]:
        return {
            "after_tokens": self.after_tokens,
            "before_tokens": self.before_tokens,
            "content_hash_after": self.content_hash_after,
            "content_hash_before": self.content_hash_before,
            "item_id": self.item_id,
            "record_id": self.record_id,
            "strategy": self.strategy.value,
        }


@dataclass(frozen=True)
class ContextProfile:
    profile_id: str
    engine_version: str
    allowed_kinds: tuple[ContextItemKind, ...]
    max_items: int
    compression_allowed: bool = False

    def __post_init__(self) -> None:
        _require_non_empty("ContextProfile.profile_id", self.profile_id)
        _require_non_empty("ContextProfile.engine_version", self.engine_version)
        if not self.allowed_kinds:
            raise ContextValidationError("ContextProfile.allowed_kinds cannot be empty")
        if len(set(self.allowed_kinds)) != len(self.allowed_kinds):
            raise ContextValidationError("ContextProfile.allowed_kinds cannot contain duplicates")
        if self.max_items <= 0:
            raise ContextValidationError("ContextProfile.max_items must be positive")


@dataclass(frozen=True)
class ContextManifest:
    manifest_id: str
    run_id: str
    schema_version: str
    profile_id: str
    selected_items: tuple[ContextItem, ...]
    compression_records: tuple[CompressionRecord, ...]
    budget: ContextBudget
    created_at: datetime
    context_hash: str | None = None
    input_token_actual: int | None = None

    def __post_init__(self) -> None:
        _require_non_empty("ContextManifest.manifest_id", self.manifest_id)
        _require_non_empty("ContextManifest.run_id", self.run_id)
        _require_non_empty("ContextManifest.schema_version", self.schema_version)
        _require_non_empty("ContextManifest.profile_id", self.profile_id)
        _require_utc("ContextManifest.created_at", self.created_at)
        item_ids = tuple(item.item_id for item in self.selected_items)
        if len(set(item_ids)) != len(item_ids):
            raise ContextValidationError(
                "ContextManifest selected item IDs cannot contain duplicates"
            )
        compression_item_ids = {record.item_id for record in self.compression_records}
        if not compression_item_ids.issubset(item_ids):
            raise ContextValidationError("compression records must refer to selected context items")
        if self.input_token_actual is not None and self.input_token_actual < 0:
            raise ContextValidationError("ContextManifest.input_token_actual cannot be negative")
        computed_hash = self.compute_hash()
        if self.context_hash is None:
            object.__setattr__(self, "context_hash", computed_hash)
        elif self.context_hash != computed_hash:
            raise ContextValidationError("ContextManifest.context_hash is not canonical")

    def canonical(self) -> dict[str, Any]:
        return {
            "budget": {
                "input_token_limit": self.budget.input_token_limit,
                "mandatory_token_estimate": self.budget.mandatory_token_estimate,
                "optional_token_estimate": self.budget.optional_token_estimate,
                "output_token_reserve": self.budget.output_token_reserve,
            },
            "compression_records": [
                record.canonical()
                for record in sorted(
                    self.compression_records, key=lambda rec: rec.record_id
                )
            ],
            "created_at": self.created_at.isoformat(),
            "input_token_actual": self.input_token_actual,
            "manifest_id": self.manifest_id,
            "profile_id": self.profile_id,
            "run_id": self.run_id,
            "schema_version": self.schema_version,
            "selected_items": [
                item.canonical()
                for item in sorted(self.selected_items, key=lambda item: item.item_id)
            ],
        }

    def compute_hash(self) -> str:
        return _hash_payload(self.canonical())

    @property
    def source_refs(self) -> tuple[str, ...]:
        return _dedupe_sorted(
            tuple(item.source_ref for item in self.selected_items), label="source_refs"
        )
