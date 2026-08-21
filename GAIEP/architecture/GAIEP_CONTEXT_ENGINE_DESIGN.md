# GAIEP Context Engine — Phase-1 Design Specification

**Status:** Proposal / implementation specification
**Date:** 2026-08-21
**Scope:** First runtime subsystem after GAIEP contract establishment

> This specification deliberately evolves the existing GreenZ engineering context builder rather than replacing it. The first implementation objective is behavioral preservation plus explicit contracts; retrieval, semantic memory, and advanced compression are later phases.

---

## 1. Executive Decision

GAIEP should promote the existing deterministic engineering context construction into a first-class **Context Engine** with four explicit lifecycle operations:

```text
SELECT → BUDGET → COMPRESS → OBSERVE
```

The engine is responsible for deciding **what context is available to the model**, how much can be supplied, how context is reduced when necessary, and what was actually consumed.

It is **not** responsible for:

- choosing the model/provider;
- granting filesystem or tool permissions;
- inventing durable memory;
- deciding research/trading truth;
- certification or promotion;
- executing tools.

Those concerns remain with their existing owners.

---

# 2. Why Context Engine Is the Next Step

The current GreenZ engineering stack already has a context-construction path with important properties: deterministic serialization, bounded payloads, redaction/sanitization, provenance and hashing. Those properties should be preserved.

The architectural problem is not that context construction is absent. The problem is that it is currently too closely coupled to a particular task runner.

The target is:

```text
CURRENT
runner
  └── context builder

TARGET
Agent Runtime
  └── Context Engine
        ├── selector
        ├── budget
        ├── compressor
        ├── manifest
        └── sanitization
```

The migration therefore starts as an **adapter/refactoring exercise**, not a rewrite.

---

# 3. Context Engine Boundary

```text
                    AgentRun
                       |
                       v
                +--------------+
                | ContextEngine|
                +------+-------+
                       |
        +--------------+---------------+
        |              |               |
        v              v               v
     SELECT          BUDGET         COMPRESS
        |              |               |
        +--------------+---------------+
                       |
                       v
                ContextManifest
                       |
                       v
                  Model Gateway
                       |
                       v
                     Model
                       |
                       v
                    OBSERVE
                       |
                       v
                Trajectory/Event
```

The Context Engine produces a **ContextManifest plus rendered context payload**, subject to the run's policy and token budget.

---

# 4. Design Invariants

## 4.1 Determinism first

For the same:

- task,
- source snapshot,
- instruction set,
- policy,
- selected references,
- and context-engine version,

selection and serialization should be deterministic unless an explicitly stochastic retrieval strategy is enabled in a future version.

## 4.2 Context cannot expand authority

Context can explain a permission. It cannot create one.

```text
Context
  ≠
Authorization
```

A prompt containing a shell command does not grant shell access.

## 4.3 Provenance is mandatory

Every externally sourced or retrieved context item must be traceable to a source reference.

## 4.4 Redaction occurs before model exposure

Sensitive data must be removed before context reaches the model.

## 4.5 Compression must preserve semantics as far as contractually possible

Compression is a transformation, not a license to silently drop mandatory instructions, constraints, source identity, or validation requirements.

## 4.6 Observation is not memory

The engine records what happened. A separate governed mechanism decides whether any observation becomes durable memory.

---

# 5. Context Sources

Phase 1 should support the existing source classes first:

```text
SYSTEM / RUNTIME INSTRUCTIONS
PROJECT INSTRUCTIONS
TASK SPECIFICATION
REPOSITORY / FILE REFERENCES
CURRENT CODE / DIFF CONTEXT
CERTIFICATION / VALIDATION CONTEXT
SELECTED SKILLS
SELECTED MEMORY REFERENCES
TOOL SCHEMAS
PRIOR TURN OUTPUTS
```

Do not introduce a general-purpose web/search retrieval engine in Phase 1.

---

# 6. Context Item Contract

The engine should internally normalize every candidate source into a common conceptual representation.

```python
@dataclass(frozen=True)
class ContextItem:
    item_id: str
    source_type: ContextSourceType
    source_ref: str
    content: str
    priority: int
    mandatory: bool
    sensitivity: SensitivityClass
    estimated_tokens: int
    provenance: ProvenanceRef
```

