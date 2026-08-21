# GAIEP GreenSkills — Architecture & Governance Design

**Status:** Proposal / architecture specification
**Date:** 2026-08-21
**Scope:** GreenSkills layer for GAIEP Runtime VNext

> GreenSkills are reusable, versioned procedures for performing classes of work. They are not model prompts alone, not durable memory, and not permissions. A skill may describe how to use an allowed capability, but it cannot grant authority that the runtime policy does not already provide.

---

# 1. Executive Decision

GreenSkills should become a first-class GAIEP runtime primitive with four strict boundaries:

```text
GreenSkills
  = HOW to perform work

GreenMemory
  = WHAT we know / observed / decided

Tool Policy
  = WHAT the agent is allowed to do

Context Engine
  = WHAT information the agent sees

Model Gateway
  = WHICH certified model executes

Governance
  = WHETHER the result may be accepted/promoted
```

This separation is foundational.

A skill must never be able to bypass:

- WorkspaceScope;
- ToolManifest;
- TaskPolicy;
- ModelPolicy;
- certification;
- validation gates;
- promotion governance.

---

# 2. Why GreenSkills

The current engineering workflow contains repeated procedural knowledge:

```text
implementation workflow
refactor workflow
review workflow
review-audit workflow
testing workflow
validation workflow
certification workflow
research-analysis workflow
```

Today such knowledge can become scattered across:

- prompts;
- scripts;
- task-specific instructions;
- model-specific instructions;
- human memory;
- repository documentation.

GreenSkills provide a governed abstraction for reusable procedure without turning procedures into hidden runtime logic.

---

# 3. Skill Definition

A GreenSkill should answer:

> Given a permitted task class and authority envelope, what sequence of actions, checks, artifacts, and validation gates should be followed?

Conceptually:

```text
Skill
  |
  +-- Applicability
  +-- Preconditions
  +-- Procedure
  +-- Allowed toolsets
  +-- Expected artifacts
  +-- Validation gates
  +-- Evidence requirements
  +-- Failure handling
  +-- Version
  +-- Owner
```

The skill is a **procedure specification**, not an autonomous agent.

---

# 4. Proposed SkillManifest

The Phase-0 contract already defines:

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

GreenSkills provide the definitions referenced by that manifest.

The manifest records what was selected for a particular run.

The skill definition remains separately versioned.

---

# 5. Skill Definition Contract

Proposed logical contract:

```python
@dataclass(frozen=True)
class GreenSkill:
    skill_id: str
    name: str
    version: str
    owner: str
    description: str
    applicability: SkillApplicability
    prerequisites: tuple[SkillPrerequisite, ...]
    procedure: tuple[SkillStep, ...]
    allowed_toolsets: tuple[str, ...]
    expected_artifacts: tuple[ArtifactRequirement, ...]
    validation_gates: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    failure_policy: FailurePolicy
    approval_state: SkillApprovalState
```

The implementation may split this across modules, but these concepts should remain explicit.

---

# 6. Skill Lifecycle

```text
DRAFT
  ↓
REVIEW
  ↓
VALIDATED
  ↓
APPROVED
  ↓
ACTIVE
  ↓
DEPRECATED
  ↓
RETIRED
```

Only `ACTIVE` skills may be automatically selected for normal runtime execution.

A deprecated skill may remain available for historical reproducibility but should not be selected for new work without explicit policy.

---

# 7. Skill Versioning

Skills must be immutable by version.

```text
coding-review@1.0
coding-review@1.1
coding-review@2.0
```

A change to any of the following should normally create a new version:

- procedure;
- required validation;
- allowed toolset;
- artifact contract;
- evidence requirement;
- applicability rules.

Do not silently mutate an active skill definition.

This is essential for reproducing historical agent runs.

---

# 8. Applicability

Skill selection should be deterministic initially.

A skill can declare applicability conditions such as:

```text
capability = CODING
workflow = REVIEW
language = Python
repository_class = GreenZ engineering
risk_level = engineering
```

The selection engine should evaluate:

```text
task metadata
capability
repository/project metadata
policy
skill status
prerequisites
```

Semantic skill discovery can be added later.

---

# 9. Skill Preconditions

Before a skill can start, the runtime verifies prerequisites.

