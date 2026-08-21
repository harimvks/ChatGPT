# GAIEP-LAB Runtime VNext — Implementation Status

**Branch:** `lab/runtime-vnext`
**Upstream repositories:** protected; no changes made there.

## Phase 9 audit status

The laboratory code has been audited at repository/tree level. The canonical executable package is `platform_vnext/`; the earlier duplicate `platform-vnext/` scaffold has been removed. The empty engineering placeholder trees remain non-executable and are not part of the canonical package path.

## Phase 9 hardening completed in this pass

```text
[done] pytest now discovers tests under tests/ and platform_vnext/
[done] guarded workspace exposes canonical workspace_root to GS-PY-001
[done] invalid GreenSkill test fixtures repaired to satisfy procedure invariant
[done] optional Gateway import moved behind runtime import boundary
[done] subagent skill resolver typed for strict Pyright
[done] unused runtime/skill imports removed
[done] static-verification GitHub Actions workflow added
```

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
[done] Phase 9 static verification workflow
```

## Verification state

The CI workflow has been added, but no workflow run is currently visible for the latest commit. Therefore **ruff, pyright and pytest have not been claimed as passing**. The next authoritative result must come from GitHub Actions or a real local environment using the same commands.

## Not yet production-complete

```text
[ ] clean ruff result
[ ] clean pyright result
[ ] clean full pytest result
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
[ ] release packaging and operational documentation
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