Important fields:

- `source_type` identifies what kind of context it is.
- `source_ref` identifies where it came from.
- `priority` supports budget selection.
- `mandatory` prevents critical constraints from being dropped.
- `sensitivity` drives sanitization.
- `estimated_tokens` supports deterministic budgeting.
- `provenance` makes the item auditable.

The actual implementation may split `content` from a payload/artifact reference for large files; the contract should not require huge strings to remain in memory.

---

# 7. SELECT

## 7.1 Purpose

`SELECT` answers:

> Which candidate context items are relevant and permitted for this run?

Selection must be constrained by:

```text
TaskPolicy
WorkspaceScope
ToolManifest
SkillManifest
MemoryManifest
source provenance
```

## 7.2 Selection order

Initial deterministic order:

```text
1. mandatory runtime constraints
2. task specification
3. applicable project instructions
4. directly referenced source files
5. required validation/certification context
6. selected skill material
7. selected memory references
8. tool schemas
9. optional prior outputs
```

The exact ranking should be configurable by task class, but mandatory constraints must always outrank optional context.

## 7.3 No semantic retrieval yet

Phase 1 should not depend on a vector database or embedding service.

Use explicit references and deterministic selectors first.

This is important because the existing GreenZ architecture intentionally treats more advanced memory/fingerprint search as a separate evolution path.

---

# 8. BUDGET

## 8.1 Purpose

`BUDGET` determines how much selected context can be placed into the model request.

The budget must account for:

```text
model context limit
system/runtime overhead
input context
tool schemas
output reserve
provider-specific constraints
```

The runtime should obtain the actual model/deployment constraints through the existing platform Gateway rather than duplicating provider knowledge.

## 8.2 Budget contract

```python
@dataclass(frozen=True)
class ContextBudget:
    context_window: int
    reserved_system_tokens: int
    reserved_output_tokens: int
    reserved_tool_tokens: int
    available_input_tokens: int
```

All values are non-negative.

```text
available_input_tokens
  = context_window
  - reserved_system_tokens
  - reserved_output_tokens
  - reserved_tool_tokens
```

The implementation must fail closed if the available budget becomes negative.

---

# 9. Mandatory vs Optional Context

The engine should classify context into:

```text
MANDATORY
HIGH
NORMAL
LOW
OPTIONAL
```

If mandatory context cannot fit within the available budget, the engine must **not silently continue with an incomplete request**.

It should return a typed budget failure such as:

```text
ContextBudgetExceeded
```

and allow the Task/Model policy to decide whether to:

- reduce optional material;
- compress eligible material;
- escalate to a larger-context certified model;
- or stop.

---

# 10. COMPRESS

## 10.1 Purpose

Compression reduces context while preserving mandatory semantics and provenance.

Phase 1 should implement only deterministic, low-risk compression.

Examples:

```text
whitespace normalization
repeated boilerplate removal
duplicate source reference elimination
bounded truncation of optional outputs
structured summarization of already validated artifacts
```

Do **not** begin with an LLM-generated recursive summarizer.

That can become a later, separately certified component.

## 10.2 Compression record

Every compression operation should be represented in the ContextManifest.

```python
@dataclass(frozen=True)
class CompressionRecord:
    compression_id: str
    source_item_id: str
    method: str
    input_tokens: int
    output_tokens: int
    information_class: str
    provenance_preserved: bool
```

## 10.3 Hard rule

Never compress away:

- security constraints;
- task acceptance criteria;
- required validation commands;
- authoritative source identity;
- explicit user requirements;
- model/tool policy boundaries.

---

# 11. SANITIZATION

Sanitization occurs before final context rendering.

```text
candidate context
      |
      v
classification
      |
      v
sanitization
      |
      v
selection/budget
      |
      v
rendered context
```

The implementation must preserve the existing GreenZ behavior for sensitive-path/content filtering.

Do not broaden access because a file was selected by the context engine.

---

# 12. ContextManifest Construction

The Context Engine should create the Phase-0 `ContextManifest` described in `GAIEP_AGENT_RUNTIME_CONTRACTS.md`.

