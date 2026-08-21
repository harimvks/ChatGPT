# GAIEP Agent Runtime VNext — Agent Runtime Contracts

**Status:** Proposal / contract specification
**Date:** 2026-08-21
**Scope:** First implementation boundary for GAIEP Runtime VNext
**Authority:** Derived from `GAIEP_RUNTIME_VNEXT_DESIGN.md` and the audited GreenZ AI Engineering / GreenZ AI Platform / GreenZAlgo V4 repositories.

> This document defines contracts only. It does not implement subagents, Tool Search, skills, or a new model/provider abstraction.
>
> The source repositories remain read-only authorities during this design phase. `ChatGPT` is the design/output workspace.

---

## 1. Executive Decision

The first implementation step is **contract-first runtime construction**.

Before implementing subagents, Tool Search, GreenSkills, or advanced orchestration, GAIEP must establish a small immutable vocabulary that makes an agent execution:

- identifiable,
- bounded,
- reproducible,
- auditable,
- policy-constrained,
- resumable,
- and separable from provider/model implementation details.

The initial contract set is:

```text
AgentRun
WorkspaceScope
ContextManifest
ToolManifest
SkillManifest
MemoryManifest
Checkpoint
SubagentHandle
TrajectoryRecord
EvidenceRecord
TaskPolicy
ModelPolicy
EscalationPolicy
```

The runtime should then build its execution spine around these contracts.

---

## 2. Design Principles

### 2.1 Contracts describe facts; engines perform work

Contracts must not become service objects.

```text
contract  = immutable description of state / authority / identity
engine    = computation or orchestration
ledger    = persistence
adapter   = external integration
```

A contract must not secretly perform I/O, model calls, filesystem mutation, or policy evaluation.

### 2.2 Identity is immutable

The runtime must never rewrite the identity of a run after it starts.

Mutable observations belong in events and associated records.

This follows the existing GreenZ discipline used by certification records, research trials, windows, and immutable ledgers.

### 2.3 Authority only narrows downstream

A child cannot gain authority from its parent.

```text
child authority ⊆ parent authority
```

The same principle applies to:

- workspace scope,
- tools,
- network access,
- model policy,
- context visibility,
- budget,
- and approval authority.

### 2.4 Visibility is not permission

The runtime must preserve the distinction:

```text
visible != permitted != executable != promotion-authorized
```

A tool schema appearing in model context never constitutes permission to execute it.

### 2.5 Evidence is not hidden reasoning

Trajectory records capture observable runtime facts and artifacts, not hidden chain-of-thought.

### 2.6 Model identity belongs to the platform

GAIEP Runtime VNext must not create a second provider/model registry. Model selection is delegated to the existing `greenz-ai-platform` Gateway and certification boundary.

---

# 3. Contract Map

```text
                           +----------------+
                           |    AgentRun    |
                           +-------+--------+
                                   |
          +------------------------+------------------------+
          |                        |                        |
          v                        v                        v
 +----------------+       +----------------+       +----------------+
 | WorkspaceScope |       | TaskPolicy     |       | ModelPolicy    |
 +----------------+       +----------------+       +----------------+
          |                        |                        |
          +------------------------+------------------------+
                                   |
                                   v
                         +--------------------+
                         | ContextManifest    |
                         +--------------------+
                           /       |        \
                          v        v         v
                    ToolManifest SkillManifest MemoryManifest
                          |
                          v
                    +-------------+
                    |  Execution  |
                    +------+------+ 
                           |
              +------------+-------------+
              |                          |
              v                          v
       TrajectoryRecord             Checkpoint
              |
              v
       +-------------+
       | Evidence    |
       | Record      |
       +-------------+

SubagentHandle references another AgentRun while carrying a strictly reduced authority envelope.
EscalationPolicy controls model/provider escalation; it does not bypass certification.
```

---

# 4. AgentRun

## 4.1 Purpose

`AgentRun` is the immutable identity of one runtime execution.

It answers:

> What execution is this, what task/capability does it serve, who is its parent, what authority envelope was assigned, and which manifests define its environment?

It does **not** contain mutable turn-by-turn state.

## 4.2 Proposed shape

```python
@dataclass(frozen=True)
class AgentRun:
    run_id: str
    task_id: str
    capability: str
    parent_run_id: str | None
    workspace_scope_id: str
    context_manifest_id: str
    tool_manifest_id: str
    skill_manifest_id: str | None
    memory_manifest_id: str | None
    task_policy_id: str
    model_policy_id: str
    escalation_policy_id: str | None
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None
```

