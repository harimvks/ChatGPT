# Codex Handoff — GAIEP Capability Registry + Read-Only MCP Gateway

## Context

Runtime VNext execution-boundary work is implemented and integration-hardened on:

- Branch: `gaiep/self-improvement-pilot-execution`
- Runtime foundation commit: `f9bcf45`
- Integration hardening commit: `19cbba6`
- Latest reported validation: 30 tests passed, Ruff clean, Pyright clean, wheel build passed, wheel inspection passed, clean-venv import smoke passed.
- Current integration verdict: **INTEGRATION COMPLETE WITH GAPS**.

The remaining gaps are explicitly documented as full-repository integration gaps because this ChatGPT lab snapshot does not contain the production Gateway/provider failover, certification, correction-capture, and production provenance surfaces needed to prove those paths end-to-end.

This task is the **next phase**: complete the capability model and prepare/implement the read-only MCP gateway at the correct architectural boundary.

## Primary references

- OpenHands Software Agent SDK: https://github.com/OpenHands/software-agent-sdk
- OpenHands: https://github.com/OpenHands/OpenHands
- Hermes Agent: https://github.com/NousResearch/Hermes-Agent
- MetaTrader MCP reference: https://github.com/ariadng/metatrader-mcp-server
- Target GAIEP repository: https://github.com/harimvks/greenz-ai-engineering

Do not copy any reference project wholesale.

## Non-negotiable architecture

```text
Agent / LLM
    |
    v
MCP transport / other capability transport
    |
    v
Capability Registry
    |
    v
Deterministic Authorization Engine
    |
    v
Runtime
    |
    v
GreenZ domain capability
```

MCP is a **transport/interface**, not an authority layer.

A tool is not a capability. A capability is not permission.

```text
Tool != Capability != Permission
```

The LLM's claimed security/risk classification is advisory metadata only. It must never override deterministic GAIEP authorization.

Default is DENY.

Unknown capability is DENY.

Malformed request is DENY.

Denied action must never reach Runtime.

No live trading, broker execution, order submission, cancellation, modification, or flattening is part of this phase.

---

# Phase A — Audit existing Runtime VNext first

Before implementation:

1. Inspect `main`.
2. Inspect `gaiep/self-improvement-pilot-execution`.
3. Inspect commits `f9bcf45` and `19cbba6`.
4. Inspect existing Runtime VNext contracts and tests.
5. Search the full repository for existing capability, tool, policy, authorization, registry, Gateway, provenance, and run identity abstractions.
6. Do not create duplicate abstractions if an existing contract is suitable.
7. If the real `greenz-ai-engineering` repository contains a stronger existing implementation than this lab snapshot, prefer that contract when integrating there.

Do not rewrite the Runtime foundation merely to resemble OpenHands.

---

# Phase B — Capability model

Implement or harden a typed capability contract.

Minimum fields:

- `capability_id`
- `version`
- `description`
- `access_mode`: `READ` or `ACTION`
- `risk_class`
- `required_scopes`
- `allowed_runtime`
- `provenance_required`
- `audit_required`
- `input_schema_ref` or equivalent typed schema reference
- `output_schema_ref` or equivalent typed schema reference

Capability identity must be stable and versioned.

Do not allow arbitrary Python callables to become capabilities through registration alone.

A capability declaration must describe the boundary; actual execution remains behind Runtime.

---

# Phase C — Capability Registry

Implement a deterministic registry.

Required behavior:

- register capability
- lookup capability by ID/version
- reject duplicate identity
- reject malformed capability
- reject unknown capability
- deterministic enumeration
- immutable/frozen metadata after registration where practical
- explicit registry version if needed

Registration does NOT imply authorization.

A capability may exist in the registry and still be denied by policy.

Add tests for:

- registration
- duplicate registration
- lookup
- unknown capability
- version mismatch
- malformed metadata
- deterministic enumeration

---

# Phase D — Authorization integration

Use the existing Runtime VNext authorization machinery.

