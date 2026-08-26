from pathlib import Path

from self_improvement.artifact import CandidateArtifact
from self_improvement.evaluation import EvaluationResult
from self_improvement.evidence_store import GreenMemoryStore
from self_improvement.experiment import ExperimentArm, ExperimentPlan
from self_improvement.experiment_runner import ExperimentRunner
from self_improvement.provenance import RunProvenance
from self_improvement.rollout import ResearchRolloutRunner, RolloutResult
from self_improvement.task_factory import TaskFactory


def _runner(evidence_store=None):
    task = TaskFactory().from_seed(task_type="implementation", title="T", objective="Implement X")
    plan = ExperimentPlan(
        name="test",
        task_ids=(task.task_id,),
        arms=(ExperimentArm("m1", "s1"), ExperimentArm("m2", "s2")),
    )

    def rollout_factory(arm):
        return ResearchRolloutRunner(
            lambda _task: CandidateArtifact({"x.py": "x = 1\n"}),
            model_name=arm.model_name,
            scaffold_name=arm.scaffold_name,
        )

    def evaluate(_task, _artifact):
        return EvaluationResult(
            task_id=task.task_id,
            passed=True,
            reward=1.0,
            checks={"pytest": True},
        )

    return ExperimentRunner(rollout_factory, evaluate, evidence_store), plan, task


def test_runner_executes_every_task_arm_pair():
    runner, plan, task = _runner()

    trials = runner.run(plan, [task])

    assert len(trials) == 2
    assert {(t.arm.model_name, t.arm.scaffold_name) for t in trials} == {
        ("m1", "s1"),
        ("m2", "s2"),
    }


def test_runner_persists_each_completed_trial(tmp_path: Path):
    store = GreenMemoryStore(tmp_path / "greenmemory.sqlite3")
    runner, plan, task = _runner(store)

    trials = runner.run(plan, [task])

    assert len(trials) == 2
    assert store.count() == 2
    assert len(store.find_by_task(task.task_id)) == 2


def test_runner_persists_provenance_from_normalized_rollout(tmp_path: Path):
    task = TaskFactory().from_seed(task_type="implementation", title="T", objective="Implement X")
    provenance = RunProvenance(
        run_id="run-real-1",
        capability_ids_requested=("market.get_quote",),
        capability_ids_authorized=("market.get_quote",),
        observation_refs=("obs-real-1",),
        evidence_refs=("evidence://real/1",),
    )
    store = GreenMemoryStore(tmp_path / "greenmemory.sqlite3")
    plan = ExperimentPlan(
        name="test",
        task_ids=(task.task_id,),
        arms=(ExperimentArm("m1", "s1"),),
    )

    class ProvenanceRolloutRunner:
        def run(self, _task):
            return RolloutResult(
                task_id=task.task_id,
                artifact={"files": {"x.py": "x = 1\n"}},
                model_name="m1",
                scaffold_name="s1",
                endpoint_model="endpoint-m1",
                latency_s=0.5,
                usage={"tokens": 12},
                provenance=provenance,
            )

    runner = ExperimentRunner(
        lambda _arm: ProvenanceRolloutRunner(),
        lambda _task, _artifact: EvaluationResult(
            task_id=task.task_id,
            passed=True,
            reward=1.0,
            checks={"pytest": True},
        ),
        store,
    )

    trials = runner.run(plan, [task])

    trajectory = trials[0].trajectory
    restored = store.find_by_run("run-real-1")[0]
    assert trajectory.provenance == provenance
    assert trajectory.endpoint_model == "endpoint-m1"
    assert trajectory.latency_s == 0.5
    assert trajectory.usage == {"tokens": 12}
    assert restored.provenance == provenance
    assert restored.artifact_files == ("x.py",)
    assert "x = 1" not in restored.to_json()
