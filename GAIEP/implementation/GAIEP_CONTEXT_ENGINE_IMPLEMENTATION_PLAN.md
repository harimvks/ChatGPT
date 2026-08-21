# GAIEP Context Engine — Implementation & Validation Plan

**Status:** Proposal
**Date:** 2026-08-21
**Design basis:** `GAIEP_CONTEXT_ENGINE_DESIGN.md`, `GAIEP_AGENT_RUNTIME_CONTRACTS.md`, current GreenZ repositories

> This plan is deliberately implementation-safe: the current GreenZ engineering context path remains the behavioral baseline until the new Context Engine passes compatibility validation.

---

## 1. Objective

Convert the existing engineering context-building path into a first-class GAIEP Context Engine without changing model capability, certification behavior, security boundaries, or current task outcomes as an initial goal.

The migration target is:

```text
CURRENT
run_task
  -> context builder
  -> Gateway

TARGET
AgentRun
  -> ContextEngine
       -> SELECT
       -> BUDGET
       -> COMPRESS
       -> MANIFEST
       -> Gateway
       -> OBSERVE
```

The first milestone is **behavioral equivalence**, not maximum sophistication.

---

# 2. Source Baseline

The implementation must begin from the actual current engineering context path and its callers.

Before modifying source code, capture:

```text
runner/context.py
runner/run_task.py
runner/qwen_task.py
runner/gateway_client.py
related prompt/task configuration
existing context tests
certification corpus/test harness
```

Also inspect the platform-side request/context contracts used by the Gateway so the engineering runtime does not duplicate them.

The source repositories remain read-only during this design stage.

---

# 3. Target Package Layout

Initial target inside `greenz-ai-engineering`:

```text
runtime/
└── context/
    ├── __init__.py
    ├── contracts.py
    ├── engine.py
    ├── selector.py
    ├── budget.py
    ├── compressor.py
    ├── manifest.py
    ├── sanitization.py
    ├── profiles.py
    ├── errors.py
    └── adapters/
        ├── __init__.py
        └── legacy_builder.py
```

Tests:

```text
tests/runtime/context/
├── test_contracts.py
├── test_selector.py
├── test_budget.py
├── test_compressor.py
├── test_manifest.py
├── test_sanitization.py
├── test_profiles.py
└── test_legacy_compatibility.py
```

Do not create a second generic `common.py` or generic provider layer.

---

# 4. Phase 0 — Archaeology Before Coding

## 4.1 Capture current behavior

Document:

- input structure to the current context builder;
- all context sources;
- serialization order;
- redaction rules;
- payload limits;
- hashes/fingerprints;
- prompt rendering format;
- caller assumptions;
- error behavior;
- tests;
- certification dependencies.

## 4.2 Produce a golden fixture

For representative tasks, save a **sanitized logical context fixture** containing:

```text
source references
section order
redaction outcomes
payload length
context hash
model request metadata
```

Do not commit secrets, private credentials, or unrestricted production data.

## 4.3 Representative task matrix

At minimum:

```text
implementation
refactor
review
review_audit
testing
```

Include at least one task with:

- multiple source files;
- a large source file;
- test context;
- project instructions;
- a forbidden/sensitive path candidate;
- output requiring validation.

---

# 5. Phase 1 — Introduce Contracts

Implement the smallest immutable types:

```text
ContextItem
ContextBudget
CompressionRecord
ContextManifest
ContextProfile
```

Reuse the contract vocabulary established in `GAIEP_AGENT_RUNTIME_CONTRACTS.md`.

### Acceptance

- immutable;
- typed enums where state is closed;
- timezone-aware timestamps;
- deterministic serialization;
- deterministic hashing;
- validation errors are typed;
- no I/O in contract classes.

---

# 6. Phase 2 — Legacy Builder Adapter

Create:

```text
runtime/context/adapters/legacy_builder.py
```

Its responsibility is to adapt the current builder's behavior to the new Context Engine contract.

```text
ContextEngine
     |
     v
LegacyBuilderAdapter
     |
     v
existing context builder
```

The adapter must not alter existing selection semantics unless required to satisfy a contract invariant.

This gives us a safe seam for migration.

---

# 7. Phase 3 — ContextManifest

Create the manifest from the adapted result.

The manifest should record:

```text
instructions
project instructions
task refs
source refs
skill refs
memory refs
tool schema refs
prior output refs
compression refs
estimated tokens
actual tokens if available
output reserve
context hash
engine version
```

### Critical requirement

The manifest must describe **what the model actually received**, not merely what the runner intended to send.

---

# 8. Phase 4 — Deterministic Selector

Extract selection logic into:

```text
selector.py
```

Initial selection sources:

```text
runtime constraints
user/task specification
project instructions
explicit source references
required validation context
selected skills
selected memory
tool schemas
prior outputs
```

