# GAIEP Subagent Runtime — Bounded Architecture & Governance Design

**Status:** Proposal / architecture specification
**Date:** 2026-08-21
**Scope:** Bounded subagent runtime for GAIEP Runtime VNext

> Subagents are bounded execution workers created under an existing AgentRun. They do not become independent principals, acquire authority, or create unrestricted recursive agents. Their purpose is decomposition and parallel/bounded execution while preserving GreenZ policy, context, skills, model certification, checkpoints, and evidence.

---

# 1. Executive Decision

GAIEP should introduce subagents only after the AgentRun, Context Engine, and GreenSkills contracts are established.

A subagent is:

```text
bounded child execution
        of
an existing AgentRun
```

It is **not**:

```text
an independent autonomous agent
an unrestricted process
an authority holder
an independent memory owner
an independent model router
```

The parent AgentRun remains responsible for the overall task and governance.

---

# 2. Why Subagents

Subagents become useful when a task naturally decomposes into independently bounded work.

Examples:

```text
Review a large change
   ├── inspect architecture
   ├── inspect implementation
   ├── inspect tests
   └── inspect security

Research campaign
   ├── data-quality analysis
   ├── feature analysis
   ├── strategy analysis
   └── evidence synthesis
```

The benefit is decomposition, specialization, isolation, and potentially parallel execution.

The risk is uncontrolled complexity:

```text
parent
  -> child
      -> child
          -> child
              -> runaway cost / authority / state
```

Therefore the runtime must impose explicit bounds.

---

# 3. Core Invariant

A child may never have more authority than its parent.

Formally:

```text
ChildAuthority ⊆ ParentAuthority
```

and, more specifically:

```text
ChildWorkspace ⊆ ParentWorkspace
ChildTools     ⊆ ParentTools
ChildSkills    ⊆ ParentSkills
ChildMemory    ⊆ ParentMemoryPolicy
ChildBudget    ≤ ParentRemainingBudget
ChildDepth     < ParentMaxDepth
```

This is the foundational subagent safety invariant.

---

# 4. SubagentHandle

The Phase-0 contract already includes:

```python
@dataclass(frozen=True)
class SubagentHandle:
    subagent_id: str
    parent_run_id: str
    task_ref: str
    workspace_scope_ref: str
    context_manifest_ref: str
    skill_manifest_ref: str
    model_policy_ref: str
    status: str
    created_at: datetime
```

This is the durable identity of the child execution.

---

# 5. Parent / Child Relationship

```text
                         AgentRun
                            |
                +-----------+-----------+
                |           |           |
                v           v           v
             Child A     Child B     Child C
                |           |           |
                v           v           v
             bounded     bounded     bounded
             execution   execution   execution
                |           |           |
                +-----------+-----------+
                            |
                            v
                    Parent aggregation
                            |
                            v
                       Validation
                            |
                            v
                        Evidence
```

The parent remains the authoritative orchestrator.

---

# 6. Subagent Lifecycle

```text
REQUESTED
   ↓
AUTHORIZED
   ↓
PLANNED
   ↓
CONTEXT_READY
   ↓
RUNNING
   ↓
CHECKPOINTED
   ↓
VALIDATING
   ↓
COMPLETED / FAILED / CANCELLED
   ↓
AGGREGATED
```

A subagent cannot jump directly from requested to unrestricted execution.

---

# 7. Spawn Contract

The parent should create a child through a controlled request:

```python
@dataclass(frozen=True)
class SubagentRequest:
    parent_run_id: str
    task_spec_ref: str
    skill_ref: str | None
    context_refs: tuple[str, ...]
    workspace_scope_ref: str
    toolset_refs: tuple[str, ...]
    model_policy_ref: str
    max_depth: int
    max_steps: int
    timeout_seconds: int
    token_budget: int
    approval_required: bool
```

The runtime validates the request before constructing a child.

---

# 8. Spawn Authorization

The runtime must evaluate:

```text
ParentTaskPolicy
       ∩
ParentWorkspaceScope
       ∩
ParentToolManifest
       ∩
ParentSkillManifest
       ∩
ParentModelPolicy
       ∩
GlobalRuntimePolicy
```

Only then is the child created.

The child receives a **derived policy**, never a fresh unrestricted policy.

---

# 9. No Recursive Freedom

Initial GAIEP policy:

```text
subagent cannot spawn another subagent
```

unless an explicit future policy enables bounded depth.

Recommended Phase-1 rule:

```text
max_depth = 1
```

Meaning:

```text
AgentRun
  └── Subagent
```

No:

```text
AgentRun
  └── Subagent
       └── Subagent
            └── ...
```