Do not create a second policy engine.

Effective authority must remain the intersection of:

```text
Skill capabilities
    ∩
TaskPolicy
    ∩
WorkspaceScope
    ∩
GlobalPolicy
    ∩
Runtime/resource budget
    ∩
ParentAuthority
```

Required properties:

- default deny
- unknown capability deny
- unsupported access mode deny
- workspace violation deny
- budget violation deny
- parent authority escalation deny
- capability version mismatch deny

The authorization decision must remain auditable and linked to `run_id` and the capability identity.

---

# Phase E — Read-only GreenZ capability set

Create the **minimum useful read-only capability catalog**.

Prefer domain-neutral names and typed schemas.

Initial candidates:

```text
market.get_snapshot
market.get_quote
market.get_candles
measurements.get_snapshot
measurements.get_breadth
measurements.get_options_state
forecast.get_current
forecast.get_history
strategy.get_state
risk.get_state
portfolio.get_positions
```

Only register capabilities that can be backed by existing authoritative GreenZ interfaces.

Do NOT invent fake data providers or mock production interfaces into the final runtime.

If a domain interface is absent, register the capability as a documented future candidate rather than pretending it is implemented.

Each implemented capability must specify:

- authoritative source
- input schema
- output schema
- freshness semantics
- point-in-time semantics where relevant
- provenance/evidence requirement
- risk classification

---

# Phase F — MCP boundary

Implement the read-only MCP gateway only after the capability registry and authorization contracts are stable.

The MCP adapter should translate:

```text
MCP tool request
      |
      v
Capability request
      |
      v
Authorization
      |
      v
Runtime execution
      |
      v
Typed observation
```

The MCP layer must NOT:

- contain business authorization logic
- call providers directly
- bypass Runtime
- bypass provenance
- bypass workspace policy
- bypass budget policy
- choose models/providers
- execute arbitrary Python
- execute arbitrary shell
- execute arbitrary SQL
- execute broker actions

MCP errors should distinguish at least:

- unknown capability
- invalid request
- unauthorized
- unavailable capability
- execution failure
- stale/unavailable data where domain semantics require it

Do not leak secrets or internal filesystem paths through MCP errors.

---

# Phase G — MCP request identity and evidence

Every MCP request must be attributable to an existing `run_id`/execution identity.

Do not create a second run identity system.

Trace should remain reconstructable:

```text
AgentRun
  -> MCP request
  -> Capability resolution
  -> Authorization decision
  -> Runtime action
  -> Observation
  -> Evidence/provenance
```

Large responses must use artifact/reference mechanisms where the existing architecture requires them. Do not duplicate large payloads into event history.

Reuse the existing provenance/evidence mechanism.

---

# Phase H — Security tests

Add integration tests proving:

1. known read capability + authorized request executes.
2. unknown capability is denied.
3. malformed request is denied.
4. capability version mismatch is denied.
5. task policy denial prevents Runtime execution.
6. skill policy denial prevents Runtime execution.
7. workspace violation prevents Runtime execution.
8. budget violation prevents Runtime execution.
9. child run cannot gain parent-excluded capability.
10. MCP cannot directly call Runtime without authorization.
11. MCP cannot directly call a provider.
12. MCP cannot execute arbitrary Python.
13. MCP cannot execute arbitrary shell.
14. MCP cannot execute arbitrary SQL.
15. MCP cannot submit a broker order.
16. denied requests produce auditable authorization events.
17. successful requests produce observation/evidence linkage.
18. execution failures do not become successful observations.
19. secrets are not included in MCP responses/errors.
20. large outputs use artifact references when required.

---

# Phase I — Domain integration tests

For every capability actually implemented, test against the authoritative domain interface rather than a duplicated fake implementation.

At minimum verify:

- point-in-time correctness
- stale data behavior
- missing data behavior
- schema validation
- provenance linkage
- run identity linkage

For market/measurement capabilities, preserve GreenZ's fail-closed/no-fabrication philosophy.

