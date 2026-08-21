# GAIEP-LAB Runtime VNext — Implementation Status

**Branch:** `lab/runtime-vnext`
**Upstream repositories:** protected; no changes made there.

## Phase 9 audit status

The laboratory code has now been audited at repository/tree level and the duplicate `platform-vnext/` runtime tree is being removed in favor of the canonical `platform_vnext/` package. The duplicate engineering placeholder trees remain empty and are not imported by the package configuration.

## Implemented

```text
[done] upstream provenance baseline
[done] initial file-level responsibility map
[done] canonical platform_vnext package
[done] ContextBuilderBase compatibility seam
[done] fail-closed context redaction boundary
[done] AgentRun / WorkspaceScope / TaskPolicy / ModelPolicy contracts
[done] GreenSkill / SkillStep contracts
[done] bounded depth-1 SubagentRequest / Handle / Result runtime
[done] governed subagent worker bridge
[done] structured runtime evidence events
[done] WorkspaceMutationGuard
[done] evidence-producing WriteSkillExecutor
[done] GS-PY-001 Python Implementation skill orchestration
[done] allowlisted validation command runner
[done] GS-PY-001 validation profile
[done] model certification adapter
[done] fixed GreenZ engineering corpus references
[done] local deployment certification boundary
[done] isolated pytest contract tests
[done] isolated lab pyproject
```

## Not yet production-complete

```text
[ ] run full test suite in a real local environment
[ ] run ruff and pyright successfully against the complete lab package
[ ] wire the real greenz-ai-engineering Gateway composition root
[ ] execute a real read-only Gateway run on the Mac
[ ] execute a real isolated write/validation run on the Mac
[ ] connect certification output to the existing authoritative ledger
[ ] persist evidence/checkpoints
[ ] production-grade retry/repair loop
[ ] full tool registry and tool-policy enforcement
[ ] production filesystem atomicity/rollback semantics
[ ] governance decision persistence/promotion gates
[ ] model routing/promotion logic
[ ] framework/Hermes integration
[ ] GreenZAlgo V4 consumer integration
[ ] CI/release packaging and operational documentation
```

## Phase 9 acceptance rule

No VNext component is considered production-ready merely because its interface or unit tests exist. Promotion requires:

1. clean local test/lint/type-check results;
2. successful compatibility run against the real upstream Gateway;
3. evidence parity with the existing GreenZ engineering path;
4. security/path-boundary validation;
5. successful Qwen3.6:27B control run;
6. only then, candidate-model certification.

The upstream repositories remain unchanged throughout this laboratory phase.
