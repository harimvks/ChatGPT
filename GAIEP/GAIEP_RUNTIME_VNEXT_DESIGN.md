# GAIEP Runtime VNext — Design Baseline

**Status:** Proposal / design baseline
**Date:** 2026-08-21
**Scope:** Consolidation of the Hermes Agent source audit with the current GreenZ AI Engineering, GreenZ AI Platform, and GreenZAlgo V4 architecture.

> This document is a design artifact only. It does not modify the three source repositories.

---

## 1. Executive Decision

GreenZ should **not replace GAIEP with Hermes Agent**.

Instead:

> **GAIEP Runtime VNext = Hermes-inspired agent-runtime discipline + GreenZ-specific engineering intelligence + GreenZ governance/evidence.**

The three source repositories remain the authorities for their respective concerns:

```text
GreenZAlgo_V4
    = domain system / trading / research source of truth

greenz-ai-engineering
    = engineering intelligence / CODING & REVIEW corpus / prompts / certification records

greenz-ai-platform
    = generic AI Gateway / provider routing / certification primitives / governance / observability

ChatGPT
    = design, proposals, audits, patches, experiments and generated implementation artifacts
```

---

## 2. Existing Architecture We Must Preserve

The current repository split is already sound.

`greenz-ai-engineering` is explicitly product-agnostic in its capability mechanism while owning the engineering corpus, prompts, certification records and task runner; it routes through `greenz-ai-platform`'s Gateway. fileciteturn130file0

`greenz-ai-platform` owns the generic Gateway, capability routing, provider/model registries, certification trust boundary, governance, prompt registry and observability, while keeping domain content out of the platform. fileciteturn131file0

GreenZAlgo V4 remains the domain application with modular separation, contracts/engines, acquisition, feedback, execution, liveops, pattern and platform layers. fileciteturn111file0 fileciteturn113file0 fileciteturn114file0

This means Runtime VNext should sit **between engineering intelligence and the generic platform**, not inside GreenZAlgo's trading-domain modules.

---

## 3. Target Architecture

```text
                              HUMAN / RESEARCH CAMPAIGN
                                        |
                                        v
                              +----------------------+
                              |   GAIEP Orchestrator  |
                              +----------+-----------+
                                         |
                  +----------------------+----------------------+
                  |                      |                      |
                  v                      v                      v
           Task / Plan Engine     Context Engine        Policy Engine
                  |                      |                      |
                  |                      +----------+-----------+
                  |                                 |
                  +---------------------+-----------+
                                        |
                                        v
                               Agent Runtime Loop
                                        |
               +------------------------+------------------------+
               |                        |                        |
               v                        v                        v
        Tool Registry              Model Gateway            Subagents
               |                        |                        |
               v                        v                        v
        GreenZ Toolsets       Local / API Providers       Bounded Children
               |                        |                        |
               +------------------------+------------------------+
                                        |
                                        v
                               Execution + Events
                                        |
                  +---------------------+---------------------+
                  |                     |                     |
                  v                     v                     v
             Checkpoints          Validation             Trajectory
                  |                     |                     |
                  +---------------------+---------------------+
                                        |
                                        v
                                  Evidence Layer
                                        |
                                        v
                              Certification / Governance
```

---

## 4. New GAIEP Runtime Package Boundary

The proposed runtime should be a **new layer** in `greenz-ai-engineering`, consuming the generic services from `greenz-ai-platform`.

```text
src / greenz-ai-engineering
└── runtime/
    ├── agent/
    ├── context/
    ├── tools/
    ├── skills/
    ├── subagents/
    ├── checkpoints/
    ├── trajectory/
    ├── policy/
    ├── sessions/
    └── models/
```

The platform should continue to own the generic Gateway/provider/certification mechanics rather than duplicating them.

---

## 5. Core Contract: AgentRun

`AgentRun` is the central runtime identity tying together model execution, tools, context, mutation safety and evidence.

```python
@dataclass(frozen=True)
class AgentRun:
    run_id: str
    task_id: str
    capability: str
    parent_run_id: str | None
    model_deployment: str
    provider: str
    context_manifest_id: str
    tool_manifest_id: str
    skill_manifest_id: str | None
    memory_manifest_id: str | None
    workspace_scope: str
    status: str
    started_at: datetime
    finished_at: datetime | None
```

