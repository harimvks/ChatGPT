# GAIEP Runtime VNext Lab Status

This lab implementation follows the Hermes/OpenHands baseline as GreenZ-native contracts, not as a clone of either project.

## Implemented

- AgentRun identity and lifecycle transition validation.
- Typed Action/Observation contracts.
- Runtime event history with ActionRequested, AuthorizationEvaluated, ActionDenied, ActionExecuted, ActionFailed, and ObservationProduced.
- Capability and CapabilityRegistry contracts.
- Deterministic authorization with default-deny capability checks.
- Policy authorization intersection across capability, task policy, skill manifest, workspace scope, global policy, and budget.
- WorkspaceScope path boundary and traversal rejection.
- RuntimeBudget action/token/child allocation constraints.
- Minimal LocalRuntime proving denied actions never execute and failures produce ActionFailed events.
- Context Engine contracts for context items, budgets, compression records, manifests, hashes, and profiles.
- GreenSkills contracts for registry, applicability, immutable versioning, and certification evidence.
- GreenMemory contracts for candidate memory and governed durable promotion.
- Bounded subagent contracts enforcing child authority, tools, context, and budget subsets.

## Partial

- LocalRuntime is intentionally a testable shell. It does not provide a production filesystem, shell, SQL, network, broker, Docker, VPS, or remote execution backend.
- Context Engine is contract-level only. Full selection, sanitization, compression implementation, and legacy adapter migration remain future work.
- Skill and memory layers are contracts only; no marketplace, autonomous promotion, or durable store is implemented.

## Deferred

- MCP capability gateway.
- Docker/VPS/remote runtime.
- Autonomous subagents or swarms.
- Live trading or direct broker execution.
- Model routing changes. Model selection remains Gateway/ModelPolicy owned.
- A second artifact/provenance store. Events reference existing evidence/artifacts by ID or ref.

## Proven In Tests

- Invalid lifecycle transitions fail deterministically.
- Terminal runs cannot transition again.
- Authorization denies unknown capability, task policy mismatch, skill mismatch, workspace mismatch, global policy denial, and exhausted budgets.
- Child authority/tool/context/budget escalation is rejected.
- ActionExecuted cannot appear without prior ALLOW authorization.
- Large event payloads require an artifact reference.
- LocalRuntime does not call its executor for denied actions.
