"""Phase-1 tests for GAIEP Context Engine contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from runtime.context.contracts import (
    CompressionRecord,
    CompressionStrategy,
    ContextBudget,
    ContextItem,
    ContextItemKind,
    ContextManifest,
    ContextProfile,
    ContextValidationError,
    SelectionReason,
)

_NOW = datetime(2026, 8, 24, 10, 0, tzinfo=UTC)


def _item(item_id: str = "ctx-1", *, mandatory: bool = True) -> ContextItem:
    return ContextItem(
        item_id=item_id,
        kind=ContextItemKind.SOURCE,
        source_ref=f"src/{item_id}.py",
        token_estimate=12,
        mandatory=mandatory,
        selection_reason=SelectionReason.MANDATORY
        if mandatory
        else SelectionReason.SUPPORTING_CONTEXT,
        content_hash=f"hash-{item_id}",
        redaction_checked=True,
    )


def test_context_item_is_immutable_and_rejects_unsafe_refs() -> None:
    item = _item()

    with pytest.raises(FrozenInstanceError):
        item.source_ref = "src/changed.py"  # type: ignore[misc]

    with pytest.raises(ContextValidationError, match="escapes"):
        ContextItem(
            item_id="ctx-bad",
            kind=ContextItemKind.SOURCE,
            source_ref="../secrets.env",
            token_estimate=1,
            mandatory=True,
            selection_reason=SelectionReason.MANDATORY,
            content_hash="hash",
        )


def test_context_budget_preserves_output_reserve_and_rejects_overflow() -> None:
    budget = ContextBudget(
        input_token_limit=100,
        output_token_reserve=25,
        mandatory_token_estimate=50,
        optional_token_estimate=20,
    )

    assert budget.available_input_tokens == 75
    assert budget.total_token_estimate == 70

    with pytest.raises(ContextValidationError, match="mandatory context"):
        ContextBudget(input_token_limit=10, output_token_reserve=5, mandatory_token_estimate=6)

    with pytest.raises(ContextValidationError, match="negative"):
        ContextBudget(input_token_limit=-1, output_token_reserve=0)


def test_compression_record_is_loss_accounting_not_budget_expansion() -> None:
    record = CompressionRecord(
        record_id="cmp-1",
        item_id="ctx-1",
        strategy=CompressionStrategy.TRUNCATE_OPTIONAL,
        before_tokens=50,
        after_tokens=20,
        content_hash_before="before",
        content_hash_after="after",
    )

    assert record.canonical()["strategy"] == "truncate_optional"

    with pytest.raises(ContextValidationError, match="increase"):
        CompressionRecord(
            record_id="cmp-2",
            item_id="ctx-1",
            strategy=CompressionStrategy.SUMMARIZE_DETERMINISTIC,
            before_tokens=20,
            after_tokens=21,
            content_hash_before="before",
            content_hash_after="after",
        )


def test_context_profile_rejects_duplicate_kinds_and_empty_profiles() -> None:
    profile = ContextProfile(
        profile_id="implementation",
        engine_version="context-v1",
        allowed_kinds=(ContextItemKind.SOURCE, ContextItemKind.TASK),
        max_items=5,
    )

    assert profile.max_items == 5

    with pytest.raises(ContextValidationError, match="duplicates"):
        ContextProfile(
            profile_id="bad",
            engine_version="context-v1",
            allowed_kinds=(ContextItemKind.SOURCE, ContextItemKind.SOURCE),
            max_items=5,
        )


def test_context_manifest_hash_is_deterministic_and_canonical() -> None:
    item_a = _item("a")
    item_b = _item("b", mandatory=False)
    budget = ContextBudget(
        input_token_limit=200,
        output_token_reserve=50,
        mandatory_token_estimate=12,
        optional_token_estimate=12,
    )

    manifest_a = ContextManifest(
        manifest_id="manifest-1",
        run_id="run-1",
        schema_version="context-manifest-v1",
        profile_id="implementation",
        selected_items=(item_b, item_a),
        compression_records=(),
        budget=budget,
        created_at=_NOW,
    )
    manifest_b = ContextManifest(
        manifest_id="manifest-1",
        run_id="run-1",
        schema_version="context-manifest-v1",
        profile_id="implementation",
        selected_items=(item_a, item_b),
        compression_records=(),
        budget=budget,
        created_at=_NOW,
    )

    assert manifest_a.context_hash == manifest_b.context_hash
    assert manifest_a.source_refs == ("src/a.py", "src/b.py")

    with pytest.raises(ContextValidationError, match="canonical"):
        ContextManifest(
            manifest_id="manifest-1",
            run_id="run-1",
            schema_version="context-manifest-v1",
            profile_id="implementation",
            selected_items=(item_a,),
            compression_records=(),
            budget=budget,
            created_at=_NOW,
            context_hash="wrong",
        )


def test_context_manifest_rejects_naive_timestamps_and_unknown_compression_items() -> None:
    item = _item()
    budget = ContextBudget(
        input_token_limit=100,
        output_token_reserve=20,
        mandatory_token_estimate=12,
    )
    compression = CompressionRecord(
        record_id="cmp-1",
        item_id="missing",
        strategy=CompressionStrategy.TRUNCATE_OPTIONAL,
        before_tokens=10,
        after_tokens=5,
        content_hash_before="before",
        content_hash_after="after",
    )

    with pytest.raises(ContextValidationError, match="timezone-aware UTC"):
        ContextManifest(
            manifest_id="manifest-1",
            run_id="run-1",
            schema_version="context-manifest-v1",
            profile_id="implementation",
            selected_items=(item,),
            compression_records=(),
            budget=budget,
            created_at=datetime(2026, 8, 24, 10, 0),
        )

    with pytest.raises(ContextValidationError, match="selected context"):
        ContextManifest(
            manifest_id="manifest-1",
            run_id="run-1",
            schema_version="context-manifest-v1",
            profile_id="implementation",
            selected_items=(item,),
            compression_records=(compression,),
            budget=budget,
            created_at=_NOW,
        )
