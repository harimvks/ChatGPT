# GAIEP Runtime VNext — Master Architecture & Implementation Roadmap

**Status:** Master proposal / architecture baseline
**Date:** 2026-08-21
**Scope:** Consolidation of Agent Runtime Contracts, Context Engine, GreenSkills, and Bounded Subagent Runtime

> This document is the master architecture for the next GAIEP runtime layer. It consolidates the previously defined contracts and keeps existing GreenZ engineering/model certification behavior as the compatibility baseline.

---

# 1. Executive Summary

GAIEP Runtime VNext should evolve from a model-calling workflow into a **governed execution substrate**.

The runtime is built around six separations:

```text
AgentRun
  = unit of governed execution

Context Engine
  = what information is exposed

GreenSkills
  = how work should be performed

Tool Policy
  = what actions are authorized

Model Gateway
  = which certified model executes

Evidence / Governance
  = what actually happened and whether it is acceptable
```

Bounded Subagents provide decomposition across these primitives without becoming independent authority holders.

---

# 2. Architectural Goal

The target is not:

```text
LLM wrapper
```

and not:

```text
fully autonomous agent swarm
```

The target is:

```text
                    GOVERNED AGENT RUNTIME

       deterministic where possible
       adaptive where justified
       evidence-backed
       policy-bounded
       model-independent
       locally deployable
       remotely scalable
```

The architecture must work on the current Mac and scale to a larger AI server later without redesigning the core contracts.

---

# 3. Current Baseline

GAIEP already has important pieces of the target architecture:

```text
Gateway
Capability tags
Certified model deployments
Task-type surface
Ordered escalation/failover
Engineering context builder
Validation gates
Overwrite protection
Certification ledger
Run manifests
```

Therefore VNext should **mature and formalize existing mechanisms**, not replace everything simultaneously.

---

# 4. Master Architecture

```text
                               USER / SYSTEM TASK
                                      |
                                      v
                                +-----------+
                                |  AgentRun |
                                +-----+-----+
                                      |
                +---------------------+---------------------+
                |                     |                     |
                v                     v                     v
         WorkspaceScope           TaskPolicy           ModelPolicy
                |                     |                     |
                +---------------------+---------------------+
                                      |
                                      v
                              GreenSkill Selection
                                      |
                                      v
                                SkillManifest
                                      |
                    +-----------------+-----------------+
                    |                                   |
                    v                                   v
              Context Engine                       Tool Policy
                    |                                   |
          +---------+---------+                         |
          |         |         |                         |
       SELECT     BUDGET   COMPRESS                    |
          |         |         |                         |
          +---------+---------+                         |
                    |                                   |
                    v                                   v
             ContextManifest                     ToolManifest
                    |                                   |
                    +-----------------+-----------------+
                                      |
                                      v
                               Subagent Runtime
                              /        |        \
                             /         |         \
                            v          v          v
                         Child A    Child B     Child C
                            |          |           |
                            +----------+-----------+
                                       |
                                       v
                                Model Gateway
                                       |
                          +------------+------------+
                          |                         |
                     local model               API model
                          |                         |
                          +------------+------------+
                                       |
                                       v
                                  Tool Execution
                                       |
                                       v
                                   Validation
                                       |
                              +--------+--------+
                              |                 |
                              v                 v
                           Evidence         Checkpoints
                              |                 |
                              +--------+--------+
                                       |
                                       v
                                Parent Aggregation
                                       |
                                       v
                                  Governance
                                       |
                          +------------+------------+
                          |                         |
                       ACCEPT                   REJECT
                          |                         |
                          v                         v
                      Artifact                 Escalation /
                      / update                  Human review
```

---

# 5. The Runtime as a State Machine

```text
REQUESTED
   |
   v
PLANNED
   |
   v
AUTHORIZED
   |
   v
CONTEXT_READY
   |
   v
SKILL_READY
   |
   v
EXECUTING
   |
   +-------> CHECKPOINTED
   |
   v
VALIDATING
   |
   +-------> FAILED
   |
   v
EVIDENCE_READY
   |
   v
GOVERNANCE
   |
   +-------> ESCALATE
   |
   +-------> REJECT
   |
   v
ACCEPTED
```

