from datetime import UTC, datetime
from pathlib import Path

from self_improvement.controlled_pilot import (
    build_controlled_pilot,
    fixture_evaluator,
    fixture_rollout_factory,
)
from self_improvement.evidence_store import GreenMemoryStore
from self_improvement.experiment_runner import ExperimentRunner
from self_improvement.provenance import RunProvenance
from self_improvement.research_loop import FailureResearchLoop, ResearchSubmissionAdapter
from self_improvement.research_outcome import ResearchOutcome, assess_intervention
from self_improvement.rollout import RolloutResult
from self_improvement.task_factory import EngineeringTask

_NOW = datetime(2026, 8, 26, 17, 30, tzinfo=UTC)


def test_controlled_pilot_is_12_trials_and_drives_one_research_cycle(tmp_path: Path) -> None:
    spec = build_controlled_pilot()
    assert len(spec.tasks) == 3
    assert spec.plan.matrix_size() == 12

    first_task_id = spec.tasks[0].task_id

    def failure_selector(task: EngineeringTask, arm) -> bool:
        return task.task_id == first_task_id and arm.model_name == "small-python-coder"

    memory = GreenMemoryStore(tmp_path / "greenmemory.sqlite3")
    runner = ExperimentRunner(
        fixture_rollout_factory(failure_selector=failure_selector),
        fixture_evaluator,
        memory,
    )
    trials = runner.run(spec.plan, spec.tasks)

    assert len(trials) == 12
    assert memory.count() == 12
    assert sum(not trial.trajectory.passed for trial in trials) == 2
    assert len(FailureResearchLoop(memory).discover()) == 1

    proposals = FailureResearchLoop(memory).propose(spec.tasks)
    assert len(proposals) == 1
    proposal = proposals[0]
    source = memory.find_by_failure_fingerprint(proposal.hypothesis.failure_fingerprint)
    assert len(source) == 2
    assert all(not record.passed for record in source)

    def corrected_factory(arm):
        class CorrectedRunner:
            def run(self, task):
                return RolloutResult(
                    task_id=task.task_id,
                    artifact={"files": {"candidate.py": "# corrected\nvalue = 1\n"}},
                    model_name=arm.model_name,
                    scaffold_name=arm.scaffold_name,
                    provenance=RunProvenance(run_id="controlled-follow-up-001"),
                )

        return CorrectedRunner()

    corrected_runner = ExperimentRunner(corrected_factory, fixture_evaluator, memory)
    submission = ResearchSubmissionAdapter(memory).submit(
        proposal,
        approved_by="controlled-research-review",
        runner=corrected_runner,
        arm=spec.plan.arms[0],
        experiment_run_id="controlled-follow-up-001",
        submitted_at=_NOW,
    )

    assert submission.result_evidence_ids
    follow_up_records = [
        record
        for record_id in submission.result_evidence_ids
        if (record := memory.get(record_id)) is not None
    ]
    assessment = assess_intervention(source, follow_up_records)
    assert assessment.outcome is ResearchOutcome.IMPROVED
    assert memory.count() == 13

    restarted = GreenMemoryStore(memory.path)
    lineage = restarted.find_research_lineage_by_hypothesis(proposal.hypothesis.hypothesis_id)
    assert [event.status for event in lineage] == [
        "PROPOSED",
        "APPROVED",
        "SUBMITTED",
        "COMPLETED",
    ]