Examples:

```text
required repository state exists
required task metadata exists
required test command available
required source files accessible
required tools present
required policy permits the workflow
```

If prerequisites fail:

```text
SkillBlocked
```

The runtime should not improvise an alternative procedure merely because a skill cannot start.

---

# 10. Skill Procedure Model

A skill procedure should be a bounded sequence of declarative steps.

Example:

```yaml
skill_id: python-implementation
version: 1.0
steps:
  - inspect_task
  - inspect_relevant_files
  - identify_interfaces
  - implement_change
  - run_formatter
  - run_type_checks
  - run_tests
  - inspect_diff
  - produce_evidence
```

A step can reference an approved tool capability, but the skill does not itself execute arbitrary commands.

---

# 11. Step Contract

Conceptual:

```python
@dataclass(frozen=True)
class SkillStep:
    step_id: str
    purpose: str
    required: bool
    allowed_toolsets: tuple[str, ...]
    input_refs: tuple[str, ...]
    output_artifacts: tuple[str, ...]
    validation_refs: tuple[str, ...]
    max_attempts: int
```

Each step should be:

- bounded;
- observable;
- attributable;
- testable.

---

# 12. Skills Cannot Grant Authority

This is a hard invariant.

```text
Skill
  |
  +--> requests tool capability
  |
  v
ToolManifest / Policy
  |
  +--> permitted
  |
  +--> denied
```

For example, a skill may state:

```text
run pytest
```

but the skill does not automatically gain shell access.

The actual command must be permitted by the run's existing execution policy.

Likewise:

```text
Skill says: modify source file
```

does not override:

```text
WorkspaceScope = read-only
```

---

# 13. Skills and Context Engine

A skill can contribute procedural context.

The Context Engine decides what portion is actually supplied to the model.

```text
GreenSkill
     |
     v
SkillManifest
     |
     v
Context Engine SELECT
     |
     v
ContextManifest
     |
     v
Model
```

Therefore:

```text
Skill definition != model prompt
```

This allows the same skill to work with multiple certified models.

---

# 14. Skills and Models

Skills must remain model-neutral wherever possible.

Avoid:

```text
skill = Qwen-specific prompt
```

Prefer:

```text
skill = engineering procedure
model adapter = model-specific rendering constraints
```

If a model genuinely requires a special instruction, that should be represented as an adapter/renderer concern rather than changing the underlying procedural skill.

This is important for the current multi-model GAIEP strategy on the Mac.

---

# 15. Skills and Toolsets

Tools should be grouped into governed toolsets.

Example:

```text
READ_SOURCE
WRITE_WORKSPACE
RUN_TESTS
RUN_LINT
RUN_TYPECHECK
GIT_READ
GIT_WRITE
WEB_RESEARCH
```

A skill declares which toolsets it may need.

The runtime intersects:

```text
skill allowed toolsets
        ∩
run ToolManifest
        ∩
WorkspaceScope / policy
```

Only the intersection is available.

---

# 16. Skills and GreenMemory

GreenMemory should record durable outcomes such as:

```text
skill worked successfully for task class X
known failure condition
validated implementation convention
human-approved decision
observed recurring correction
```

But memory must not silently modify a skill.

The relationship is:

```text
Skill execution
      |
      v
Observation / Evidence
      |
      v
GreenMemory candidate
      |
      v
Governed review
      |
      +--> memory update
      |
      +--> skill improvement candidate
```

Automatic mutation of active skills from memory is prohibited in the initial design.

---

# 17. Skills and Evidence

A skill should define expected evidence.

For Python implementation:

```text
changed files
formatter result
type-check result
test result
diff summary
validation result
```

For review:

```text
review findings
severity
file/line references
validation evidence
```

The runtime produces evidence records from actual artifacts/events.

A skill cannot declare success merely because the model says it succeeded.

---

# 18. Skill Success Contract

A skill execution should have:

```text
procedure status
required steps completed
required artifacts present
required validations passed
failure conditions resolved
```

Conceptually:

```python
@dataclass(frozen=True)
class SkillExecutionResult:
    skill_id: str
    skill_version: str
    run_id: str
    completed_steps: tuple[str, ...]
    artifact_refs: tuple[str, ...]
    validation_refs: tuple[str, ...]
    status: SkillExecutionStatus
    failure_refs: tuple[str, ...]
```