Every state transition should be observable and attributable to a `run_id`.

---

# 6. Core Runtime Objects

The master object graph is:

```text
AgentRun
  |
  +-- TaskSpec
  +-- WorkspaceScope
  +-- TaskPolicy
  +-- ModelPolicy
  +-- SkillManifest
  +-- ContextManifest
  +-- ToolManifest
  +-- SubagentHandle[]
  +-- Checkpoint[]
  +-- Evidence[]
  +-- Validation[]
  +-- GovernanceDecision
```

Each object should have immutable identifiers and explicit provenance.

---

# 7. AgentRun

`AgentRun` is the top-level unit of execution.

It establishes:

```text
identity
scope
policy
budget
selected skill(s)
context
model policy
child budget
lifecycle
trajectory
final disposition
```

A child subagent belongs to an AgentRun; it does not become a peer of the AgentRun.

---

# 8. WorkspaceScope

Workspace authority must be explicit.

Example:

```text
WorkspaceScope
  root = ~/ChatGPT
  mode = READ_WRITE
  allowed_paths = [...]
  forbidden_paths = [...]
```

For current GreenZ development, the design can represent:

```text
source repositories = READ_ONLY
ChatGPT design/workspace = READ_WRITE
```

The runtime must enforce the scope independently of model instructions.

---

# 9. TaskPolicy

TaskPolicy defines what the run is intended and permitted to do.

Examples:

```text
analysis only
implementation
review
research
validation
artifact generation
```

TaskPolicy can constrain:

```text
tools
skills
write capability
network capability
subagents
approval requirements
```

---

# 10. ModelPolicy

ModelPolicy remains the sole runtime authority for model eligibility.

```text
Task / Skill
     |
     v
ModelPolicy
     |
     v
Certified deployment(s)
     |
     v
Gateway
```

The Context Engine and GreenSkills must not become hidden model routers.

---

# 11. GreenSkills

GreenSkills define reusable procedures.

```text
GreenSkill
  |
  +-- applicability
  +-- prerequisites
  +-- procedure
  +-- allowed toolsets
  +-- expected artifacts
  +-- validation gates
  +-- evidence requirements
  +-- failure policy
  +-- version
```

Skills are versioned and immutable by version.

---

# 12. Context Engine

The Context Engine controls information exposure.

Its responsibilities are:

```text
SELECT
BUDGET
COMPRESS
SANITIZE
MANIFEST
OBSERVE
```

It must answer:

> What information did the model actually receive, why was it selected, what was excluded, and what policy permitted it?

The Context Engine does not authorize tools or choose models.

---

# 13. Tool Policy / ToolManifest

Tools are governed separately from skills and context.

```text
Skill allowed tools
        ∩
Run ToolPolicy
        ∩
WorkspaceScope
        ∩
Global policy
        =
Effective tools
```

A tool mentioned in context does not become executable merely because the model sees it.

---

# 14. Bounded Subagent Runtime

Subagents provide decomposition.

Core invariant:

```text
ChildAuthority ⊆ ParentAuthority
```

Initial implementation:

```text
max_depth = 1
```

Recommended first use:

```text
read-only analysis children
```

Write-capable children should operate in isolated workspaces and return patches/artifacts to the parent for validation.

---

# 15. Resource Budget Model

Every AgentRun should have explicit budgets.

```text
AgentRun budget
  |
  +-- model tokens
  +-- context tokens
  +-- tool calls
  +-- child tokens
  +-- child count
  +-- runtime
  +-- output/artifact budget
```

Child budgets are allocations from the parent budget.

```text
ChildBudget ≤ ParentRemainingBudget
```

The runtime must preserve a reserve for final aggregation and validation.

---

# 16. Mac-Aware Execution

The current local environment has demonstrated memory sensitivity with large local models.

Therefore the runtime must distinguish:

```text
logical concurrency
vs
physical model concurrency
```

A parent may logically have three children while the scheduler runs only one local model inference at a time.

Required future scheduler inputs:

```text
model memory requirement
model residency
available RAM
current inference load
local/remote deployment
```

