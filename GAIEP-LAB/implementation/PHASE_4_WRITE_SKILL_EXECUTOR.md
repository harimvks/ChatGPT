# Phase 4 — Write Skill Executor

The first write-capable execution primitive now sits behind the Phase 3 mutation guard.

## Flow

```text
GreenSkill
   |
   v
Mutation Plan
   |
   v
WorkspaceMutationGuard
   |
   +-- workspace boundary
   +-- allowed roots
   +-- forbidden roots
   +-- operation allowlist
   +-- approval
   |
   v
WriteSkillExecutor
   |
   +-- create / modify / delete
   +-- before SHA-256
   +-- after SHA-256
   +-- unified diff
   |
   v
MutationEvidence
   |
   v
Validation Gates
   |
   v
AgentRun Evidence / Governance
```

## Deliberate limitations

The executor currently performs only the filesystem mutation primitive. It does not decide what code to write, and it does not declare a mutation successful merely because the write succeeded.

A production Python implementation skill must add validation gates such as formatting, static analysis, tests, diff review, and repository-specific policy checks before the run can be promoted.

## Important safety property

The model never receives unrestricted filesystem access. Every mutation passes through the guard individually.

## Next step

Create a `PythonImplementationSkillExecutor` that composes:

1. bounded model execution;
2. mutation-plan extraction;
3. `WorkspaceMutationGuard`;
4. `WriteSkillExecutor`;
5. ruff/pyright/pytest validation;
6. diff review;
7. structured evidence;
8. governance decision.
