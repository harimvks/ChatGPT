# GAIEP Self-Improvement Engine — V0

This research-only implementation is inspired by the Ornith-1.5 methodology while preserving GAIEP-LAB safety boundaries.

## Current loop

```text
certification corpus / seed
        ↓
TaskFactory
        ↓
EngineeringTask
        ↓
ResearchRolloutRunner
        ↓
model/agent artifact
        ↓
EvaluationRunner / external gate
        ↓
EvaluationResult
        ↓
FailureMiner
        ↓
targeted follow-up task
```

The rollout function is injected by the research harness. The package does not own model routing or mutate production systems.

## Evidence boundary

External checks define success. Candidate model output cannot self-report a pass. Existing certification artifacts can be converted into deterministic research tasks, and supplied pytest/ruff/pyright commands can be executed through the external validation adapter.

## Deliberate non-goals

- no autonomous RL;
- no model-weight mutation;
- no production routing changes;
- no certification bypass;
- no automatic promotion;
- no modification of protected upstream repositories.

## Next stages

1. Connect rollout to the existing GAIEP local model/agent runner without bypassing the Gateway.
2. Add sandbox/workspace isolation for candidate code artifacts.
3. Persist rollout/evaluation evidence through existing provenance/storage contracts.
4. Add scaffold variants and compare completion, quality, latency and tool-call cost.
5. Mine recurring failure clusters into a controlled curriculum.
6. Export accepted trajectories for MLX/PyTorch LoRA experiments.
7. Only after sufficient evidence, investigate RL/self-improvement training on larger infrastructure.
