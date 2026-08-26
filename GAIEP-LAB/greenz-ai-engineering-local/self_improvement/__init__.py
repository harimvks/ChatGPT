"""GAIEP self-improvement research primitives.

This package is deliberately research-only. It does not mutate production
models, routing policy, repositories, or certification state.
"""

from .corpus_adapter import CertificationRecord, certification_to_task, load_certifications, parse_certification
from .evaluation import EvaluationResult, EvaluationRunner
from .evidence_store import EvidenceRecord, GreenMemoryStore, IntegrityReport, MemorySummary
from .failure_miner import EvidenceFailureCluster, FailureCluster, FailureMiner
from .fingerprint import failure_fingerprint, provenance_fingerprint
from .gate_adapter import ExternalValidationGate, GateCommand, GateResult
from .gateway_rollout import GatewayResearchRollout, GatewayRolloutRequest
from .loop import ResearchRun, SelfImprovementLoop
from .provenance import AuthorizationProvenance, ContextProvenance, RunProvenance
from .rollout import ResearchRolloutRunner, RolloutResult
from .runtime_provenance import provenance_from_mcp_result
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
    "EvidenceRecord",
    "GreenMemoryStore",
    "IntegrityReport",
    "MemorySummary",
    "failure_fingerprint",
    "provenance_fingerprint",
    "FailureCluster",
    "EvidenceFailureCluster",
    "FailureMiner",
    "ExternalValidationGate",
    "GateCommand",
    "GateResult",
    "GatewayResearchRollout",
    "GatewayRolloutRequest",
    "AuthorizationProvenance",
    "ContextProvenance",
    "ResearchRun",
    "RunProvenance",
    "provenance_from_mcp_result",
    "SelfImprovementLoop",
    "ResearchRolloutRunner",
    "RolloutResult",
    "CandidateSandbox",
    "SandboxWorkspace",
    "SandboxEvaluation",
    "SandboxEvaluator",
]
