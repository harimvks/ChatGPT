# Phase 2 — Bounded Subagent Runtime

## Implemented boundary

```text
Parent AgentRun
      |
      | explicit allow_subagents
      | child count budget
      | child token budget
      | max depth
      v
BoundedSubagentExecutor
      |
      | depth = 1
      | recursive policy = false
      v
SubagentRequest
      |
      v
GovernedSubagentWorker
      |
      | injected governed execution callback
      v
Existing Context / Skill / Gateway path
```

## Architectural rule

A subagent is **not** a second agent runtime.

It is a bounded execution of a child task using the same governed platform path as the parent.

Therefore the worker does not contain:

- a model registry;
- a provider registry;
- direct Ollama calls;
- an independent routing policy;
- recursive spawning;
- unbounded retries.

## Security properties

The current implementation enforces:

1. parent must explicitly allow subagents;
2. parent must have positive child depth/count/token budgets;
3. child depth is exactly one;
4. child policy disables recursive subagents;
5. requested token budget cannot exceed the parent's child budget;
6. worker rejects depth > 1;
7. worker rejects child policies that re-enable subagents;
8. worker requires positive step/timeout/token budgets.

## What remains

The next step is to connect the injected execution callback to the existing VNext runtime executor so a subagent can actually run a registered read-only GreenSkill through the existing ContextBuilder and Gateway.

Only after that integration passes should write-capable subagents be considered.