Selection should return a stable ordered sequence of `ContextItem` objects.

### Selection algorithm

```text
collect candidates
      ↓
normalize
      ↓
classify
      ↓
validate provenance
      ↓
apply policy
      ↓
rank
      ↓
return ordered candidates
```

No vector search in this phase.

---

# 9. Phase 5 — Budget Calculator

Implement:

```text
budget.py
```

Input:

```text
model/deployment context limit
system reserve
output reserve
tool schema reserve
selected context
```

Output:

```text
ContextBudget
```

### Required behavior

```text
mandatory context
    ↓
fit check
    |
    +-- cannot fit → typed failure
    |
    +-- fits → optional context
                 ↓
              priority order
                 ↓
              available budget
```

Optional context must be discarded before mandatory context.

---

# 10. Phase 6 — Safe Compression

Initially implement only deterministic transformations.

Allowed examples:

```text
duplicate elimination
whitespace normalization
bounded optional-output truncation
structured artifact shortening
```

Do not use another LLM to compress context in Phase 1.

### Compression acceptance

For each compression:

```text
input item
method
input tokens
output tokens
provenance
preserved semantic class
```

must be recorded.

---

# 11. Phase 7 — Sanitization

Move existing sensitive-path/content handling behind a single explicit interface:

```python
sanitize(context_item, workspace_scope, policy)
```

The sanitization layer must run before model exposure.

### Security tests

Attempt:

```text
path traversal
sensitive file selection
credential-like content
unauthorized workspace path
```

Expected result:

```text
DENIED / REDACTED
```

with no secret disclosure in the error/event record.

---

# 12. Phase 8 — Context Profiles

Create task profiles without changing current prompts.

Initial profiles:

```text
CODING_IMPLEMENTATION
CODING_REFACTOR
CODING_REVIEW
CODING_REVIEW_AUDIT
CODING_TESTING
```

Each profile defines priority only.

Example:

```yaml
CODING_REVIEW:
  mandatory:
    - task
    - project_instructions
    - changed_files
  high:
    - related_interfaces
    - tests
  normal:
    - adjacent_implementation
  optional:
    - historical_context
```

Profiles must never override security or certification policies.

---

# 13. Phase 9 — Runner Integration

Change the runner integration from:

```text
run_task
  -> build_context()
  -> gateway
```

to:

```text
run_task
  -> ContextEngine.build()
  -> Gateway
```

The Gateway request should remain compatible with the existing platform contract.

No provider/model routing rewrite occurs here.

---

# 14. Phase 10 — OBSERVE / Trajectory Events

Emit observable events:

```text
context.selected
context.budgeted
context.compressed
context.rendered
context.observed
```

Each event should reference the same `run_id` and `manifest_id`.

Do not store hidden model reasoning.

---

# 15. Compatibility Validation

This is the most important phase.

Run the legacy and new context paths against the same task fixtures.

```text
                same task
                    |
          +---------+---------+
          |                   |
          v                   v
      LEGACY              CONTEXT ENGINE
          |                   |
          +---------+---------+
                    |
                    v
               COMPARATOR
                    |
       +------------+-------------+
       |            |             |
       v            v             v
    context      model         validation
    structure    outcome       outcome
```

Compare:

```text
source selection
section order
redaction
payload limits
context hash
Gateway request
model output
validation outcome
latency
```

---

# 16. Compatibility Classification

Differences should be classified rather than blindly treated as failures.

```text
IDENTICAL
EXPECTED IMPROVEMENT
EXPECTED NORMALIZATION
UNINTENDED DIFFERENCE
SECURITY REGRESSION
BEHAVIORAL REGRESSION
```

Any `SECURITY REGRESSION` or `BEHAVIORAL REGRESSION` blocks migration.

---

# 17. Certification Regression Gate

Run the existing engineering certification corpus through the new context path.

The required gate is:

```text
new context path
      |
      v
existing certification suite
      |
      +--> no unexplained pass loss
      +--> no new security violation
      +--> no new overwrite violation
      +--> no certification evidence corruption
```

Do not change certification thresholds merely to make the new Context Engine pass.

---

# 18. Performance Gate

Measure:

```text
context construction latency
serialization latency
hashing latency
memory footprint
payload size
model latency
end-to-end task latency
```

The Context Engine should add negligible overhead relative to model inference.

Target for initial implementation:

> Context processing should remain a small fraction of total task latency and must not materially degrade the existing engineering workflow.

Do not optimize prematurely before measuring.

---

# 19. Cost Gate

Measure:

```text
input tokens before
input tokens after
output tokens
context compression savings
cost per task
```

The Context Engine should make context economics **measurable**, not necessarily immediately cheaper.

A more expensive context that materially improves success may be justified; this must be demonstrated through certification/evidence rather than intuition.

---