## 4.3 Invariants

- `run_id` is non-empty and unique.
- `task_id` is non-empty.
- `capability` must be a declared capability understood by the engineering runtime.
- `parent_run_id` is null only for a root run.
- Manifest IDs must resolve to the manifests used for the run.
- `started_at` is timezone-aware.
- `finished_at` is null while running and cannot precede `started_at`.
- A terminal run cannot return to a running state.
- A child run must reference its parent explicitly.

## 4.4 Status vocabulary

Prefer a closed enum:

```text
CREATED
RUNNING
WAITING
SUCCEEDED
FAILED
CANCELLED
TIMED_OUT
BLOCKED
```

Do not use free-form status strings.

---

# 5. WorkspaceScope

## 5.1 Purpose

Defines exactly where a run may read, write, execute, and potentially access the network.

The current design requires the Mac development model to keep the three source repositories read-only and the `ChatGPT` workspace writable.

```text
READ ONLY
  ~/greenz-ai-engineering
  ~/greenz-ai-platform
  ~/GreenZAlgo_V4

READ + WRITE
  ~/ChatGPT
```

## 5.2 Proposed shape

```python
@dataclass(frozen=True)
class WorkspaceScope:
    scope_id: str
    readonly_roots: tuple[str, ...]
    writable_roots: tuple[str, ...]
    executable_commands: tuple[str, ...]
    network_policy: NetworkPolicy
    environment_variables: tuple[str, ...]
```

## 5.3 Required invariants

1. A writable root cannot overlap a protected read-only source root.
2. Paths must be normalized before comparison.
3. A command is executable only if explicitly allowed.
4. Network policy is closed and explicit.
5. Secrets are never represented as values in this contract.
6. Child scope can only be equal to or narrower than parent scope.

## 5.4 Why this is a contract

The existing engineering lane already has path-level restrictions and forbidden sensitive paths. The runtime should make the scope a first-class object instead of allowing each runner to implement its own interpretation.

---

# 6. ContextManifest

## 6.1 Purpose

A `ContextManifest` records **what context was actually made available to a model call or runtime turn**.

The existing engineering context builder already establishes important provenance and hashing behavior. Runtime VNext should promote that concept into a first-class contract rather than replacing it with an opaque prompt string.

## 6.2 Proposed shape

```python
@dataclass(frozen=True)
class ContextManifest:
    manifest_id: str
    run_id: str
    schema_version: str
    instruction_refs: tuple[str, ...]
    task_refs: tuple[str, ...]
    project_instruction_refs: tuple[str, ...]
    skill_refs: tuple[str, ...]
    memory_refs: tuple[str, ...]
    source_refs: tuple[str, ...]
    tool_schema_refs: tuple[str, ...]
    prior_output_refs: tuple[str, ...]
    compression_refs: tuple[str, ...]
    input_token_estimate: int
    input_token_actual: int | None
    output_token_reserve: int
    context_hash: str
    created_at: datetime
```

## 6.3 Important distinction

The manifest records **references and accounting**, not necessarily the complete raw prompt.

The runtime may store the rendered prompt separately where policy permits.

## 6.4 Invariants

- Every reference identifies a concrete source/artifact.
- `context_hash` is deterministic over the canonical manifest representation.
- Token counts cannot be negative.
- `output_token_reserve` cannot be negative.
- A manifest cannot claim a tool schema that was not visible to the model.
- A memory reference is context, not authority.

---

# 7. ToolManifest

## 7.1 Purpose

`ToolManifest` defines the tool surface available to a particular run.

It does **not** itself authorize execution.

## 7.2 Proposed shape

```python
@dataclass(frozen=True)
class ToolManifest:
    manifest_id: str
    run_id: str
    tool_ids: tuple[str, ...]
    toolset_ids: tuple[str, ...]
    permission_classes: tuple[str, ...]
    network_policy: NetworkPolicy
    result_limits: tuple[ToolResultLimit, ...]
    audit_required: bool
    created_at: datetime
```

A future implementation should normalize the result-limit representation rather than using parallel tuples; the conceptual requirement is that every exposed tool has an explicit bound.

## 7.3 Tool state model