This becomes important when the system uses multiple models.

---

# 17. Local-First, Remote-Ready

The architecture should support:

```text
                    Model Gateway
                         |
              +----------+----------+
              |                     |
              v                     v
        Local deployment       API deployment
              |                     |
           Ollama/other          provider
              |                     |
              +----------+----------+
                         |
                         v
                  same AgentRun
```

The runtime must not embed provider-specific assumptions in Skills, Context Engine, or Subagent contracts.

---

# 18. Evidence Architecture

Evidence is the bridge between execution and governance.

```text
Tool events
Skill steps
Model execution metadata
Artifacts
Validation
Tests
Diffs
Subagent results
       |
       v
    Evidence
       |
       v
Governance / Ledger
```

Evidence should describe observable facts rather than hidden model reasoning.

---

# 19. Checkpoint Architecture

Checkpoints enable recovery and audit.

```text
AgentRun
  |
  +-- checkpoint 1: authorized
  +-- checkpoint 2: context ready
  +-- checkpoint 3: skill step complete
  +-- checkpoint 4: artifact ready
  +-- checkpoint 5: validation complete
  +-- checkpoint 6: governance decision
```

Checkpoint data should reference artifacts rather than duplicate large payloads.

---

# 20. Validation Architecture

Validation remains external to model claims.

```text
Model says "done"
       |
       X
       |
       v
Actual validation
       |
       +--> tests
       +--> lint
       +--> type check
       +--> policy checks
       +--> artifact checks
       +--> certification checks
```

Only validation-backed evidence can support acceptance.

---

# 21. Governance Architecture

Governance determines whether the result may be accepted.

```text
Evidence
   |
   v
Governance Rules
   |
   +--> ACCEPT
   +--> REJECT
   +--> ESCALATE
   +--> HUMAN REVIEW
```

Governance should remain deterministic wherever possible.

---

# 22. Multi-Model Strategy

The architecture supports multiple models without a static tier hierarchy.

Instead of:

```text
small = easy
large = hard
```

use:

```text
Task
 + Skill
 + Evidence
 + Model certification
 + Resource constraints
        |
        v
ModelPolicy
        |
        v
eligible deployment(s)
```

This matches the empirical lesson from current certification: a model must earn routing eligibility rather than receive it because of size or branding.

---

# 23. Skill-Specific Model Certification

The long-term unit of evaluation should be:

```text
Model × Skill × Task Class
```

For example:

```text
Qwen3.6:27B × PythonImplementation × corpus
Candidate14B × PythonTesting × corpus
CandidateModel × CodeReview × corpus
```

This produces much more useful routing evidence than a single generic coding score.

---

# 24. Optional Challenger Pattern

A high-value future pattern is:

```text
Primary execution
       |
       v
Independent challenger
       |
       v
Agreement analyzer
       |
   +---+---+
   |       |
 agree  disagree
   |       |
   v       v
accept   escalate
```

Use selectively because it increases latency and token cost.

---

# 25. Memory Architecture

GreenMemory remains separate.

```text
Execution
   |
   v
Observation
   |
   v
Evidence
   |
   v
Memory candidate
   |
   v
Governance
   |
   v
GreenMemory
```

No runtime component should silently mutate durable memory.

---

# 26. Research / Trading Integration

For GreenZAlgo V4, GAIEP should eventually support:

```text
Research Task
      |
      v
Research Skill
      |
      v
Context Engine
      |
      v
Research Subagents
      |
  +---+---+---+
  |   |   |   |
  v   v   v   v
Data Feature Strategy Prediction
  |   |   |   |
  +---+---+---+
      |
      v
Evidence Generator
      |
      v
Research Campaign / Governance
```

The trading/research domain remains in GreenZAlgo rather than being hard-coded into generic GAIEP runtime components.

---

# 27. Research Safety Boundary

The generic runtime must not directly perform live trading actions simply because a trading Skill exists.

A future trading execution capability must have its own explicit:

```text
ToolPolicy
RiskPolicy
ExecutionPolicy
ApprovalPolicy
Validation
Audit
```

Research and live execution remain distinct capability classes.

---

# 28. Runtime Observability

