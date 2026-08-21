# Phase 3 — Workspace Mutation Guard

## Purpose

Prevent write-capable GreenSkills and subagents from receiving unrestricted filesystem access.

The guard authorizes a mutation before an executor receives permission to perform it.

## Authorization model

```text
Skill / Subagent
      |
      v
MutationRequest
      |
      +-- operation
      +-- target path
      +-- explicit approval
      |
      v
WorkspaceMutationGuard
      |
      +-- workspace boundary
      +-- allowed roots
      +-- forbidden roots
      +-- operation allowlist
      +-- symlink rejection
      |
      v
AUTHORIZED PATH
      |
      v
Filesystem executor
      |
      v
Diff / hash / validation / evidence
```

## Fail-closed properties

The initial guard rejects:

- operations not explicitly allowed;
- writes without explicit approval when approval is required;
- paths outside the workspace root;
- paths outside configured allowed roots;
- paths inside forbidden roots;
- path components that are existing symlinks.

## Important distinction

`WorkspaceMutationGuard` does **not** write files.

It only answers:

> Is this exact operation on this exact path authorized under this policy?

A separate filesystem executor will perform the mutation and generate a before/after diff and evidence record.

## Next step

Integrate the guard with a `WriteSkillExecutor` that:

1. obtains a bounded mutation plan;
2. requests authorization for each operation;
3. performs only authorized operations;
4. captures before/after hashes and diffs;
5. runs validation gates;
6. records the complete evidence chain.