The runtime must distinguish:

```text
REGISTERED
    ↓
VISIBLE
    ↓
PERMITTED
    ↓
EXECUTABLE
    ↓
EXECUTED
```

A tool can be registered but unavailable to a run.

A tool can be visible but denied at execution time.

## 7.4 Invariants

- Every `tool_id` resolves in the Tool Registry.
- No manifest grants a permission class absent from the parent authority envelope.
- Tool result limits are finite unless an explicit bounded policy says otherwise.
- Network access is inherited from `WorkspaceScope` and policy; a tool cannot expand it.

---

# 8. SkillManifest

## 8.1 Purpose

A `SkillManifest` records which procedural skills were selected for the run.

GreenSkills are **procedural knowledge**, not permissions and not durable factual memory.

## 8.2 Proposed shape

```python
@dataclass(frozen=True)
class SkillManifest:
    manifest_id: str
    skill_refs: tuple[str, ...]
    selection_reason_refs: tuple[str, ...]
    prerequisite_refs: tuple[str, ...]
    validation_gate_refs: tuple[str, ...]
    version: str
    created_at: datetime
```

## 8.3 Skill contract

Each skill definition should eventually carry:

```text
skill_id
owner
version
applicability
prerequisites
allowed_toolsets
expected_outputs
validation_gates
evidence_requirements
approval_state
```

The manifest records the selected version, not an unversioned skill name.

## 8.4 Invariant

A skill cannot grant authority not already present in `ToolManifest`, `WorkspaceScope`, or policy.

---

# 9. MemoryManifest

## 9.1 Purpose

`MemoryManifest` records which durable memory/context references were supplied to a run.

The architectural distinction is strict:

```text
GreenMemory
  = durable facts, decisions, constraints, prior evidence

GreenSkills
  = reusable procedures
```

## 9.2 Proposed shape

```python
@dataclass(frozen=True)
class MemoryManifest:
    manifest_id: str
    memory_refs: tuple[str, ...]
    retrieval_query_hash: str | None
    retrieval_policy_id: str
    source_count: int
    created_at: datetime
```

## 9.3 Authority rule

A memory item is never authoritative merely because it was retrieved.

The authoritative source remains the repository, ledger, governed record, or source corpus that owns the fact.

---

# 10. TaskPolicy

## 10.1 Purpose

Defines what the run is trying to accomplish and the hard operational boundaries around it.

## 10.2 Proposed shape

```python
@dataclass(frozen=True)
class TaskPolicy:
    policy_id: str
    task_class: str
    allowed_operations: tuple[str, ...]
    forbidden_operations: tuple[str, ...]
    required_validation_gates: tuple[str, ...]
    approval_mode: ApprovalMode
    max_turns: int
    max_tool_calls: int
    max_child_runs: int
    created_at: datetime
```

## 10.3 Invariants

- Limits must be non-negative.
- Forbidden operations override allowed operations.
- Validation gates cannot be removed by a child.
- Production mutation is never implied by a generic engineering task policy.

---

# 11. ModelPolicy

## 11.1 Purpose

Defines the model-selection requirements without embedding provider implementation into the runtime.

## 11.2 Proposed shape

```python
@dataclass(frozen=True)
class ModelPolicy:
    policy_id: str
    capability: str
    required_certification: str | None
    preferred_tier: str | None
    allowed_deployments: tuple[str, ...]
    minimum_context_window: int | None
    max_output_tokens: int | None
    escalation_allowed: bool
    created_at: datetime
```

## 11.3 Critical rule

`ModelPolicy` describes eligibility.

The existing `greenz-ai-platform` Gateway remains responsible for actual provider/model selection and certification enforcement.

```text
GAIEP ModelPolicy
       |
       v
ReasoningRequest
       |
       v
GreenZ AI Platform Gateway
       |
       +--> Model Registry
       +--> Certification Gate
       +--> Provider Registry
       |
       v
Certified model deployment
```

There must be no second model-selection algorithm in GAIEP that can bypass this boundary.

---

# 12. EscalationPolicy

## 12.1 Purpose

Defines what happens when the primary execution fails validation or becomes otherwise ineligible for completion.

## 12.2 Proposed shape

```python
@dataclass(frozen=True)
class EscalationPolicy:
    policy_id: str
    enabled: bool
    trigger_conditions: tuple[str, ...]
    max_escalations: int
    allowed_model_policy_ids: tuple[str, ...]
    preserve_context: bool
    require_human_approval: bool
    created_at: datetime
```