---

# 19. Skill Failure Model

Failures should be explicit:

```text
SkillNotFound
SkillNotActive
SkillPrerequisiteFailed
SkillPolicyDenied
SkillToolDenied
SkillStepFailed
SkillValidationFailed
SkillEvidenceIncomplete
SkillBudgetExceeded
```

The runtime can then decide whether to:

```text
retry bounded step
escalate model
request human intervention
fail task
```

The skill itself must not silently broaden permissions.

---

# 20. Human Approval Boundaries

Some skills should require human approval.

Example classes:

```text
LOW RISK
read-only analysis
review
local tests

MEDIUM RISK
workspace code modification
branch creation
larger refactor

HIGH RISK
production configuration
live deployment
trading execution
credential/security changes
```

The skill declares the approval requirement, but the runtime policy is authoritative.

No skill can convert a high-risk action into an autonomous action merely by declaring it safe.

---

# 21. GreenSkill Categories

Initial categories for GAIEP:

## Engineering

```text
python-implementation
python-refactor
python-debug
python-testing
python-code-review
python-review-audit
```

## Research

```text
literature-review
hypothesis-analysis
evidence-synthesis
experiment-design
backtest-analysis
```

## GreenZAlgo

Domain-specific skills should eventually live with the domain owner rather than in the generic platform.

Examples:

```text
strategy-analysis
feature-analysis
indicator-validation
prediction-analysis
research-campaign-analysis
```

These should remain separate from generic engineering skills.

---

# 22. Repository Ownership

Recommended ownership:

```text
GreenSkills runtime mechanism
    -> greenz-ai-engineering

Generic Skill Registry / governance interfaces
    -> greenz-ai-platform if required

Trading/research skill definitions
    -> GreenZAlgo_V4

Design specifications
    -> ChatGPT repository
```

Do not put GreenZAlgo trading procedure into the generic platform.

---

# 23. Skill Registry

The first registry should be filesystem/Git-backed and deterministic.

Conceptually:

```text
skills/
├── engineering/
│   ├── python-implementation/
│   │   └── skill.yaml
│   ├── python-review/
│   │   └── skill.yaml
│   └── python-testing/
│       └── skill.yaml
└── research/
    └── ...
```

Avoid introducing a database before the lifecycle is proven.

A future registry may index skills for semantic discovery.

---

# 24. Skill Selection

Initial selection algorithm:

```text
Task
 |
 v
candidate skills
 |
 v
status filter
 |
 v
capability filter
 |
 v
applicability filter
 |
 v
prerequisite filter
 |
 v
policy intersection
 |
 v
ranked skill candidates
 |
 v
selected SkillManifest
```

The selection decision should be observable.

---

# 25. Skill Ranking

Initial deterministic ranking factors:

```text
exact task-class match
project match
capability match
version approval
prerequisite satisfaction
historical evidence
```

Historical evidence may influence ranking later, but must not silently rewrite the skill.

Semantic ranking can be introduced after deterministic selection is stable.

---

# 26. Skill Discovery vs Skill Execution

Keep these separate.

```text
Discovery
  = Which skill might apply?

Selection
  = Which approved skill should be used?

Execution
  = Follow the selected procedure.

Validation
  = Did the procedure produce acceptable evidence?
```

This separation prevents an LLM from inventing a new procedure and labeling it an approved skill during execution.

---

# 27. Skill Authoring

Skill authoring should eventually support:

```text
human authored
AI-assisted draft
validated against corpus
human/governance approval
versioned activation
```

AI may propose a skill, but it cannot activate an unapproved skill automatically.

---

# 28. Skill Evaluation Corpus

Each important skill should have a small benchmark corpus.

Example `python-implementation`:

```text
SKILL-PY-001 isolated function
SKILL-PY-002 multi-file change
SKILL-PY-003 interface extension
SKILL-PY-004 bug fix
SKILL-PY-005 test addition
SKILL-PY-006 type-check failure repair
SKILL-PY-007 regression prevention
```

Evaluate:

```text
completion rate
validation pass rate
repair count
tool calls
latency
token cost
human intervention
regression rate
```