Recursive subagents can be evaluated later after the base runtime has evidence.

---

# 10. Why Depth-1 First

Depth-1 provides most useful decomposition patterns without introducing recursive orchestration complexity.

It makes:

```text
cost
latency
failure
authority
context
trajectory
```

easier to attribute.

The architecture should support future depth, but the first implementation should not activate it.

---

# 11. Subagent Context

A child receives a derived ContextManifest.

```text
Parent ContextManifest
          |
          v
Child Context Selection
          |
          v
Child ContextManifest
```

The child does not automatically inherit the parent's entire context.

This is critical for:

- token efficiency;
- information isolation;
- provenance;
- task focus;
- reducing accidental prompt contamination.

---

# 12. Context Derivation Rules

A child context may contain:

```text
parent task subset
child task specification
required project instructions
selected source references
selected skill references
permitted tool schemas
relevant parent artifacts
```

It should not automatically receive:

```text
all parent conversation
all parent memory
all parent tools
all parent secrets
all parent source tree
```

Inheritance is explicit, not implicit.

---

# 13. Child Workspace Scope

The child workspace must be derived from the parent.

Example:

```text
Parent:
~/ChatGPT/GAIEP

Child:
~/ChatGPT/GAIEP/workspaces/run-123/child-01
```

For read-only analysis, the child may receive a read-only source scope.

For implementation, use a bounded workspace/branch/worktree where practical.

The child must not escape the parent scope.

---

# 14. Child Tool Policy

Tools are inherited by intersection.

```text
ChildTools =
    RequestedTools
    ∩ ParentAllowedTools
    ∩ GlobalAllowedTools
```

A child cannot request a tool that the parent does not possess.

A skill can further restrict the set.

---

# 15. Child Skill Policy

The child should normally receive exactly one primary skill.

Example:

```text
Parent task: review pull request

Child A: python-code-review
Child B: security-review
Child C: test-review
```

This keeps child scope narrow.

The parent can aggregate the resulting evidence.

---

# 16. Model Policy

A child may use a model allowed by the parent's ModelPolicy.

The child must not:

- install an unapproved model;
- bypass certification;
- silently switch provider;
- change model policy;
- create a new provider route.

This is particularly important for the current multi-model Mac strategy.

---

# 17. Multi-Model Subagents

A parent can eventually decompose work by skill/model suitability:

```text
Parent
  |
  +-- implementation → strong coding model
  |
  +-- test generation → cheaper certified model
  |
  +-- review → reviewer model
  |
  +-- architecture → strongest available model
```

But selection must be evidence-driven through ModelPolicy and skill certification.

Do not encode a static model-size hierarchy.

---

# 18. Subagent Budget

Every child receives a hard resource envelope.

Minimum controls:

```text
token budget
step budget
timeout
tool-call budget
context budget
memory/event budget
```

The child cannot exceed the parent's remaining aggregate budget.

Conceptually:

```text
ParentBudgetRemaining
        |
        +--> Child A allocation
        +--> Child B allocation
        +--> Child C allocation
```

The parent must reserve enough budget for aggregation and validation.

---

# 19. Cost Guard

A parent should not be allowed to spawn an arbitrary number of children.

Initial controls:

```text
max_children_per_run
max_total_child_tokens
max_total_child_tool_calls
max_total_child_runtime
```

Recommended initial defaults should be configured rather than hard-coded and tuned from measurements.

---

# 20. Parallelism

Parallel child execution is useful when tasks are independent.

Example:

```text
               Parent
                  |
        +---------+---------+
        |         |         |
        v         v         v
      Child A   Child B   Child C
        |         |         |
        +---------+---------+
                  |
                  v
              Aggregator
```

The runtime must not parallelize tasks with known write conflicts without an isolation strategy.

---

# 21. Workspace Isolation

For independent implementation children:

```text
Parent branch
     |
     +-- child worktree A
     +-- child worktree B
     +-- child worktree C
```

Each child produces artifacts/patches rather than blindly writing to the same working tree.

This is safer than concurrent writes to one directory.

---

# 22. Read-Only Analysis Children

The safest initial subagent class is read-only analysis.

Examples:

```text
code review
architecture analysis
research decomposition
test inspection
security inspection
```

These children can share read-only source snapshots without write conflicts.

This should be the first implementation target.

---

# 23. Write-Capable Children

Write-capable children require stronger controls.

Recommended Phase-1 rule:

```text
child writes only to isolated workspace
```

The parent later decides whether to apply/merge the resulting change.

This creates:

```text
Child writes
    ↓
Artifact / patch
    ↓
Parent validation
    ↓
Governance
    ↓
Apply / reject
```

The child does not directly mutate the parent's authoritative workspace.

---

# 24. Checkpoints

Subagents should checkpoint at meaningful boundaries.

Example:

```text
child started
     ↓
context prepared
     ↓
step 1 complete
     ↓
artifact created
     ↓
validation complete
     ↓
final result
```

Checkpoints support:

- recovery;
- debugging;
- cancellation;
- audit;
- reproducibility.

---

# 25. Cancellation

The parent must be able to cancel a child.

Cancellation should propagate:

```text
Parent CANCEL
      |
      +--> Child A CANCEL
      +--> Child B CANCEL
      +--> Child C CANCEL
```

The runtime should attempt graceful termination and then enforce the timeout boundary.

---

# 26. Failure Isolation

A child failure should not automatically fail every sibling.

```text
Child A → PASS
Child B → FAIL
Child C → PASS
        |
        v
Parent aggregation
        |
        v
Policy decides
```

Possible parent outcomes:

```text
continue
retry child
replace child
escalate
human review
fail overall task
```

The parent remains responsible for that decision.

---

# 27. No Silent Substitution

If a child fails and another model/skill is used as a substitute, the event must record:

```text
failed child
failure reason
replacement policy
replacement model/skill
parent decision
```

This follows the existing GreenZ principle that failover must be visible rather than silent.

---

# 28. Child Result Contract

Conceptual:

```python
@dataclass(frozen=True)
class SubagentResult:
    subagent_id: str
    status: SubagentStatus
    artifact_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    validation_refs: tuple[str, ...]
    context_manifest_ref: str
    skill_manifest_ref: str
    model_execution_ref: str
    failure_refs: tuple[str, ...]
    resource_usage_ref: str
```

The result should reference artifacts/evidence rather than copying arbitrary large payloads into the parent event.

---

# 29. Parent Aggregation

Aggregation is a separate stage.

```text
Child results
    |
    v
Evidence normalization
    |
    v
Conflict detection
    |
    v
Parent synthesis
    |
    v
Validation
    |
    v
Governance
```

The parent should not simply concatenate child outputs.

---

# 30. Conflict Handling

If children disagree:

```text
Child A → conclusion X
Child B → conclusion Y
```

the aggregator should produce an explicit disagreement record.

Possible actions:

```text
request evidence
run targeted challenger
escalate model
human review
reject unsupported conclusion
```

Disagreement should be treated as evidence, not hidden.

---

# 31. Dual-Model Pattern

The earlier dual-model disagreement idea fits naturally here.

```text
              Task
               |
        +------+------+
        |             |
        v             v
     Model A       Model B
        |             |
        v             v
      Result A      Result B
        |             |
        +------+------+
               |
               v
         Disagreement
           Analyzer
               |
        +------+------+
        |             |
      agree       disagree
        |             |
        v             v
     accept       escalate
```

This should be an optional bounded pattern, not the default for every task, because it doubles model work.

---

# 32. Subagent Memory

A child does not automatically create durable memory.

Its observations become:

```text
Trajectory / Evidence
        |
        v
Memory candidate
        |
        v
Governance
```

The child cannot directly mutate GreenMemory as a side effect of execution.

---

# 33. Subagent Skills

Each child should normally have:

```text
one primary SkillManifest
```

Optional supporting skills can be allowed later.

This avoids creating a child with an ambiguous procedural scope.

---

# 34. Context Isolation

Children should receive only task-relevant context.

For example:

```text
Parent context:
  architecture + implementation + tests + history + research notes

Security child:
  security task + relevant source + security skill + test evidence
```

This improves both safety and model efficiency.

---

# 35. Subagent Event Model

Emit events such as:

```text
subagent.requested
subagent.authorized
subagent.started
subagent.context_ready
subagent.step_started
subagent.step_completed
subagent.checkpointed
subagent.tool_called
subagent.validation_started
subagent.validation_completed
subagent.failed
subagent.cancelled
subagent.completed
subagent.aggregated
```

All events carry:

```text
run_id
subagent_id
parent_run_id
sequence number
timestamp
```

---

# 36. Trajectory Relationship

```text
AgentRun
  |
  +-- parent trajectory
  |
  +-- Child A trajectory
  |
  +-- Child B trajectory
  |
  +-- Child C trajectory
  |
  +-- aggregation trajectory
```

The system should be able to reconstruct:

```text
why was child created?
what context did it receive?
what skill did it execute?
what model ran it?
what tools did it use?
what did it produce?
what validation occurred?
why did the parent accept/reject it?
```

