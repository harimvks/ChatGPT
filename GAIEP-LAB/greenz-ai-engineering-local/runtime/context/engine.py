"""Deterministic ContextEngine assembly for Runtime VNext."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from runtime.context.contracts import (
    CompressionRecord,
    CompressionStrategy,
    ContextBudget,
    ContextItem,
    ContextManifest,
    ContextProfile,
    ContextValidationError,
)


@dataclass(frozen=True)
class ContextBuildRequest:
    run_id: str
    manifest_id: str
    profile: ContextProfile
    budget: ContextBudget
    items: tuple[ContextItem, ...]
    created_at: datetime


class DeterministicContextEngine:
    """Select, budget, compact, and manifest context without execution authority."""

    schema_version = "context-manifest-v1"

    def build(self, request: ContextBuildRequest) -> ContextManifest:
        allowed = tuple(
            item for item in request.items if item.kind in request.profile.allowed_kinds
        )
        mandatory = tuple(item for item in allowed if item.mandatory)
        optional = tuple(sorted(
            (item for item in allowed if not item.mandatory),
            key=lambda item: (item.selection_reason.value, item.item_id),
        ))
        if len(mandatory) > request.profile.max_items:
            raise ContextValidationError("mandatory context exceeds profile max_items")
        available_optional_slots = request.profile.max_items - len(mandatory)
        selected_optional: list[ContextItem] = []
        optional_tokens = 0
        available_tokens = (
            request.budget.available_input_tokens
            - sum(item.token_estimate for item in mandatory)
        )
        for item in optional:
            if len(selected_optional) >= available_optional_slots:
                break
            if optional_tokens + item.token_estimate <= available_tokens:
                selected_optional.append(item)
                optional_tokens += item.token_estimate
        selected = tuple(sorted((*mandatory, *selected_optional), key=lambda item: item.item_id))
        budget = ContextBudget(
            input_token_limit=request.budget.input_token_limit,
            output_token_reserve=request.budget.output_token_reserve,
            mandatory_token_estimate=sum(item.token_estimate for item in mandatory),
            optional_token_estimate=optional_tokens,
        )
        return ContextManifest(
            manifest_id=request.manifest_id,
            run_id=request.run_id,
            schema_version=self.schema_version,
            profile_id=request.profile.profile_id,
            selected_items=selected,
            compression_records=(),
            budget=budget,
            created_at=request.created_at,
            input_token_actual=budget.total_token_estimate,
        )

    def compact_optional(
        self, *, item: ContextItem, after_tokens: int, content_hash_after: str
    ) -> CompressionRecord:
        if item.mandatory:
            raise ContextValidationError("mandatory context cannot be compacted by policy")
        return CompressionRecord(
            record_id=f"cmp:{item.item_id}",
            item_id=item.item_id,
            strategy=CompressionStrategy.SUMMARIZE_DETERMINISTIC,
            before_tokens=item.token_estimate,
            after_tokens=after_tokens,
            content_hash_before=item.content_hash,
            content_hash_after=content_hash_after,
        )
