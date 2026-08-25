from dataclasses import FrozenInstanceError

import pytest

from self_improvement.evaluation import EvaluationResult
from self_improvement.provenance import (
    AuthorizationProvenance,
    ContextProvenance,
    RunProvenance,
)
from self_improvement.rollout import RolloutResult
from self_improvement.trajectory import TrajectoryRecord


def _provenance() -> RunProvenance:
    return RunProvenance(
        run_id="run-1",
        context=ContextProvenance(manifest_id="ctx-1", context_hash="hash-ctx"),
        skill_fingerprints=("skill-fp-1",),
        authorization=(
            AuthorizationProvenance(
                decision_ref="authz-1",
                decision="ALLOW",
                reason="authorized",
                capability_id="market.get_quote",
                capability_version="v1",
                policy_version="policy-v1",
            ),
        ),
        observation_refs=("obs-1",),
        artifact_refs=("artifact://candidate/1",),
        evidence_refs=("evidence://runtime/1",),
        gateway_model="small-python-coder",
        gateway_endpoint_model="qwen-local",
        capability_ids_requested=("market.get_quote",),
        capability_ids_authorized=("market.get_quote",),
        policy_decision_refs=("authz-1",),
        started_at_ref="event:start",
        finished_at_ref="event:finish",
    )


def test_run_provenance_is_immutable_reference_only_and_roundtrips() -> None:
    provenance = _provenance()

    with pytest.raises(FrozenInstanceError):
        provenance.run_id = "changed"  # type: ignore[misc]

    payload = provenance.to_json()
    assert "hash-ctx" in payload
    assert "raw context" not in payload
    assert "candidate source" not in payload
    assert RunProvenance.from_dict(provenance.to_dict()) == provenance


def test_rollout_provenance_survives_evaluation_to_trajectory() -> None:
    provenance = _provenance()
    rollout = RolloutResult(
        task_id="task-1",
        artifact=type("Artifact", (), {"files": {"a.py": "secret source"}})(),
        model_name="small-python-coder",
        scaffold_name="inspect-plan-implement-test",
        provenance=provenance,
    )
    evaluation = EvaluationResult(
        task_id="task-1",
        passed=True,
        reward=1.0,
        checks={"pytest": True},
    )

    record = TrajectoryRecord.from_results(rollout, evaluation)

    assert record.provenance == provenance
    assert record.provenance is not None
    assert record.provenance.context is not None
    assert record.provenance.context.context_hash == "hash-ctx"
    assert record.provenance.skill_fingerprints == ("skill-fp-1",)
    assert record.provenance.authorization[0].decision == "ALLOW"
    assert record.provenance.observation_refs == ("obs-1",)
    assert record.provenance.evidence_refs == ("evidence://runtime/1",)
    assert "secret source" not in record.to_json()
    assert TrajectoryRecord.from_json(record.to_json()) == record


def test_denied_authorization_is_recorded_but_cannot_become_execution_observation() -> None:
    denied = AuthorizationProvenance(
        decision_ref="authz-denied",
        decision="DENY",
        reason="skill_denied",
        capability_id="market.get_quote",
        capability_version="v1",
        policy_version="policy-v1",
    )

    provenance = RunProvenance(
        run_id="run-denied",
        authorization=(denied,),
        capability_ids_requested=("market.get_quote",),
        capability_ids_authorized=(),
        policy_decision_refs=("authz-denied",),
        evidence_refs=("evidence://denial/1",),
    )

    assert provenance.authorization[0].decision == "DENY"
    assert provenance.observation_refs == ()
    with pytest.raises(ValueError, match="denied authorization"):
        RunProvenance(
            run_id="run-invalid",
            authorization=(denied,),
            capability_ids_requested=("market.get_quote",),
            observation_refs=("obs-should-not-exist",),
        )


def test_authorized_capabilities_must_be_requested_first() -> None:
    with pytest.raises(ValueError, match="requested first"):
        RunProvenance(
            run_id="run-invalid",
            capability_ids_requested=(),
            capability_ids_authorized=("market.get_quote",),
        )
