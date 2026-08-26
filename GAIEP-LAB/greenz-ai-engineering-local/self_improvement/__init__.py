"""GAIEP self-improvement research primitives.

This package is deliberately research-only. It does not mutate production
models, routing policy, repositories, or certification state.
"""

from .corpus_adapter import CertificationRecord, certification_to_task, load_certifications, parse_certification
from .evaluation import EvaluationResult, EvaluationRunner
from .failure_miner import FailureMiner
from .gate_adapter import ExternalValidationGate, GateCommand, GateResult
from .gateway_rollout import GatewayResearchRollout, GatewayRolloutRequest
from .governed_agent_run import GovernedAgentRunResult, run_governed_agent_request
from .loop import ResearchRun, SelfImprovementLoop
from .rollout import ResearchRolloutRunner, RolloutResult
from .sandbox import CandidateSandbox, SandboxWorkspace
from .sandbox_evaluation import SandboxEvaluation, SandboxEvaluator
from .task_factory import EngineeringTask, TaskFactory

__all__ = [
    "CertificationRecord",
    "certification_to_task",
    "load_certifications",
    "parse_certification",
    "EngineeringTask",
    "TaskFactory",
    "EvaluationResult",
    "EvaluationRunner",
    "FailureMiner",
    "ExternalValidationGate",
    "GateCommand",
    "GateResult",
    "GatewayResearchRollout",
    "GatewayRolloutRequest",
    "GovernedAgentRunResult",
    "AuthorizationProvenance",
    "ContextProvenance",
    "ResearchRun",
    "RunProvenance",
    "provenance_from_mcp_result",
    "run_governed_agent_request",
    "SelfImprovementLoop",
    "ResearchRolloutRunner",
    "RolloutResult",
    "CandidateSandbox",
    "SandboxWorkspace",
    "SandboxEvaluation",
    "SandboxEvaluator",
]