For Forecast capabilities, do not create a generic `Prediction` entity. Use the existing `Forecast` / `ForecastResolution` contracts.

---

# Phase J — Model boundary

MCP/capabilities must not become a model router.

Model selection remains under:

```text
ModelPolicy -> ModelGateway -> provider
```

No capability, skill, MCP server, Runtime, or context component may secretly select a provider/model.

---

# Phase K — Future ACTION capability boundary

Do NOT implement action capabilities now.

Reserve the namespace and architecture for future capabilities such as:

```text
trade.submit
trade.cancel
trade.modify
trade.flatten
```

But mark them explicitly as unavailable/forbidden in this phase.

A request for any future ACTION capability must return deterministic denial rather than falling through to an implementation.

---

# Phase L — OpenHands adoption boundary

Adopt only the useful architectural patterns:

- agent/runtime separation
- action/observation loop
- explicit execution boundary
- workspace isolation
- typed security decisions
- reconstructible execution history

Do not add OpenHands UI, product-specific server architecture, Docker orchestration, or unnecessary dependencies.

---

# Phase M — Hermes compatibility

Do not implement the full Hermes-derived ContextEngine/Skills/Memory/Subagent layer in this task.

Only ensure the capability contracts are compatible with future:

- ContextEngine
- GreenSkills
- GreenMemory
- bounded subagents

In particular, parent/child authority constraints must remain enforceable.

---

# Phase N — Packaging and validation

Run the complete existing suite.

Required:

```bash
uv run --extra dev pytest
uv run --extra dev ruff check .
uv run --extra dev pyright
uv build
```

Inspect wheel contents.

Run a clean-venv import/smoke test from the built wheel.

Do not silently remove or weaken existing tests.

Do not alter Ruff/Pyright versions merely to obtain green validation.

---

# Phase O — Documentation

Create/update:

`docs/GAIEP_CAPABILITY_MCP_ARCHITECTURE.md`

Include:

1. capability model
2. registry
3. authorization boundary
4. MCP transport boundary
5. Runtime boundary
6. read-only capability catalog
7. request/evidence lifecycle
8. security invariants
9. unavailable future action capabilities
10. OpenHands patterns adopted/rejected
11. Hermes compatibility boundary
12. remaining gaps

Add a Mermaid diagram showing:

```text
Agent
  |
MCP
  |
Capability Registry
  |
Authorization
  |
Runtime
  |
GreenZ Domain
  |
Observation/Evidence
```

---

# Phase P — Final report

Create:

`reports/GAIEP_CAPABILITY_MCP_IMPLEMENTATION_REPORT.md`

Include:

- baseline commit
- final commit
- branch
- files changed
- capability catalog
- authorization rules
- MCP transport details
- tests
- pytest result
- Ruff result
- Pyright result
- wheel result
- security findings
- known gaps
- future action capabilities explicitly deferred
- whether full-repository integration was possible

Final verdict must be exactly one:

`COMPLETE`

`COMPLETE WITH NON-BLOCKING GAPS`

`PARTIALLY COMPLETE`

`BLOCKED BY MISSING AUTHORITATIVE DOMAIN INTERFACES`

Do not call the task COMPLETE merely because unit tests pass.

---

# Git discipline

Work on a dedicated feature branch.

Do not modify `main` directly.

Do not merge automatically.

Preserve unrelated work.

Before committing:

```bash
git status
git diff
git diff --check
```

Use logical commits where practical:

1. capability contracts/registry
2. authorization integration
3. read-only capability adapters
4. MCP transport
5. tests/security
6. documentation/report

---

# Critical implementation rule

If the authoritative GreenZ domain interface does not exist in the current checkout, DO NOT fabricate it.

Instead:

- document the missing interface;
- implement the generic capability/authorization/MCP boundary if possible;
- leave that specific capability unavailable;
- report the exact blocker.

The goal is a real, governed capability layer—not a demo MCP server.