```text
ContextManifest
├── instruction_refs
├── task_refs
├── project_instruction_refs
├── skill_refs
├── memory_refs
├── source_refs
├── tool_schema_refs
├── prior_output_refs
├── compression_refs
├── input_token_estimate
├── input_token_actual
├── output_token_reserve
└── context_hash
```

The manifest is the durable explanation of **what context was made available**, not necessarily a full copy of the rendered prompt.

---

# 13. Rendering

The engine should render context into a stable section structure.

Proposed logical order:

```text
[RUNTIME CONTRACT]

[TASK]

[PROJECT INSTRUCTIONS]

[RELEVANT SOURCE]

[VALIDATION / ACCEPTANCE]

[SKILLS]

[MEMORY]

[TOOLS]

[PRIOR OUTPUTS]
```

The exact textual delimiters can remain compatible with the existing Qwen/runner prompt format during migration.

Do not break current certification prompts merely to achieve the new conceptual architecture.

---

# 14. OBSERVE

`OBSERVE` occurs after the model/tool turn and records what context was actually involved in the execution.

The engine should record:

```text
manifest_id
selected item IDs
compressed item IDs
rendered token count
actual token count if available
model/deployment identity
turn count
tool-call count
validation result
context-budget events
```

The observation becomes a `TrajectoryRecord`/event and can later feed:

- context efficiency measurement;
- regression analysis;
- skill candidate generation;
- model routing analysis;
- future memory decisions.

It does not automatically write durable memory.

---

# 15. Context Efficiency Metrics

The Context Engine should expose metrics that let us answer:

> Are we spending context tokens on information that materially improves successful task completion?

Initial metrics:

```text
context_window_utilization
mandatory_context_fraction
optional_context_fraction
compression_ratio
source_item_count
selected_item_count
removed_item_count
tool_schema_tokens
prior_output_tokens
validation_success
retry_count
escalation_count
latency
cost
```

Derived metrics:

```text
successful_tokens_per_task
context_tokens_per_success
compression_saved_tokens
optional_context_success_delta
```

These should eventually be correlated with the certification ledger.

---

# 16. Existing Runner Migration

The existing runner context path should be wrapped first.

```text
CURRENT

run_task
   |
   +--> context builder
   |
   +--> Gateway

PHASE 1

run_task
   |
   +--> ContextEngineAdapter
   |        |
   |        +--> existing context builder
   |        +--> ContextManifest
   |
   +--> Gateway
```

Only after behavioral equivalence is established should the internal builder be split into selector/budget/compressor modules.

This gives us a safe migration point.

---

# 17. Behavioral Compatibility Gate

Before replacing the old path, run the existing certification corpus through both:

```text
LEGACY CONTEXT PATH
NEW CONTEXT ENGINE ADAPTER
```

Compare:

```text
context hash
selected source references
redaction behavior
payload limits
model response
validation outcome
latency
```

The first target is:

```text
NO REGRESSION
```

Not:

```text
NEW ARCHITECTURE AT ANY COST
```

---

# 18. Context Hashing

The context hash must be generated from canonical manifest data.

Conceptually:

```text
canonical(manifest)
      |
      v
SHA-256
      |
      v
context_hash
```

Do not hash nondeterministic fields such as timestamps unless they are intentionally part of identity.

The hash should allow two executions to answer:

> Did these runs receive the same logical context manifest?

---

# 19. Model Gateway Boundary

The Context Engine must not determine the model.

Instead:

```text
Context Engine
      |
      v
ContextManifest + payload
      |
      v
Gateway ReasoningRequest
      |
      v
Existing Platform Gateway
      |
      v
Certified deployment
```

This is critical for our current multi-model strategy.

The Mac may eventually use multiple local/API coding models, while the VPS may run research/prediction models. The Context Engine should not know or care where the model lives.

---

# 20. Context Profiles

The engine should support task-specific context profiles.

Initial profiles:

```text
CODING_IMPLEMENTATION
CODING_REFACTOR
CODING_DEBUG
CODING_TEST
CODING_REVIEW
RESEARCH_ANALYSIS
RESEARCH_HYPOTHESIS
TRADING_ANALYSIS
```

Each profile defines selection priorities and mandatory sections, but cannot weaken security or authority policies.