Every run should be reconstructible through:

```text
run_id
parent/child relationships
skill version
context manifest
context hash
model execution reference
tool events
checkpoint sequence
validation results
evidence references
governance decision
```

This creates the GAIEP trajectory/evidence substrate.

---

# 29. Artifact Model

Artifacts should be first-class references.

Examples:

```text
source snapshot
patch
diff
report
test result
lint result
backtest result
feature snapshot
research evidence
model evaluation result
```

Avoid storing giant duplicated outputs in event records.

---

# 30. Failure Model

Failures should be typed and attributable.

Examples:

```text
ContextBudgetExceeded
SkillPrerequisiteFailed
ToolPolicyDenied
WorkspaceScopeDenied
ModelUnavailable
ModelCertificationDenied
SubagentBudgetExceeded
ValidationFailed
EvidenceIncomplete
GovernanceRejected
```

Every failure should answer:

```text
what failed?
why?
where?
what budget was consumed?
what recovery policy applied?
```

---

# 31. Escalation Model

Escalation is a policy decision, not an informal model substitution.

```text
failure / uncertainty
       |
       v
EscalationPolicy
       |
   +---+---+
   |       |
 retry   escalate
           |
           v
       eligible model
           |
           v
         Gateway
```

The event should preserve the original failed execution and the replacement execution.

---

# 32. Implementation Repository Boundaries

Recommended ownership:

```text
ChatGPT
  = architecture / design / proposals / review artifacts

 greenz-ai-engineering
  = GAIEP runtime implementation

 greenz-ai-platform
  = shared Gateway / platform contracts / governance services

 GreenZAlgo_V4
  = trading/research domain implementation and skills
```

This avoids turning one repository into a monolith.

---

# 33. Package-Level Boundary

Recommended engineering runtime structure:

```text
runtime/
├── agent/
├── context/
├── skills/
├── subagents/
├── tools/
├── policy/
├── checkpoints/
├── evidence/
├── validation/
└── governance/
```

Platform integrations should remain behind explicit adapters.

---

# 34. Phase-1 Implementation Scope

Do not implement the entire architecture at once.

Phase 1:

```text
AgentRun contracts
Context Engine
GreenSkills contracts/registry
Depth-1 read-only Subagent Runtime
Tool-policy intersection
Checkpoints
Evidence references
Validation integration
```

Phase 1 deliberately excludes:

```text
recursive agents
autonomous skill generation
semantic skill discovery
large-scale memory retrieval
production trading execution
unrestricted network tools
```

---

# 35. Phase-2 Scope

After Phase 1 is certified:

```text
isolated write subagents
skill benchmark automation
model × skill certification
adaptive model selection
semantic/fingerprint retrieval
improved GreenMemory integration
parallel local scheduling
```

---

# 36. Phase-3 Scope

Only after sufficient evidence:

```text
bounded recursive subagents
challenger execution
advanced planning
adaptive context selection
research campaign orchestration
cross-run learning
```

Each feature remains subject to governance gates.

---

# 37. Implementation Sequence

Recommended exact order:

```text
01. Freeze architecture contracts
        ↓
02. Map existing runtime implementation
        ↓
03. Introduce AgentRun identity/state
        ↓
04. Implement Context Engine contracts
        ↓
05. Legacy context adapter
        ↓
06. Context compatibility tests
        ↓
07. GreenSkills registry/contracts
        ↓
08. First six engineering skills
        ↓
09. Skill certification fixtures
        ↓
10. Tool-policy intersection
        ↓
11. Read-only Subagent Runtime
        ↓
12. Checkpoints + evidence
        ↓
13. Gateway integration
        ↓
14. Certification regression
        ↓
15. Isolated write subagents
        ↓
16. Model × Skill certification
```

This order minimizes simultaneous architectural change.

---

# 38. Migration Strategy

Existing workflow:

```text
run_task
  ↓
current context builder
  ↓
Gateway
  ↓
validation
```

Migration:

```text
run_task
  ↓
AgentRun
  ↓
ContextEngine
  ↓
Legacy adapter initially
  ↓
Gateway
  ↓
existing validation
```

