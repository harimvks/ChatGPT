# GAIEP-LAB

Isolated experimental workspace for GAIEP Runtime VNext.

## Protected upstream repositories

- https://github.com/harimvks/greenz-ai-platform
- https://github.com/harimvks/greenz-ai-engineering
- https://github.com/harimvks/GreenZAlgo_V4

These remain the reference baselines. GAIEP-LAB changes do not modify them.

## Current baseline

The initial baseline audit was performed against the `main` commits recorded in `provenance/UPSTREAM_SNAPSHOTS.yaml`.

## Working areas

```text
upstream/       provenance and reference mapping
platform-vnext/ generic platform implementation
engineering-vnext/ engineering runtime implementation
algo-vnext/     GreenZAlgo domain integration
frameworks/     isolated framework evaluations
experiments/    controlled alternatives
benchmarks/     reproducible evidence
```

## Rules

1. Never modify the original repositories from GAIEP-LAB work.
2. Record upstream commit SHAs before importing/reconciling.
3. Reuse existing contracts before creating replacements.
4. Keep framework dependencies isolated until evaluated.
5. Benchmark before replacing working behavior.
6. Preserve certification and security regression gates.
7. Promote upstream only through an explicit human decision.

## First implementation target

```text
existing platform contracts
        ↓
compatibility harness
        ↓
AgentRun
        ↓
Context Engine integration
        ↓
one GreenSkill
        ↓
read-only Subagent
        ↓
validation + evidence
```
