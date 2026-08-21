# Phase 9 — Integration & Hardening

## Objective

Move GAIEP-LAB from an interface-rich prototype to a verified runtime by testing it against the real GreenZ platform/engineering composition without modifying the upstream repositories.

## Audit findings

### Canonical package

`GAIEP-LAB/platform_vnext/` is the canonical Python package. A duplicate hyphenated `platform-vnext/` tree existed from an earlier scaffold and is being removed to eliminate ambiguous source locations.

### Empty placeholders

`engineering-vnext/` and `engineering_vnext/` contain no executable implementation at present. They are not part of the canonical runtime import path.

### Runtime maturity

The current runtime has unit/contract-level coverage for major primitives, but the real provider execution path remains an integration boundary. `RuntimeVNext` currently validates the provider response and records lifecycle evidence; production repository validation and mutation are provided by the write-skill path rather than the base runtime.

### Packaging

The lab `pyproject.toml` is intentionally isolated and currently targets Python 3.14 with strict Pyright. A local environment must satisfy this before test/lint/type-check results can be considered authoritative.

## Phase 9 gates

### Gate A — static integrity

```text
ruff check .
pyright
pytest -q
```

No production promotion if any gate fails.

### Gate B — contract/integration imports

Verify that the actual local checkouts expose the pinned ContextBuilder/Gateway interfaces and that the VNext adapters import without shadow copies.

### Gate C — read-only live execution

Run one harmless capability through:

```text
AgentRun
 → ContextBuilder
 → GreenSkill
 → VNext Adapter
 → existing CertifiedProviderRegistry
 → existing Gateway
 → real local provider/model
 → evidence
```

### Gate D — isolated write execution

Use a disposable workspace only. Execute one tiny approved mutation, then:

```text
mutation evidence
 → ruff
 → pyright
 → pytest
 → diff review
 → evidence
```

### Gate E — certification control

Run Qwen3.6:27B as the control against the fixed GreenZ corpus before any candidate model.

### Gate F — candidate sweep

Only after the control passes should Devstral/Qwen/DeepSeek/Kimi/Hugging Face candidates be evaluated.

## Non-goals in Phase 9

Do not add autonomous multi-agent recursion, production routing policy, Hermes integration, or GreenZAlgo V4 integration until the above gates pass.

## Promotion criterion

A VNext component is promoted only when its behavior is demonstrated against the real upstream path and its evidence is compatible with the existing GreenZ engineering certification/governance model.
