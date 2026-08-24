from pathlib import Path

from self_improvement.evaluation import EvaluationResult
from self_improvement.experiment import ExperimentArm, ExperimentPlan
from self_improvement.pilot_manifest import PilotManifest
from self_improvement.pilot_runner import PilotRunner
from self_improvement.rollout import ResearchRolloutRunner
from self_improvement.task_factory import TaskFactory
from self_improvement.trajectory_store import TrajectoryStore


def test_pilot_runner_executes_all_cells_and_records_results(tmp_path: Path):
    task = TaskFactory().from_seed(task_type="implementation", title="T", objective="Implement X")
    plan = ExperimentPlan(
        name="pilot",
        task_ids=(task.task_id, "missing"),
        arms=(ExperimentArm("m1", "s1"),),
    )
    manifest = PilotManifest(
        experiment_id=plan.name,
        corpus_version="v1",
        task_ids=(task.task_id,),
        arms=plan.arms,
        validation_profile="test",
    )

    runner = PilotRunner(
        lambda arm: ResearchRolloutRunner(
            lambda _task: {"files": {"x.py": "x = 1\n"}},
            model_name=arm.model_name,
            scaffold_name=arm.scaffold_name,
        ),
        lambda task, _artifact: EvaluationResult(
            task_id=task.task_id,
            passed=True,
            reward=1.0,
            checks={"pytest": True},
        ),
        TrajectoryStore(tmp_path / "trajectory.jsonl"),
    )
    results = runner.run(manifest, [task])
    assert len(results) == 1
    assert results[0].trajectory.passed
    assert (tmp_path / "trajectory.jsonl").read_text().count("task_id") == 1