The purpose is to determine whether the skill actually improves execution quality rather than merely making prompts longer.

---

# 29. Skill Certification

Skills should have a certification concept distinct from model certification.

```text
Model Certification
  = can this model reliably perform capability X?

Skill Certification
  = does this procedure reliably produce acceptable outcomes for task class X?
```

The runtime combines both:

```text
Skill
   +
Certified Model
   +
Tool Policy
   +
Validation
   =
Eligible Execution
```

Neither skill nor model certification alone is sufficient.

---

# 30. Multi-Model Implication

This is especially valuable for the current Mac constraint.

Instead of building:

```text
Qwen-only coding workflow
```

we build:

```text
Python Implementation Skill
          |
          v
      ModelPolicy
          |
   +------+-------+
   |      |       |
 Model A Model B Model C
```

The same procedure can be tested against multiple models.

This gives us empirical answers to:

> Which model is good enough for this specific skill?

rather than assuming a model is suitable merely because it is marketed as a coding model.

---

# 31. Cheap-Model Offloading

The architecture supports the earlier goal of using multiple models on the Mac without building a fragile tier router.

A cheaper model may execute a skill only after its **skill-specific certification evidence** demonstrates acceptable performance.

Example:

```text
Python formatting skill
    -> small model may pass

Python implementation skill
    -> 27B model may currently remain primary

Architecture review skill
    -> stronger model

Test generation skill
    -> candidate model under evaluation
```

This is better than:

```text
14B = normal work
27B = hard work
```

because our existing certification evidence already demonstrated that model size alone is not a reliable routing criterion.

---

# 32. Dual-Model / Disagreement Pattern

A future skill execution can optionally use:

```text
Primary model
      |
      v
result
      |
      +-------> challenger model
                     |
                     v
                 comparison
                     |
             +-------+-------+
             |               |
          agreement      disagreement
             |               |
             v               v
         confidence       escalate
```

This should be implemented later because it increases latency/cost.

It becomes particularly useful for high-impact engineering or research tasks once a credible second model exists.

---

# 33. Skill Observability

Every skill execution should produce:

```text
skill_id
skill_version
run_id
selected_reason
step events
tool calls
artifacts
validation
failure/retry events
model execution fingerprint
final disposition
```

This allows us to ask:

- which skill versions work;
- which models work with each skill;
- which steps fail most often;
- which skills consume excessive context;
- where human intervention is required.

---

# 34. Skill Improvement Loop

The improvement loop should be evidence-driven:

```text
Skill execution
      ↓
Observation
      ↓
Evidence
      ↓
Failure / success analysis
      ↓
Improvement proposal
      ↓
Skill candidate version
      ↓
Evaluation corpus
      ↓
Review / approval
      ↓
New active version
```

Do not permit:

```text
runtime failure
    ↓
automatically rewrite active skill
```

That would destroy reproducibility.

---

# 35. Relationship to Hermes-Inspired Runtime

Hermes-style agent systems provide useful inspiration for procedural skill organization and tool-oriented execution.

GAIEP should adapt that concept to GreenZ governance:

```text
Hermes-inspired skill mechanism
              +
GreenZ skill versioning
              +
GreenZ evidence
              +
GreenZ certification
              +
GreenZ authority boundaries
              =
GreenSkills
```

The goal is not to clone another agent framework.

---

# 36. Phase-1 GreenSkills Scope

The first implementation should be intentionally small.

Build only:

```text
Skill definition schema
Skill registry
SkillManifest integration
Deterministic applicability
Skill lifecycle
Skill execution events
Skill validation hooks
Skill benchmark fixture format
```

Do not yet build:

```text
semantic skill discovery
automatic skill generation
automatic skill activation
skill marketplace
cross-project skill synchronization
LLM-generated skill execution graphs
```

---

# 37. Initial Engineering Skills

Recommended first six:

```text
GS-PY-001 python-implementation
GS-PY-002 python-refactor
GS-PY-003 python-debug
GS-PY-004 python-testing
GS-PY-005 python-code-review
GS-PY-006 python-review-audit
```

These map directly to the existing engineering task surface and therefore provide the lowest-risk validation path.

---

# 38. Initial Skill Contract Example