## 12.3 Invariants

- Escalation never silently substitutes a model.
- Every escalation produces a trajectory event.
- The challenger remains subject to the same certification gate.
- An escalation cannot expand workspace/tool authority.
- Maximum escalation count is finite.

---

# 13. Checkpoint

## 13.1 Purpose

A checkpoint establishes a recoverable baseline before consequential mutation.

## 13.2 Proposed shape

```python
@dataclass(frozen=True)
class Checkpoint:
    checkpoint_id: str
    run_id: str
    task_id: str
    workspace_scope_id: str
    git_revision: str | None
    workspace_fingerprint: str
    created_at: datetime
    mutation_scope: tuple[str, ...]
```

## 13.3 Lifecycle

```text
Checkpoint
    |
    v
Mutation
    |
    v
Validation
   / \
PASS FAIL
 |     |
 v     v
Keep  Rollback
```

Rollback must itself be represented by observable trajectory events.

## 13.4 Invariants

- A checkpoint is immutable.
- It belongs to exactly one run.
- Its scope cannot exceed the run's workspace scope.
- A rollback cannot silently modify unrelated paths.

---

# 14. SubagentHandle

## 14.1 Purpose

A parent run needs a stable reference to a bounded child execution without embedding the child's mutable state into the parent.

## 14.2 Proposed shape

```python
@dataclass(frozen=True)
class SubagentHandle:
    handle_id: str
    parent_run_id: str
    child_run_id: str
    role: str
    goal: str
    authority_scope_id: str
    context_budget: int
    token_budget: int
    wall_clock_seconds: int
    max_depth: int
    approval_mode: ApprovalMode
    created_at: datetime
```

## 14.3 Authority invariant

For every child:

```text
child.workspace ⊆ parent.workspace
child.tools     ⊆ parent.tools
child.network  ⊆ parent.network
child.budget    ≤ parent.remaining_budget
child.depth     < parent.max_depth
```

The runtime must enforce these structurally, not merely document them.

## 14.4 Result rule

The child returns a bounded result/artifact reference.

The parent remains responsible for deciding whether that result is integrated.

---

# 15. TrajectoryRecord

## 15.1 Purpose

`TrajectoryRecord` is the observable event envelope for runtime execution.

It is deliberately **not** a hidden-reasoning log.

## 15.2 Proposed shape

```python
@dataclass(frozen=True)
class TrajectoryRecord:
    event_id: str
    run_id: str
    parent_event_id: str | None
    event_type: str
    occurred_at: datetime
    actor: str
    payload_ref: str | None
    artifact_refs: tuple[str, ...]
    outcome: str | None
```

## 15.3 Initial event vocabulary

```text
run.created
run.started
run.waiting
run.completed
run.failed
run.cancelled

context.selected
context.compressed
context.observed

model.requested
model.completed
model.failed
model.escalated

tool.visible
tool.denied
tool.call
tool.result
tool.failed

file.read
file.write

checkpoint.created
checkpoint.rollback

subagent.started
subagent.completed
subagent.failed

validation.started
validation.completed
validation.failed

evidence.created
disposition.finalized
```

The event vocabulary should eventually be a closed registry rather than free-form strings.

---

# 16. EvidenceRecord

## 16.1 Purpose

Evidence connects runtime activity to an externally reviewable artifact or result.

It is not the same thing as a trajectory event.

```text
TrajectoryRecord
    = what the runtime observed/did

EvidenceRecord
    = what can substantiate a conclusion or decision
```

## 16.2 Proposed shape

```python
@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    run_id: str
    task_id: str
    evidence_type: str
    artifact_refs: tuple[str, ...]
    source_event_ids: tuple[str, ...]
    validation_refs: tuple[str, ...]
    created_at: datetime
```

## 16.3 Rule

An evidence record cannot claim a validation result that has no corresponding validation event/artifact.

This follows the existing GreenZ preference for refusing records that cannot honestly substantiate what they claim.

---

# 17. Contract Relationships