---

# 37. Subagent Runtime API

Conceptual API:

```python
class SubagentRuntime:
    def spawn(self, request: SubagentRequest) -> SubagentHandle: ...
    def start(self, handle: SubagentHandle) -> None: ...
    def checkpoint(self, handle: SubagentHandle) -> None: ...
    def cancel(self, handle: SubagentHandle) -> None: ...
    def result(self, handle: SubagentHandle) -> SubagentResult: ...
```

The public interface should remain small.

Orchestration complexity should live behind policy-aware services.

---

# 38. Execution State Machine

```text
REQUESTED
   |
   v
AUTHORIZED --X--> DENIED
   |
   v
PLANNED
   |
   v
CONTEXT_READY
   |
   v
RUNNING
   |
   +----> CHECKPOINTED ----+
   |                       |
   |                       v
   |                    RUNNING
   |
   +----> FAILED
   |
   +----> CANCELLED
   |
   v
VALIDATING
   |
   +----> FAILED
   |
   v
COMPLETED
```

State transitions should be explicit and validated.

---

# 39. Runtime Safety Limits

Minimum initial limits:

```text
max_children = configurable
max_depth = 1
max_steps_per_child = configurable
max_tool_calls_per_child = configurable
max_tokens_per_child = configurable
max_runtime_per_child = configurable
max_total_child_budget = configurable
```

Every limit should appear in the execution record.

---

# 40. Observability / Metrics

Measure:

```text
children per run
child success rate
child failure rate
child cancellation rate
child retry rate
child latency
child token usage
child tool calls
child context size
child validation pass rate
aggregation conflicts
escalation rate
```

Derived metrics:

```text
successful work per child token
successful work per child second
parallelism benefit
child overhead
```

This lets us determine whether subagents actually improve GAIEP rather than merely increasing complexity.

---

# 41. Parallelism Efficiency

For independent tasks:

```text
serial latency ≈ A + B + C
parallel latency ≈ max(A,B,C) + aggregation
```

But the runtime must include:

```text
spawn overhead
context preparation
model contention
Mac memory pressure
aggregation
validation
```

Given current Mac memory constraints, parallel local model execution must be conservative.

The runtime should support concurrency limits and model resource reservations.

---

# 42. Mac Constraint

The current development environment has demonstrated memory sensitivity with large local models.

Therefore GAIEP should not assume:

```text
3 children = 3 independent model processes
```

If all children invoke a 27B-class local deployment concurrently, memory pressure can become the dominant failure mode.

Initial local policy should therefore support:

```text
max_concurrent_local_model_runs = configurable
model residency awareness = required before aggressive parallelism
```

Subagent parallelism must not be allowed to create avoidable model OOM/crash risk.

---

# 43. API / Remote Model Children

Remote/API models may have different resource characteristics.

The architecture therefore keeps:

```text
Subagent policy
     |
     v
ModelPolicy
     |
     v
Gateway
```

The subagent runtime does not assume local execution.

This supports future larger AI server deployment without changing subagent contracts.

---

# 44. Write Conflict Strategy

Three levels:

### Level 1 — Read-only

Preferred first implementation.

### Level 2 — Isolated writes

Child writes to its own worktree/workspace.

### Level 3 — Shared writes

Do not support initially.

Shared concurrent mutation introduces difficult race, provenance, rollback, and validation problems.

---

# 45. Parent Merge Policy

For implementation children:

```text
Child
  ↓
Patch/artifact
  ↓
Parent review
  ↓
Tests
  ↓
Policy check
  ↓
Apply/merge
```

The child cannot directly declare its own patch production-ready.

---

# 46. Human-in-the-Loop

Human intervention may occur at:

```text
before spawn
before high-risk tool
after child result
before parent merge
before promotion
```

The runtime should represent approval as an explicit event/reference rather than relying on an informal UI state.

---

# 47. Subagent Security Tests

Required tests:

```text
SA-SEC-001 child requests parent-forbidden tool
SA-SEC-002 child escapes workspace
SA-SEC-003 child attempts protected file access
SA-SEC-004 child attempts unauthorized model
SA-SEC-005 child attempts second-level spawn
SA-SEC-006 child exceeds token budget
SA-SEC-007 child exceeds timeout
SA-SEC-008 child bypasses validation
SA-SEC-009 child writes outside isolated workspace
SA-SEC-010 child attempts memory mutation
```

All should fail closed.

---

# 48. Subagent Functional Tests

