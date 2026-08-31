from self_improvement.artifact import CandidateArtifact
from self_improvement.evaluation import EvaluationResult
from self_improvement.experiment import ExperimentArm, ExperimentPlan
from self_improvement.experiment_runner import ExperimentRunner
from self_improvement.rollout import ResearchRolloutRunner
from self_improvement.task_factory import TaskFactory


def test_runner_executes_every_task_arm_pair():
    task = TaskFactory().from_seed(
        task_type="implementation", title="T", objective="Implement X"
    )
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

    trials = ExperimentRunner(rollout_factory, evaluate).run(plan, [task])
    assert len(trials) == 2
    assert {(t.arm.model_name, t.arm.scaffold_name) for t in trials} == {
        ("m1", "s1"), ("m2", "s2")
    }