```text
AgentRun
  |
  +---- WorkspaceScope
  |
  +---- TaskPolicy
  |
  +---- ModelPolicy
  |
  +---- EscalationPolicy
  |
  +---- ContextManifest
  |         |
  |         +---- SkillManifest
  |         +---- MemoryManifest
  |         +---- ToolManifest
  |
  +---- Checkpoint(s)
  |
  +---- SubagentHandle(s)
  |
  +---- TrajectoryRecord(s)
              |
              v
        EvidenceRecord(s)
```

The identity direction is intentionally one-way.

A child/event/evidence object references its parent identity rather than mutating the parent record.

---

# 18. Execution Spine

Once these contracts exist, the first runtime loop should be deliberately small.

```text
                         TASK
                          |
                          v
                   +-------------+
                   | AgentRun    |
                   +------+------+ 
                          |
          +---------------+----------------+
          |               |                |
          v               v                v
     WorkspaceScope   TaskPolicy      ModelPolicy
          |               |                |
          +---------------+----------------+
                          |
                          v
                  Context Engine
                          |
              +-----------+-----------+
              |           |           |
              v           v           v
           SELECT      BUDGET      COMPRESS
              \           |           /
               +----------+----------+
                          |
                          v
                  ContextManifest
                          |
                          v
                  Tool / Skill / Memory
                       Manifests
                          |
                          v
                    Model Gateway
                          |
                          v
                       MODEL
                          |
                  +-------+-------+
                  |               |
                  v               v
                TOOLS          OUTPUT
                  |               |
                  +-------+-------+
                          |
                          v
                     VALIDATION
                      /       \
                   PASS       FAIL
                    |            |
                    v            v
                 Evidence    Escalation
                    |            |
                    +-----+------+
                          |
                          v
                     Checkpoint /
                     Final State
                          |
                          v
                   Trajectory Ledger
```

`OBSERVE` is deliberately included in the Context Engine lifecycle even though its exact learning behavior is deferred. The runtime must record what happened before attempting to turn observations into durable memory or skills.

---

# 19. Contract Ownership

The contracts should not all live in one giant module.

Proposed eventual ownership inside `greenz-ai-engineering`:

```text
runtime/
├── agent/
│   └── contracts.py          AgentRun
├── workspace/
│   └── contracts.py          WorkspaceScope
├── context/
│   └── contracts.py          ContextManifest
├── tools/
│   └── contracts.py          ToolManifest
├── skills/
│   └── contracts.py          SkillManifest
├── memory/
│   └── contracts.py          MemoryManifest
├── policy/
│   ├── task.py               TaskPolicy
│   ├── model.py              ModelPolicy
│   └── escalation.py         EscalationPolicy
├── checkpoints/
│   └── contracts.py          Checkpoint
├── subagents/
│   └── contracts.py          SubagentHandle
├── trajectory/
│   └── contracts.py          TrajectoryRecord
└── evidence/
    └── contracts.py          EvidenceRecord
```

A common `runtime/contracts/` package is acceptable only if it remains a thin vocabulary package. It must not become a new `common.py`-style dumping ground.

This respects the existing GreenZ architectural rule that domain nouns and invariants have an explicit owner rather than accumulating in orchestration code.

---

# 20. Persistence Rules

Contracts are pure.

Persistence is separate.

```text
contracts/
     |
     v
engine / runtime
     |
     v
ledger adapter
```

The runtime should reuse the established immutable-ledger patterns where appropriate rather than creating an ad-hoc database layer in Phase 0.

Important properties:

- append-only for historical runtime events,
- immutable identity records,
- no overwrite of evidence,
- explicit IDs,
- deterministic serialization where hashes are involved,
- timezone-aware timestamps,
- malformed historical records fail closed rather than being silently normalized.

---

# 21. Hash / Reproducibility Rules

The runtime should adopt the existing GreenZ execution-fingerprint philosophy rather than inventing a weaker identity.

At minimum, future model execution evidence should be able to associate:

```text
provider
model
model version
digest / quantization where available
runtime version
temperature
seed
thinking mode
context window
max output tokens
```

The existing platform already has `ExecutionFingerprint` precisely because model tags alone are not sufficient historical identity.

GAIEP should reference that platform identity rather than creating a competing fingerprint format.

---

# 22. Security and Governance Rules

The contracts must enforce the following architectural rules:

### Rule 1 — No implicit filesystem authority

A path outside `WorkspaceScope` is inaccessible regardless of model instruction.

### Rule 2 — No implicit tool authority

A tool outside `ToolManifest` is unavailable.