```text
SA-FN-001 spawn read-only child
SA-FN-002 child receives derived context
SA-FN-003 child executes selected skill
SA-FN-004 child emits evidence
SA-FN-005 child checkpoint works
SA-FN-006 child cancellation works
SA-FN-007 child failure isolated
SA-FN-008 parent aggregates results
SA-FN-009 disagreement recorded
SA-FN-010 child resource usage recorded
```

---

# 49. Integration Tests

Test the complete chain:

```text
AgentRun
  ↓
Skill selection
  ↓
Subagent authorization
  ↓
Context Engine
  ↓
Gateway
  ↓
Tool execution
  ↓
Validation
  ↓
Evidence
  ↓
Parent aggregation
```

This should be tested first with read-only analysis children.

---

# 50. No Hidden Agent State

Subagent state should be persisted through explicit runtime state/events.

Do not rely on:

```text
Python process memory
implicit conversation history
undocumented global variables
```

A child should be restartable or at least diagnosable from durable state.

---

# 51. Checkpoint / Recovery Strategy

At minimum checkpoint:

```text
spawn authorization
context completion
step boundaries
major artifacts
validation completion
final result
```

Future runtime can resume from a checkpoint if the underlying model/tool execution is safely repeatable.

---

# 52. Initial Subagent Patterns

Recommended first patterns:

## Pattern A — Parallel review

```text
Parent review
  ├── correctness reviewer
  ├── security reviewer
  └── test reviewer
```

## Pattern B — Research decomposition

```text
Research task
  ├── data analysis
  ├── literature/evidence analysis
  └── alternative hypothesis analysis
```

## Pattern C — Challenger

```text
Primary result
       |
       v
Independent challenger
       |
       v
Agreement/disagreement
```

Do not begin with recursive planner swarms.

---

# 53. Initial Non-Goals

Do not implement initially:

```text
recursive subagents
unlimited parallelism
autonomous agent swarms
shared mutable workspaces
autonomous production deployment
subagents that alter policy
subagents that alter skills
subagents that alter memory directly
hidden long-term child identity
independent provider management
```

---

# 54. Implementation Package Structure

Proposed:

```text
runtime/subagents/
├── __init__.py
├── contracts.py
├── policy.py
├── runtime.py
├── lifecycle.py
├── context.py
├── resources.py
├── scheduler.py
├── checkpoint.py
├── aggregation.py
├── errors.py
└── adapters/
```

Tests:

```text
tests/runtime/subagents/
├── test_contracts.py
├── test_policy.py
├── test_lifecycle.py
├── test_context.py
├── test_resources.py
├── test_scheduler.py
├── test_checkpoint.py
├── test_aggregation.py
└── test_security.py
```

---

# 55. Phase-1 Implementation Sequence

```text
1. Contracts
      ↓
2. Derived-policy calculator
      ↓
3. Depth-1 enforcement
      ↓
4. Read-only child execution
      ↓
5. Child ContextManifest
      ↓
6. Resource budgets
      ↓
7. Checkpoints/events
      ↓
8. Result/evidence contract
      ↓
9. Parent aggregation
      ↓
10. Security tests
      ↓
11. Certification/integration tests
      ↓
12. Isolated write children
```

This order keeps the first implementation narrow and observable.

---

# 56. Exit Criteria

Subagent Runtime Phase 1 is complete only when:

```text
[ ] child authority is provably subset of parent authority
[ ] depth-1 limit enforced
[ ] child budget cannot exceed parent allocation
[ ] child context is explicitly derived
[ ] child tools are policy-intersected
[ ] child skill is explicit
[ ] model remains Gateway-controlled
[ ] read-only child execution works
[ ] child result is evidence-backed
[ ] cancellation works
[ ] checkpointing works
[ ] failure isolation works
[ ] aggregation works
[ ] security tests pass
[ ] Mac concurrency limits are enforced
[ ] no uncontrolled recursion exists
```

---

# 57. Strategic Role in GAIEP

The Subagent Runtime completes the basic execution model:

```text
AgentRun
   |
   +--> Context Engine
   |
   +--> GreenSkills
   |
   +--> Tool Policy
   |
   +--> Model Gateway
   |
   +--> Subagents
   |
   +--> Checkpoints
   |
   +--> Evidence
   |
   +--> Governance
```

The runtime is therefore becoming a **governed execution substrate**, not merely an LLM wrapper.

---

# 58. Final Architecture Principle

The correct GAIEP model is:

> **Subagents provide bounded decomposition; GreenSkills provide procedure; Context Engine controls information exposure; Tool Policy controls authority; Model Gateway controls certified execution; checkpoints provide recoverability; evidence provides observability; and Governance controls acceptance and promotion.**

The subagent is powerful precisely because it is constrained.
