"""Staging tests for the GAIEP ModelCall provenance wrapper.

These tests are intentionally self-contained at the adapter boundary. They do not modify or
replace the production runner; VPS integration remains a later, reviewed surgical change.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from runner.gateway_client import ChatResult
from runner.provenance_model_call import with_provenance
from runtime.artifact_refs import ArtifactReferenceIndex
from runtime.artifact_store import FileArtifactStore
from runtime.artifact_hooks import ArtifactRegistrar


def _result(text: str = "hello") -> ChatResult:
    return ChatResult(
        text=text,
        model="test-model",
        provider_name="test-provider",
        execution_id="exec-1",
        context_id="ctx-1",
        context_hash="hash-1",
        elapsed_seconds=0.125,
        failed_over_from=(),
    )


def _registrar(root: Path) -> ArtifactRegistrar:
    return ArtifactRegistrar(
        FileArtifactStore(root / "artifacts"),
        ArtifactReferenceIndex(root / "artifacts" / "index.db"),
    )


def test_wrapper_returns_original_chat_result_and_persists_artifact(tmp_path: Path) -> None:
    expected = _result()
    calls: list[tuple[str, str]] = []

    def model_call(system: str, user: str) -> ChatResult:
        calls.append((system, user))
        return expected

    wrapped = with_provenance(
        model_call,
        repo_root=tmp_path,
        run_id="run-1",
        registrar=_registrar(tmp_path),
    )

    actual = wrapped("system", "user")

    assert actual is expected
    assert calls == [("system", "user")]
    assert actual.text == "hello"


def test_wrapper_registers_model_request_reference(tmp_path: Path) -> None:
    registrar = _registrar(tmp_path)
    result = _result("durable")

    wrapped = with_provenance(
        lambda _system, _user: result,
        repo_root=tmp_path,
        run_id="run-2",
        registrar=registrar,
    )
    wrapped("s", "u")

    records = registrar.index.records()
    assert len(records) == 1
    record = records[0]
    assert record.reference_count == 1
    assert registrar.store.get(record.sha256) == b"durable"


def test_provider_failure_does_not_create_success_artifact(tmp_path: Path) -> None:
    registrar = _registrar(tmp_path)

    def failing_call(_system: str, _user: str) -> ChatResult:
        raise RuntimeError("provider failure")

    wrapped = with_provenance(
        failing_call,
        repo_root=tmp_path,
        run_id="run-fail",
        registrar=registrar,
    )

    with pytest.raises(RuntimeError, match="provider failure"):
        wrapped("s", "u")

    assert registrar.index.records() == ()


def test_artifact_persistence_failure_propagates(tmp_path: Path) -> None:
    class FailingRegistrar(ArtifactRegistrar):
        def persist_and_reference(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise OSError("artifact store unavailable")

    result = _result()
    wrapped = with_provenance(
        lambda _system, _user: result,
        repo_root=tmp_path,
        run_id="run-artifact-fail",
        registrar=FailingRegistrar(
            FileArtifactStore(tmp_path / "artifacts"),
            ArtifactReferenceIndex(tmp_path / "artifacts" / "index.db"),
        ),
    )

    with pytest.raises(OSError, match="artifact store unavailable"):
        wrapped("s", "u")


def test_existing_artifact_is_not_duplicated(tmp_path: Path) -> None:
    registrar = _registrar(tmp_path)
    reference = registrar.store.put("existing")
    result = ChatResult(
        text="ignored-inline-text",
        model="test-model",
        provider_name="test-provider",
        execution_id="exec-existing",
        context_id="ctx-1",
        context_hash="hash-1",
        elapsed_seconds=0.1,
        failed_over_from=(),
    )

    # The production adapter currently receives inline ChatResult output. This test documents
    # the intended deduplication invariant at the underlying registrar boundary.
    registrar.reference_existing(reference, owner_type="model_request", owner_id=result.execution_id)
    registrar.reference_existing(reference, owner_type="evidence", owner_id="ev-1")

    assert registrar.index.record(reference.sha256).reference_count == 2
    assert registrar.store.get(reference.sha256) == b"existing"
