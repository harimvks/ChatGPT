"""GAIEP self-improvement research primitives.

This package is deliberately research-only. It does not mutate production
models, routing policy, repositories, or certification state.
"""

from .task_factory import EngineeringTask, TaskFactory
from .evaluation import EvaluationResult, EvaluationRunner
from .failure_miner import FailureMiner

__all__ = [
    "EngineeringTask",
    "TaskFactory",
    "EvaluationResult",
    "EvaluationRunner",
    "FailureMiner",
]
