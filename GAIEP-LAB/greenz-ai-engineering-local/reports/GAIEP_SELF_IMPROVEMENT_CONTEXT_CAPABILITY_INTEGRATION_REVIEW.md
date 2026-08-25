# GAIEP Self-Improvement + Context/Capability Integration Review

## Verdict

**INTEGRATION REVIEW COMPLETE**

The current feature branch already descends from `gaiep/self-improvement-pilot-execution`, so the self-improvement work and the capability/MCP/context work are not divergent Git histories. The remaining issue is architectural integration: the self-improvement loop should consume Runtime VNext, ContextEngine, GreenSkills, Capability Registry, and Authorization as shared boundaries rather than becoming a parallel execution stack.

## Branches Reviewed

- Self-improvement line: `gaiep/self-improvement-pilot-execution`
- Current integration line: `codex/gaiep-capability-mcp-gateway`
- Current head during review: `f2d0b44 feat(gaiep): add context skills integration layer`

## Current Layer Ownership

| Layer | Current Owner | Integration Decision |
| --- | --- | --- |
| AgentRun lifecycle | `runtime.agent` | Shared platform contract. |
| Action/Observation events | `runtime.agent` | Shared platform contract. |
| Capability Registry | `runtime.agent` / `runtime.capabilities` | Shared platform contract. |
| MCP transport | `runtime.mcp` | Shared transport boundary, not authority. |
| Authorization | `runtime.agent.policy` | Sole execution authority. |
| ContextEngine | `runtime.context` | Shared request-shaping boundary. |
| GreenSkills | `runtime.skills` | Shared procedural/context layer; no authority grant. |
| Self-improvement loop | `self_improvement` | Research orchestration only. |
| Rollout/evaluation/trajectory | `self_improvement` | Consume shared runtime/context/capability evidence; do not own execution authority. |
| Failure mining | `self_improvement` | Generate candidate research tasks only. |

## Required Integration Shape

```text
EngineeringTask
    |
    v
ContextEngine + GreenSkills
    |
    v
Agent request / rollout prompt
    |
    v
Capability or Model request
    |
    v
Authorization
    |
    v
Runtime
    |
    v
Observation + Evidence
    |
    v
TrajectoryRecord
    |
    v
FailureMiner
```

The self-improvement package should not call providers, tools, files, shell, SQL, broker actions, or model routers directly. It should receive injected Runtime/Gateway boundaries and persist observations/evidence as trajectory inputs.

## Shared Contracts To Reuse

- `AgentRun.run_id` should become the common run identity for pilot trials, runtime events, context manifests, observations, and trajectory records.
- `ContextManifest.context_hash` should be recorded with rollout/trajectory evidence so trials are reproducible.
- `GreenSkill.fingerprint` should be recorded when a skill influenced a rollout prompt or context selection.
- `Capability.identity` should be recorded for capability-backed observations.
- `AuthorizationDecision` should remain the single proof that execution was allowed or denied.
- `Observation.evidence_refs` and `artifact_refs` should be the bridge into self-improvement trajectories.

## What Should Be Merged/Shared

- Runtime identity, action, observation, and event models.
- Context manifests and hashes.
- Skill fingerprints and disclosed context refs.
- Capability catalog identities and versions.
- Authorization decisions and denial reasons.
- Evidence/artifact references.

## What Must Remain Separate

- Self-improvement task generation should remain research-only and must not mutate model policy, provider routing, or production code automatically.
- Failure mining should propose candidate tasks only; it must not create production memory or change skills without review.
- MCP should remain a transport and must not become a business policy layer.
- GreenSkills should not grant capabilities; they only declare and disclose procedural/context inputs.
- ContextEngine should not decide authorization.

## Integration Gaps

1. `TrajectoryRecord` does not yet include `run_id`, `context_manifest_id`, `context_hash`, `skill_fingerprints`, `capability_id`, `capability_version`, `authorization_reason`, `observation_id`, `artifact_refs`, or `evidence_refs`.
2. `RolloutResult` does not yet carry Runtime VNext execution identity or observation references.
3. `SelfImprovementLoop.run_task` does not yet accept a prepared `ContextManifest` or disclosed skills.
4. Pilot execution still depends on injected Gateway model calls and does not yet bind those calls into Runtime events.
5. Full production Gateway/provider/certification/correction-capture interfaces remain absent from this lab checkout.
6. Full-repository Ruff remains blocked by unrelated pre-existing `self_improvement` lint issues.

## Recommended Next Implementation

1. Extend `RolloutResult` and `TrajectoryRecord` with optional Runtime VNext identity/evidence fields while preserving backward compatibility.
2. Add a small adapter that converts a successful `Observation` into trajectory evidence metadata.
3. Add `ContextManifest` and `SkillDisclosure` references to rollout inputs, but keep them advisory/request-shaping only.
4. Add tests proving trajectory evidence can reconstruct `run_id -> context_hash -> skill_fingerprint -> authorization -> observation`.
5. Add tests proving self-improvement cannot execute a capability denied by Authorization even when a skill declares it.
6. Leave production GreenZ data/Gateway binding blocked until authoritative interfaces exist in the checkout.

## Non-Goals For The Next Step

- Do not implement durable GreenMemory yet.
- Do not implement autonomous subagent execution yet.
- Do not add broker/trading actions.
- Do not add a second Gateway, router, authorization engine, context identity, or provenance store.
- Do not clean unrelated `self_improvement` Ruff issues in this feature branch unless explicitly authorized as a separate cleanup.

## Conclusion

The branches are Git-compatible, but the next work should be a narrow contract integration inside `self_improvement`: carry Runtime VNext identity, context hashes, skill fingerprints, authorization decisions, observations, artifacts, and evidence into rollout and trajectory records. That will connect the research loop to the governed execution platform without collapsing their responsibilities.