### Rule 3 — No authority inheritance upward

A child cannot grant its parent new permissions.

### Rule 4 — No silent model substitution

Escalation is an explicit trajectory event and remains behind the platform certification gate.

### Rule 5 — No hidden promotion

Runtime success does not equal certification or production promotion.

### Rule 6 — No domain leakage into the generic platform

Trading/research semantics remain in `GreenZAlgo_V4`; generic runtime mechanisms belong in GAIEP/platform according to ownership.

### Rule 7 — No memory-as-truth shortcut

Retrieved memory cannot override the authoritative source.

### Rule 8 — No contract mutation

Historical manifests and run identity are immutable.

---

# 23. Phase-0 Acceptance Tests

Phase 0 is complete only when the following are executable tests.

## AgentRun

- rejects empty IDs;
- rejects naive timestamps;
- rejects invalid lifecycle transitions;
- preserves immutable identity;
- requires parent identity for child runs.

## WorkspaceScope

- rejects overlapping writable/read-only roots;
- rejects traversal outside declared roots;
- rejects unlisted commands;
- verifies child scope cannot exceed parent scope.

## ContextManifest

- canonical representation produces deterministic hash;
- token values reject negatives;
- all referenced components resolve;
- tool schemas in the manifest are a subset of the ToolManifest.

## ToolManifest

- every tool resolves to a registry entry;
- permissions cannot exceed parent scope;
- result limits are enforced structurally.

## SkillManifest

- skill versions are explicit;
- selected skills cannot expand tool authority;
- prerequisites are represented.

## MemoryManifest

- references are provenance-bearing;
- memory is not treated as authority by the contract.

## Checkpoint

- baseline identity is immutable;
- checkpoint scope is bounded by workspace scope;
- rollback emits an event.

## SubagentHandle

- child authority is a subset of parent authority;
- depth is bounded;
- budgets are bounded;
- child completion cannot mutate parent state directly.

## TrajectoryRecord

- event IDs are unique;
- timestamps are timezone-aware;
- event type belongs to the closed vocabulary;
- historical events are append-only.

## EvidenceRecord

- source events exist;
- validation references exist;
- artifacts are immutable references.

---

# 24. What Phase 0 Explicitly Does NOT Build

The following are intentionally outside the first contract implementation:

```text
NO subagent scheduler
NO Tool Search
NO MCP orchestration
NO GreenSkills runtime
NO semantic memory retrieval engine
NO autonomous long-running agent
NO new model/provider abstraction
NO second AI Gateway
NO automatic production deployment
NO trading-domain AI logic in greenz-ai-platform
```

The purpose is to prevent the runtime from becoming a second architecture before its vocabulary is governed.

---

# 25. Phase-1 Boundary After Contracts

Once Phase 0 passes, the next implementation boundary is:

```text
Context Engine
    |
    +-- selector
    +-- budget
    +-- compressor
    +-- sanitization
    +-- manifest builder
```

The current `runner/context.py` should be migrated incrementally into this boundary.

The four explicit lifecycle operations are:

```text
SELECT
  -> determine relevant context

BUDGET
  -> determine how much can fit

COMPRESS
  -> reduce context without silently changing authority

OBSERVE
  -> record what context was actually consumed and what happened during the turn
```

The existing context builder remains the initial implementation source. The migration must preserve current behavior before introducing new retrieval or compression strategies.

---

# 26. Recommended Implementation Sequence

```text
STEP 1
  contracts + enums + validation

STEP 2
  contract fitness tests

STEP 3
  serialization / immutable persistence adapters

STEP 4
  AgentRun creation + lifecycle

STEP 5
  WorkspaceScope enforcement

STEP 6
  ContextManifest adapter around current context builder

STEP 7
  Trajectory event emission

STEP 8
  Checkpoint manager

STEP 9
  ModelPolicy adapter into existing Gateway

STEP 10
  only then begin subagent runtime
```

This sequence deliberately puts **SubagentHandle after the authority and evidence substrate exists**.

---

# 27. Final Contract Principle

The runtime should make this statement mechanically true:

> **An agent is not an unconstrained model call. It is an immutable run identity operating inside an explicit authority envelope, using a recorded context, bounded tools, governed model selection, observable events, recoverable mutation points, and evidence that can be reviewed independently of the model's hidden reasoning.**

That is the contract foundation for GAIEP Runtime VNext.