Mutable runtime observations belong in an associated event stream rather than rewriting the identity record.

---

## 6. Context Engine

Hermes' context-engine design is one of the strongest mechanisms to adopt.

GAIEP should explicitly separate:

```text
SELECT    -> what the model needs for this request
BUDGET    -> how much context the request can afford
COMPRESS  -> how existing context can be reduced
OBSERVE   -> what the turn teaches the runtime
```

Proposed package:

```text
runtime/context/
├── engine.py
├── selector.py
├── budget.py
├── compressor.py
├── manifest.py
└── sanitization.py
```

### ContextManifest

Every model call should record:

- system/instruction sources
- task context
- project instruction files
- selected skills
- retrieved GreenMemory references
- source-code references
- tool schemas included
- prior outputs included
- compression events
- input token estimate/actual
- output reserve

This supports reproducibility and cost analysis.

---

## 7. Tool Registry and Tool Policy

Hermes' central registry should be adopted, but GreenZ needs a stricter policy boundary.

```text
Tool visible
   !=
Tool permitted
   !=
Tool executable
   !=
Tool promotion-authorized
```

A GreenZ tool declaration should include:

```yaml
tool_id: pytest.run
set: testing
permission_class: execute
risk_class: low
workspace_scope: gaiep-workspace
network_policy: offline
result_limit: 20000
audit_required: true
approval: none
```

### Toolsets

Initial toolsets:

```text
CODING
  filesystem.read
  workspace.write
  git.status
  git.diff
  python
  pytest
  ruff
  pyright

REVIEW
  filesystem.read
  git.diff
  pytest
  ruff
  pyright

RESEARCH
  filesystem.read
  research.query
  documentation
  feature_store.read
  measurement.read
  backtest.read

GOVERNANCE
  evidence.read
  certification.read
  promotion.inspect
```

Production execution tools are deliberately outside the default engineering toolsets.

---

## 8. Workspace Security Model

The requested Mac model should be the first supported local execution target.

```text
READ ONLY
~/greenz-ai-engineering
~/greenz-ai-platform
~/GreenZAlgo_V4

READ + WRITE
~/ChatGPT
```

The same policy should be expressible as a `WorkspaceScope` object.

```yaml
workspace_id: gaiep-dev
readonly_roots:
  - ~/greenz-ai-engineering
  - ~/greenz-ai-platform
  - ~/GreenZAlgo_V4
writable_roots:
  - ~/ChatGPT
commands:
  allowed:
    - git status
    - git diff
    - git log
    - pytest
    - ruff
    - pyright
```

No arbitrary shell command execution should be exposed by default.

---

## 9. Skills: GreenSkills

Hermes' skills mechanism should become **GreenSkills** rather than a generic memory dump.

```text
GreenSkills
├── engineering
│   ├── python-implementation
│   ├── refactoring
│   ├── debugging
│   ├── testing
│   └── review
├── platform
│   ├── gateway-change
│   ├── provider-registration
│   └── certification
├── research
│   ├── campaign
│   ├── feature-research
│   └── evidence
└── trading
    ├── feature-development
    ├── strategy-research
    └── backtest
```

Skills are procedural knowledge. They do not grant permissions.

Each skill should be versioned and carry:

- owner
- version
- applicability
- prerequisites
- allowed toolsets
- expected outputs
- validation gates
- evidence requirements
- approval state

---

## 10. GreenMemory vs GreenSkills

Keep a hard distinction:

```text
GreenMemory
  = durable facts, decisions, constraints, prior evidence

GreenSkills
  = reusable procedures for accomplishing work
```

Memory retrieval must include provenance.

A retrieved memory is **context**, not authoritative truth.

Authoritative truth remains in the source corpus, repository, certification ledger, or governed record appropriate to the subject.

---

## 11. Subagent Runtime

Adopt Hermes' bounded child lifecycle.

```text
Parent AgentRun
      |
      +--> Child Run: architect
      +--> Child Run: implement
      +--> Child Run: test
      +--> Child Run: review
```

Hard invariant:

```text
child authority ⊆ parent authority
```

A child declaration should include:

```text
goal
role
allowed_toolsets
workspace_scope
model_policy
context_budget
token_budget
wall_clock_budget
max_depth
approval_mode
```

The child returns an opaque handle plus a bounded result; the parent remains responsible for integration.

---