Example:

```yaml
profile: CODING_REVIEW
mandatory:
  - task
  - project_instructions
  - changed_files
  - acceptance_criteria
high:
  - relevant_tests
  - related_interfaces
normal:
  - adjacent_implementation
optional:
  - historical_notes
```

This provides a much better basis for efficient routing than blindly increasing context.

---

# 21. Future Semantic Retrieval Boundary

Semantic retrieval is explicitly deferred, but the contract should leave room for it.

Future:

```text
Selector
  |
  +--> deterministic selector
  |
  +--> fingerprint selector
  |
  +--> semantic selector
  |
  +--> repository graph selector
```

All selectors must produce the same `ContextItem` abstraction.

This means Vector DB / RAG can be introduced later without changing the AgentRun or ContextManifest contract.

---

# 22. Future Adaptive Compression

Later versions may use a certified model to compress selected context.

That component would itself require:

```text
model certification
compression-quality corpus
semantic preservation tests
provenance preservation tests
regression tests
cost/latency measurement
```

It must never be treated as an unverified utility simply because it operates on context.

---

# 23. Error Model

The Context Engine should expose typed failures.

Initial conceptual errors:

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

Errors should contain actionable metadata but must not expose secrets or unauthorized source content.

---

# 24. Phase-1 Acceptance Tests

The Context Engine phase is complete only when the following are verified.

### Selection

- mandatory context is always selected;
- forbidden context is never selected;
- explicit source references resolve deterministically;
- selection order is reproducible.

### Sanitization

- sensitive paths remain protected;
- sensitive content is redacted before rendering;
- redaction itself is observable without exposing the secret.

### Budget

- negative budgets are rejected;
- optional context is dropped before mandatory context;
- budget failures are explicit;
- output reserve is preserved.

### Compression

- mandatory context is not compressed away;
- compression is recorded;
- provenance survives compression;
- deterministic compression is reproducible.

### Manifest

- every rendered section maps to manifest references;
- hash is deterministic;
- tool schemas match ToolManifest;
- skill references match SkillManifest;
- memory references match MemoryManifest.

### Compatibility

- existing certification cases show no unexpected regression;
- legacy and new context hashes are compared;
- payload limits remain enforced;
- existing allowlist/overwrite protections remain unchanged.

---

# 25. Phase-1 Non-Goals

Do not implement yet:

```text
NO vector database
NO RAG service
NO autonomous web search
NO LLM summarization compressor
NO automatic memory promotion
NO skill learning
NO subagent scheduling
NO model routing rewrite
NO production execution context
```

Those are later layers.

---

# 26. Recommended Package Structure

After compatibility is established:

```text
runtime/context/
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

---

# 27. Implementation Sequence

```text
1. Define ContextItem / ContextBudget / CompressionRecord
        ↓
2. Implement ContextManifest builder using existing behavior
        ↓
3. Implement LegacyBuilderAdapter
        ↓
4. Add manifest/hash tests
        ↓
5. Add WorkspaceScope-aware selection
        ↓
6. Add deterministic budget calculator
        ↓
7. Add safe deterministic compression
        ↓
8. Emit Context/Trajectory events
        ↓
9. Run certification compatibility sweep
        ↓
10. Replace runner integration point
```

Only after these pass should we split more functionality out of the legacy builder.

---

# 28. Relationship to Hermes-Inspired Runtime

Hermes-inspired features are useful here because they encourage explicit context lifecycle management.

But GAIEP must retain GreenZ-specific constraints:

```text
Hermes-style runtime discipline
        +
GreenZ provenance
        +
GreenZ certification
        +
GreenZ governance
        +
GreenZ workspace restrictions
        =
GAIEP Context Engine
```

We should borrow the mechanism, not copy the entire architecture.

---

# 29. Final Decision

**Phase 1 should be a controlled refactoring of the existing context path into an explicit Context Engine contract.**

The success criterion is not architectural novelty.

It is:

> **same or better engineering-task outcomes, stronger provenance, explicit context budgets, deterministic behavior, and a clean foundation for future GreenMemory, GreenSkills, subagents, and multi-model routing.**

Only after that foundation is stable should GAIEP proceed to the Subagent Runtime.