```yaml
skill_id: GS-PY-001
name: Python Implementation
version: 1.0.0
status: ACTIVE
owner: greenz-ai-engineering
applicability:
  capability: CODING
  task_types:
    - implementation
prerequisites:
  - task_specification
  - writable_workspace
  - validation_commands
allowed_toolsets:
  - READ_SOURCE
  - WRITE_WORKSPACE
  - RUN_TESTS
  - RUN_LINT
  - RUN_TYPECHECK
steps:
  - inspect_task
  - inspect_sources
  - implement_change
  - format
  - typecheck
  - test
  - inspect_diff
  - produce_evidence
validation_gates:
  - tests_pass
  - diff_valid
  - overwrite_policy_pass
  - target_path_policy_pass
evidence_requirements:
  - changed_files
  - validation_results
  - diff_summary
```

This is illustrative; the actual active schema should be validated before source implementation.

---

# 39. Security Rules

GreenSkills must obey:

1. No arbitrary command execution.
2. No implicit network access.
3. No secret access.
4. No authority expansion.
5. No hidden tool acquisition.
6. No silent model substitution.
7. No direct production mutation unless separately authorized.
8. No automatic skill mutation.
9. No memory promotion without governance.
10. No bypass of platform certification.

---

# 40. Testing Strategy

Each skill requires:

```text
schema tests
applicability tests
precondition tests
step tests
tool-policy tests
validation tests
evidence tests
failure tests
regression tests
```

The first skill corpus should reuse the existing engineering certification cases where possible rather than creating a completely separate benchmark universe.

---

# 41. Implementation Package Structure

Proposed eventual structure:

```text
runtime/skills/
├── __init__.py
├── contracts.py
├── registry.py
├── selector.py
├── lifecycle.py
├── executor.py
├── validation.py
├── evidence.py
├── errors.py
└── adapters/
```

Definitions:

```text
skills/
├── engineering/
│   ├── python-implementation/
│   │   └── skill.yaml
│   ├── python-refactor/
│   │   └── skill.yaml
│   ├── python-debug/
│   │   └── skill.yaml
│   ├── python-testing/
│   │   └── skill.yaml
│   ├── python-code-review/
│   │   └── skill.yaml
│   └── python-review-audit/
│       └── skill.yaml
└── research/
    └── ...
```

---

# 42. Phase-1 Acceptance Criteria

GreenSkills Phase 1 is complete only when:

```text
[ ] schema is immutable/versioned
[ ] registry is deterministic
[ ] applicability is deterministic
[ ] SkillManifest integration works
[ ] skills cannot expand authority
[ ] skill lifecycle is enforced
[ ] execution events are emitted
[ ] validation gates are explicit
[ ] evidence requirements are explicit
[ ] first engineering skills have benchmark fixtures
[ ] at least one skill is evaluated against multiple certified models
[ ] no model-specific assumptions are embedded in the skill definition
[ ] rollback to previous skill version works
```

---

# 43. Strategic Outcome

GreenSkills gives GAIEP a stable unit for evaluating the **interaction of procedure and model capability**.

Instead of asking:

> Is Model X a good coding model?

we can ask:

> Is Model X certified to execute GreenSkill Y for task class Z under policy P with acceptable evidence, latency, and cost?

That is a much stronger basis for the multi-model architecture.

---

# 44. Final Architecture

```text
                         AGENT RUN
                             |
            +----------------+----------------+
            |                |                |
            v                v                v
      WorkspaceScope      TaskPolicy      ModelPolicy
            |                |                |
            +----------------+----------------+
                             |
                             v
                      Skill Selection
                             |
                             v
                       SkillManifest
                             |
              +--------------+--------------+
              |                             |
              v                             v
        Context Engine                Tool Policy
              |                             |
              +--------------+--------------+
                             |
                             v
                      Certified Model
                             |
                             v
                       Skill Execution
                             |
                    +--------+--------+
                    |                 |
                    v                 v
                Validation         Evidence
                    |                 |
                    +--------+--------+
                             |
                             v
                     Governance / Ledger
```

The core principle is:

> **GreenSkills define the procedure; the runtime controls authority; the Context Engine controls information exposure; the Gateway controls certified model execution; validation determines whether the procedure actually succeeded; and governance determines whether the result can be accepted or promoted.**