## 12. Subagent-Driven Development

For consequential coding work:

```text
Plan
  |
  v
Task Decomposition
  |
  +--> Fresh Implementer
  |
  +--> Spec Compliance Reviewer
  |
  +--> Quality Reviewer
  |
  +--> Test/Validation
  |
  v
Integration Review
  |
  v
Certification / Evidence
```

This is a strong Hermes pattern that maps directly onto GreenZ's existing certification discipline.

---

## 13. Checkpoints and Mutation Safety

Before every consequential workspace mutation:

```text
Checkpoint
   |
   v
Agent mutation
   |
   v
Validation
  / \
PASS FAIL
 |     |
 v     v
Keep  Rollback
```

Checkpoint identity should include:

- run_id
- task_id
- workspace_id
- baseline Git state
- created_at
- mutation scope

The rollback operation itself must be auditable.

---

## 14. TrajectoryRecord

Record **observable execution events and artifacts**, not hidden chain-of-thought.

```text
AgentRun
  |
  +-- model.request
  +-- context.selected
  +-- tool.visible
  +-- tool.call
  +-- tool.result
  +-- file.read
  +-- file.write
  +-- checkpoint.created
  +-- subagent.started
  +-- subagent.finished
  +-- validation.started
  +-- validation.finished
  +-- evidence.created
  +-- disposition.finalized
```

This becomes the raw evidence source for:

- model benchmarking
- routing optimization
- failure analysis
- cost analysis
- regression corpus generation
- skill candidate discovery

---

## 15. Model Gateway Integration

GAIEP Runtime VNext should **not** implement a second provider abstraction.

The runtime asks the existing platform Gateway for a model deployment.

```text
Agent Runtime
     |
     v
ReasoningRequest
     |
     v
GreenZ AI Platform Gateway
     |
     +--> registry
     +--> certification gate
     +--> capability selection
     +--> provider
     |
     v
Model
```

The existing platform already routes the engineering product's CODING/REVIEW workloads through this boundary. fileciteturn130file0

This is important because our model experiments include local Qwen, API models and future larger local models. GAIEP should remain model-agnostic.

---

## 16. Model Policy for Current GreenZ

Current evidence remains authoritative.

- `qwen3.6:27b` is the current certified engineering incumbent according to the existing platform/engineering records. fileciteturn130file0
- New models must pass the same certification harness before being eligible for routing.

Potential future model classes:

```text
Local engineering model
Cheap API worker
Premium coding model
Frontier escalation model
Research model
```

The runtime should consume certified deployments rather than hard-code model names.

---

## 17. Context / Model / Tool Cost Accounting

Every request should record:

```text
input_tokens
output_tokens
cache_read_tokens
cache_write_tokens
reasoning_tokens (if provider exposes them)
latency
model/provider
context utilization
tool-call count
child-run count
estimated cost
```

This enables the important GAIEP metric:

> **cost per successful engineering task**

rather than cost per token alone.

---

## 18. Failure and Escalation Model

The runtime should use explicit, observable escalation.

```text
Primary certified model
        |
        v
Validation
  /   \
PASS  FAIL
 |      |
 v      v
Done  Escalation policy
         |
         v
    Challenger model
         |
         v
      Validation
```

Existing `failed_over_from`-style evidence should be preserved where available.

Substitution must never be silent.

---

## 19. Repository Boundary

The runtime must keep the repository roles clean.

```text
GreenZAlgo_V4
  <- domain source of truth

Greenz AI Engineering
  <- engineering intelligence

Greenz AI Platform
  <- generic runtime/platform primitives

ChatGPT
  <- proposed designs, reports, experiments, patches
```

No new GreenZ trading-domain knowledge should be moved into `greenz-ai-platform` merely because the runtime needs it.

The platform's existing domain-vocabulary fitness discipline should remain intact. fileciteturn131file0

---

## 20. Integration With Existing Repository Structure

GreenZAlgo V4 already has explicit module boundaries, including Acquisition, Execution, Feedback, LiveOps, Pattern and Substrate, with contracts and engines separated in several modules. fileciteturn111file0 fileciteturn110file0 fileciteturn113file0 fileciteturn114file0

The new runtime must **not** be inserted into those domain modules.

Prefer:

```text
Greenz AI Engineering
└── runtime/

Greenz AI Platform
└── existing gateway/provider/governance/certification

GreenZAlgo V4
└── domain consumers of AI capabilities
```