# 20. Failure Handling

Typed failures:

```text
ContextSourceNotFound
ContextSourceForbidden
ContextSanitizationFailure
ContextBudgetExceeded
ContextCompressionFailure
ContextManifestInvalid
ContextHashMismatch
ContextPolicyViolation
```

Runner behavior should be explicit:

```text
failure
  |
  +--> recoverable → adjust optional context / retry policy
  |
  +--> escalation eligible → ModelPolicy / EscalationPolicy
  |
  +--> non-recoverable → fail closed
```

Never silently send incomplete mandatory context.

---

# 21. Test Matrix

| Area | Unit | Integration | Certification | Security |
|---|---:|---:|---:|---:|
| Contracts | ✓ | | | ✓ |
| Selection | ✓ | ✓ | ✓ | ✓ |
| Budget | ✓ | ✓ | ✓ | |
| Compression | ✓ | ✓ | ✓ | |
| Sanitization | ✓ | ✓ | | ✓ |
| Manifest | ✓ | ✓ | ✓ | |
| Profiles | ✓ | ✓ | ✓ | |
| Gateway adapter | | ✓ | ✓ | ✓ |
| Compatibility | | ✓ | ✓ | ✓ |
| Trajectory | ✓ | ✓ | ✓ | |

---

# 22. Golden Test Corpus

Create a dedicated Context Engine fixture set in the `ChatGPT` design workspace first.

Proposed logical cases:

```text
CTX-001 minimal implementation
CTX-002 multi-file implementation
CTX-003 refactor with interfaces
CTX-004 review with diff + tests
CTX-005 review audit with historical context
CTX-006 testing task
CTX-007 large source payload
CTX-008 mandatory-context overflow
CTX-009 optional-context overflow
CTX-010 sensitive-path attempt
CTX-011 duplicate context
CTX-012 compression case
CTX-013 prior-output case
CTX-014 tool-schema budget case
CTX-015 model-escalation context case
```

Fixtures should use sanitized/reproducible content and avoid copying sensitive production material.

---

# 23. No Source Repository Changes Yet

During this planning stage, all implementation code, fixture design, and reports remain under:

```text
ChatGPT/GAIEP/
```

Only after:

```text
contract review
+
architecture review
+
fixture approval
+
compatibility criteria
```

should a controlled implementation branch be created in `greenz-ai-engineering`.

---

# 24. Implementation Branch Strategy

When implementation is approved:

```text
main
 |
 +-- feature/gaiep-context-engine
        |
        +-- contracts
        +-- adapter
        +-- selector
        +-- budget
        +-- sanitization
        +-- tests
        +-- compatibility report
```

Do not mix Context Engine work with subagent, routing, or unrelated platform changes.

One capability migration per branch/PR is preferred.

---

# 25. Rollback Strategy

If compatibility fails:

```text
ContextEngine
     |
     v
LegacyBuilderAdapter
     |
     v
Existing context builder
```

The adapter remains available until the new implementation is certified as behaviorally equivalent.

This means rollback is a configuration/integration decision rather than a source-recovery emergency.

---

# 26. Exit Criteria for Context Engine Phase 1

Phase 1 is complete only when all are true:

- [ ] contracts implemented and tested;
- [ ] legacy adapter implemented;
- [ ] deterministic selection implemented;
- [ ] budget enforcement implemented;
- [ ] sanitization preserved;
- [ ] deterministic compression implemented where required;
- [ ] ContextManifest generated;
- [ ] context hash reproducible;
- [ ] trajectory events emitted;
- [ ] certification regression suite passes without unexplained degradation;
- [ ] security regression suite passes;
- [ ] performance impact measured and accepted;
- [ ] cost/context metrics available;
- [ ] rollback path tested;
- [ ] implementation documented in the source repository after approval.

---

# 27. After Phase 1

Only after the above is stable should GAIEP proceed to:

```text
Phase 2
  GreenSkills

Phase 3
  bounded Subagent Runtime

Phase 4
  Tool Search / progressive disclosure

Phase 5
  semantic/fingerprint context retrieval

Phase 6
  adaptive routing / multi-model disagreement
```

This ordering is intentional: **context, authority, evidence and safety come before autonomy.**

---

# 28. Final Recommendation

The safest and highest-value path is not to copy Hermes' context engine wholesale.

Instead:

```text
Existing GreenZ context builder
             |
             v
       compatibility adapter
             |
             v
       GAIEP Context Engine
             |
     +-------+-------+-------+
     |       |       |       |
   select  budget  compress observe
     |       |       |       |
     +-------+-------+-------+
             |
             v
      ContextManifest
             |
             v
      Existing Gateway
```

The Context Engine becomes the **first real runtime subsystem** of GAIEP Runtime VNext while preserving the current GreenZ engineering system as the behavioral baseline.