Then gradually replace adapter internals while retaining behavioral comparison.

---

# 39. Compatibility Gate

Every migration step must answer:

```text
Did existing tasks still behave correctly?
Did security boundaries remain intact?
Did certification results remain valid?
Did overwrite protection remain intact?
Did evidence remain reproducible?
```

No architecture elegance is sufficient justification for breaking an already validated engineering path.

---

# 40. Testing Architecture

```text
                 Test Pyramid
                      |
       +--------------+--------------+
       |              |              |
    Contracts      Security      Determinism
       |              |              |
       +--------------+--------------+
                      |
               Integration
                      |
               Compatibility
                      |
             Certification
                      |
            End-to-End Corpus
```

Testing should reuse existing GreenZ certification infrastructure wherever practical.

---

# 41. Architecture Decision Records

Create ADRs for decisions that materially affect the runtime.

Initial ADR candidates:

```text
ADR-001 AgentRun as top-level execution unit
ADR-002 Context Engine authority boundary
ADR-003 GreenSkills authority separation
ADR-004 Depth-1 subagents initially
ADR-005 ModelPolicy remains Gateway-owned
ADR-006 Evidence over hidden reasoning
ADR-007 Isolated write workspaces
ADR-008 Skill-specific model certification
ADR-009 Local-first / remote-ready model execution
ADR-010 No automatic mutation of skills/memory
```

---

# 42. Key Metrics

GAIEP Runtime VNext should measure:

### Quality

```text
validation pass rate
certification pass rate
regression rate
human intervention rate
```

### Efficiency

```text
latency
tokens
cost
tool calls
context size
```

### Agent behavior

```text
skill success
subagent success
escalation rate
retry rate
conflict rate
```

### Resource safety

```text
peak memory
concurrent local models
child count
budget exhaustion
```

---

# 43. Success Criteria

The architecture succeeds if it allows us to answer with evidence:

> Which procedure was used, what information did the model receive, what authority did it have, which certified model executed it, what tools were used, what artifacts were produced, what validation occurred, what went wrong, and why was the final result accepted?

That is the core GAIEP objective.

---

# 44. What GAIEP Should Not Become

Avoid:

```text
LLM decides its own permissions
LLM decides its own model
LLM edits its own active skill
LLM mutates durable memory directly
unbounded recursive agents
shared concurrent workspaces
hidden tool acquisition
silent failover
acceptance based solely on model confidence
```

These are architectural anti-patterns for the intended GreenZ environment.

---

# 45. Strategic Advantage

The architecture creates a stable abstraction over changing AI models.

Today:

```text
local Qwen deployment(s)
API coding/reasoning models
```

Later:

```text
larger local server
multiple GPUs
larger coding models
specialist models
future open-source models
```

The runtime contracts do not need to change merely because the model inventory changes.

---

# 46. Final Architecture

```text
                            GAIEP
                             |
                     +-------+-------+
                     |               |
                  AgentRun       Governance
                     |
        +------------+------------+
        |            |            |
     Context      Skills        Policy
      Engine         |            |
        |             |            |
        +-------------+------------+
                      |
                 Subagents
                      |
                 Model Gateway
                      |
                 Tool Runtime
                      |
                 Validation
                      |
                  Evidence
                      |
                 Checkpoints
                      |
                 GreenMemory
```

The ordering matters:

```text
Policy
  → Skill
  → Context
  → Execution
  → Validation
  → Evidence
  → Governance
```

Not:

```text
LLM
  → figure everything out
```

---

# 47. Final Recommendation

Freeze this architecture as the **GAIEP Runtime VNext master design** before implementing substantial source changes.

Then create a controlled implementation branch in `greenz-ai-engineering` and implement only Phase 1.

The first executable milestone should be:

```text
AgentRun
   ↓
Context Engine
   ↓
one GreenSkill
   ↓
one certified model
   ↓
read-only execution
   ↓
validation
   ↓
evidence
```

Once that path is proven, expand horizontally.

The objective is not maximum autonomy.

The objective is **measurable, reproducible, policy-bounded autonomy that can improve as models, skills, hardware, and GreenZ research capabilities evolve.**