GreenZAlgo consumers should call product-facing interfaces rather than importing low-level provider classes.

---

## 21. AGENTS.md Hierarchy

Adopt scoped project instructions:

```text
root AGENTS.md
  |
  +--> greenz-ai-engineering/AGENTS.md
  |
  +--> greenz-ai-platform/AGENTS.md
  |
  +--> GreenZAlgo_V4/AGENTS.md
```

Rules can become more specific down the tree but cannot weaken higher-level security/governance constraints.

---

## 22. MCP / External Tools

Use MCP only behind the same Tool Registry and policy boundary.

```text
MCP server
   |
   v
Tool adapter
   |
   v
Tool registry
   |
   v
Policy
   |
   v
Agent
```

MCP transport itself is not authorization.

---

## 23. Migration Strategy

### Phase 0 — Contracts

Implement only the data contracts and event model:

- AgentRun
- ContextManifest
- ToolManifest
- SkillManifest
- MemoryManifest
- WorkspaceScope
- Checkpoint
- SubagentHandle
- TrajectoryRecord
- EvidenceRecord

### Phase 1 — Runtime safety

- Context Engine
- Tool Registry/Toolsets
- Checkpoint Manager
- execution event bus
- workspace policy

### Phase 2 — Engineering intelligence

- GreenSkills
- project instruction hierarchy
- subagent lifecycle
- session/trajectory search

### Phase 3 — Evidence integration

- certification integration
- routing evidence
- failed-task capture
- successful workflow → skill candidates

### Phase 4 — Advanced orchestration

- specialist parallel review
- MoA-style evidence aggregation
- adaptive context selection
- cost-aware routing

---

## 24. What We Should Not Do

1. Do not fork Hermes wholesale.
2. Do not create a second provider abstraction in Engineering.
3. Do not put GreenZ trading concepts into Platform.
4. Do not let skills grant permissions.
5. Do not let retrieved memory override authoritative records.
6. Do not expose unrestricted shell execution.
7. Do not make subagents more privileged than parents.
8. Do not promote a model based on public benchmarks alone.
9. Do not treat model confidence as certification.
10. Do not modify the three source repositories during the design phase.

---

## 25. Immediate Next Implementation Artifacts

The following design artifacts should be created under the `ChatGPT` design workspace before source changes are proposed:

```text
GAIEP/
├── architecture/
│   ├── GAIEP_RUNTIME_VNEXT_DESIGN.md                # this document
│   ├── GAIEP_AGENT_RUNTIME_CONTRACTS.md
│   ├── GAIEP_CONTEXT_ENGINE_DESIGN.md
│   ├── GAIEP_TOOL_REGISTRY_DESIGN.md
│   ├── GAIEP_GREEN_SKILLS_DESIGN.md
│   ├── GAIEP_SUBAGENT_RUNTIME_DESIGN.md
│   ├── GAIEP_CHECKPOINT_AND_ROLLBACK.md
│   └── GAIEP_SECURITY_BOUNDARY.md
├── mapping/
│   ├── CURRENT_TO_TARGET_MODULE_MAPPING.md
│   └── HERMES_TO_GAIEP_FILE_MAPPING.md
├── implementation/
│   └── GAIEP_RUNTIME_VNEXT_IMPLEMENTATION_PLAN.md
└── reports/
    └── GAIEP_VNEXT_DECISION_RECORD.md
```

---

## 26. Final Direction

The preferred GreenZ architecture is now:

```text
                 GreenZ AI Engineering
                         |
                    GAIEP Runtime
                         |
      +------------------+------------------+
      |                  |                  |
 Context Engine     Tool/Skill System    Subagents
      |                  |                  |
      +------------------+------------------+
                         |
                 AI Platform Gateway
                         |
       +-----------------+-----------------+
       |                 |                 |
    Local Qwen        API models      Future large AI
       |                 |                 |
       +-----------------+-----------------+
                         |
                  Validation/Evidence
                         |
                    Governance
                         |
                         v
                    GreenZAlgo V4
```

The architectural goal is **not maximum autonomy**. It is **maximum useful autonomy within explicit, inspectable boundaries**.

The design target is:

> **Hermes-grade runtime discipline + GreenZ engineering intelligence + GreenZ evidence/governance.**
