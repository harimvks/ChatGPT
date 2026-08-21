# Phase 1 Vertical Slice — AgentRun to Evidence

## Implemented

The first executable VNext path is now represented in `platform_vnext.runtime.engine.RuntimeVNext`.

```text
AgentRun
  ↓
PLANNED
  ↓
AUTHORIZED
  ↓
ContextManifest
  ↓
SKILL_READY
  ↓
EXECUTING
  ↓
PlatformAdapter
  ↓
Existing Gateway boundary
  ↓
VALIDATING
  ↓
EVIDENCE_READY
  ↓
GOVERNANCE
  ↓
ACCEPTED
```

## Deliberate limitations

This is a **contract/vertical-slice executor**, not the production engineering runner yet.

It does not currently:

- execute arbitrary tools;
- modify workspaces;
- run repository tests itself;
- spawn subagents;
- perform autonomous retries;
- mutate GreenMemory;
- make a second model-routing decision.

Those remain later layers.

## Why this is the correct first slice

The runtime now proves the orchestration boundary without duplicating the platform's existing model execution machinery.

The real platform remains responsible for:

```text
certification
classification policy
provider registry
model registry
provider selection
LOCAL/CLOUD eligibility
failover
provider execution
routing observability
```

The VNext runtime remains responsible for:

```text
AgentRun lifecycle
skill authorization
context handoff
execution orchestration
validation boundary
evidence lifecycle
future subagent orchestration
```

## Next gate

Before adding subagents or framework integrations, wire a real `ContextFactory` to the existing platform context primitives and execute one real certified capability through `GreenZPlatformAdapter` in an integration environment.
