# GAIEP VNext — External Architecture Synthesis

**Status:** Research / architecture decision input  
**Scope:** DeepSeek Harness, ARC-AGI, FinceptTerminal, OpenCode, OpenClaw, Pi  
**Repository:** `harimvks/ChatGPT` / `GAIEP-LAB`  
**Decision principle:** External projects are references or isolated adapters; GAIEP remains authoritative.

---

## 1. Executive Summary

The external architecture review establishes that the current GAIEP direction is sound, but several contracts should be sharpened before further runtime implementation.

The projects reviewed serve different architectural roles:

| Reference | Primary value to GAIEP / GreenZAlgo |
|---|---|
| DeepSeek Harness | Agent runtime, plugin seams, sessions/events, approval, scoped capabilities |
| ARC-AGI | Evaluation discipline, held-out testing, exact scoring, anti-overfitting methodology |
| FinceptTerminal | Financial workstation, quant research, market data, MCP, AI-quant workflows |
| OpenCode | Coding-agent execution / harness reference |
| OpenClaw | Agent orchestration, ACP, external harness lifecycle and routing |
| Pi | Minimal/extensible coding-agent runtime and replaceable agent loop |

### Core conclusion

Do **not** fork or make any of these systems the GAIEP core.

Instead, GAIEP should expose stable internal contracts around:

1. `AgentRun`
2. `RuntimeScope`
3. `ContextEngine`
4. `PreparedModelCall`
5. `AgentDriver` / `HarnessAdapter`
6. `ToolRegistry` + policy
7. `ApprovalRequest` / `ApprovalDecision`
8. append-only `RunEvent` provenance
9. `EvaluationCampaign`
10. `EvaluationSetManifest`
11. Evidence / certification / promotion
12. GreenMemory / research memory

The external implementations can then sit behind those boundaries.

---

## 2. Existing GAIEP Architectural Invariants

The current GAIEP design already separates:

- model execution
- tools
- context
- skills
- memory
- mutation authority
- evidence
- governance

`AgentRun` is intended to be the durable identity tying together execution, context, tools, skills, memory, workspace scope, and evidence.

The existing platform Gateway already performs model/provider/deployment routing. **GAIEP must not build a second model provider/Gateway abstraction.** GAIEP should call the existing Gateway and remain model-agnostic.

Current engineering-model certification remains separate from runtime architecture. Model candidates must not drive architecture changes.

---

## 3. Architectural Synthesis

### 3.1 Target architecture

```text
                         GAIEP
                           |
              +------------+------------+
              |            |            |
          Governance    Evidence     Research
              |            |            |
              +------------+------------+
                           |
                    AgentRun Contract
                           |
                    RuntimeScope
                           |
              +------------+------------+
              |                         |
        ContextEngine              PolicyEngine
              |                         |
              +------------+------------+
                           |
                 PreparedExecution
                           |
                    AgentDriver API
                           |
        +------------------+------------------+
        |                  |                  |
   GAIEP-native        DSH adapter      OpenCode/Pi
      driver                              adapters
        |                  |                  |
        +------------------+------------------+
                           |
                       ModelRunner
                           |
                    Existing Gateway
                           |
                  Provider / deployment
                           |
                         Model
                           |
                  +--------+--------+
                  |                 |
                Tools           Subagents
                  |                 |
                  +--------+--------+
                           |
                    RunEvent Log
                           |
             +-------------+-------------+
             |             |             |
         Trajectory     Artifacts     Validation
             |             |             |
             +-------------+-------------+
                           |
                         Evidence
                           |
                      GreenMemory
                           |
                     Promotion Gate
```

The important property is that **the harness is not the authority**.

---

# 4. DeepSeek Harness Findings

DeepSeek Harness is the strongest external reference for the **agent execution substrate**.

## 4.1 Adopt: replaceable Agent Driver

DeepSeek separates the public agent abstraction from the concrete agent loop. This validates separating GAIEP's `AgentRun` / agent contract from its runtime implementation.

### GAIEP decision

Add an explicit conceptual boundary:

```text
AgentRun / Agent Contract
          |
          v
     AgentDriver
          |
     +----+----+----+
     |    |    |    |
    DSH  Pi OpenCode native
```

The driver executes a prepared run. It does not become the governance authority.

**Priority: P0 architectural contract; P1 implementation.**

---

## 4.2 Adopt: provider-neutral model boundary

DeepSeek separates the agent loop from the provider-specific model adapter.

### GAIEP decision

Keep the existing decision:

```text
GAIEP
  -> existing Gateway
     -> certified deployment
        -> model
```

Do not import a second provider abstraction into GAIEP.

If DSH is integrated, create an adapter around DSH rather than allowing DSH's provider layer to become a second GAIEP Gateway.

**Priority: DEFER direct DSH integration.**

---

## 4.3 Adopt: immutable PreparedModelCall

DSH's preparation-before-dispatch model is particularly valuable for provenance.

GAIEP should introduce a conceptual immutable object:

```text
PreparedModelCall
- run_id
- model_deployment
- provider/deployment identity
- context_manifest_id
- tool_manifest_id
- skill_manifest_id
- memory_manifest_id
- policy snapshot
- capability snapshot
- request hash
- budget
```

Preparation occurs before dispatch. After preparation, the execution request is not silently rewritten by downstream layers.

### Invariant

```text
PreparedModelCall == dispatched request identity
```

Any transformation after preparation must either be prohibited or produce a new explicit derived artifact/event.

**Priority: P0.**

---

## 4.4 Adopt: append-only RunEvent model

DSH's session architecture demonstrates the value of an append-only typed event log from which model-visible state and other projections can be derived.

GAIEP should evolve toward:

```text
RunEvent
  - run.created
  - run.authorized
  - context.committed
  - model.requested
  - model.started
  - model.completed
  - tool.called
  - tool.completed
  - approval.requested
  - approval.decided
  - checkpoint.created
  - validation.completed
  - artifact.created
  - evidence.created
  - disposition.finalized
  - run.cancelled
```

### Derived projections

```text
RunEventLog
   |
   +--> model-visible trajectory
   +--> execution summary
   +--> artifact lineage
   +--> evidence graph
   +--> cost/latency metrics
   +--> failure corpus
```

`TrajectoryRecord` should therefore be treated as a projection, not the sole source of truth.

**Priority: P0 design; P1 implementation after Context Engine.**

---

## 4.5 Adopt: formal Approval seam

DeepSeek's approval design validates:

```text
ApprovalRequest
       |
ApprovalService
       |
ApprovalDecision
```

with fail-closed behavior and durable auditability.

### GAIEP distinction

Approval is not equivalent to authorization.

```text
Authorization
  = is this actor/run/capability/action permitted?

Approval
  = if policy requires human/explicit approval, did that specific action receive it?
```

Recommended flow:

```text
GAIEP Authorization
        |
        +--> approval required?
                 |
                 v
          ApprovalRequest
                 |
          ApprovalDecision
                 |
          tool/model mutation
```

**Priority: P0 contract; P1 runtime.**

---

## 4.6 Adopt: RuntimeScope

DeepSeek's scoped agent context supports temporary, agent-local capability registration and unwinding.

GAIEP should formalize a monotonic scope model:

```text
RuntimeScope
  - context scope
  - tool scope
  - skill scope
  - workspace scope
  - model scope
  - memory scope
  - budget scope
  - network scope
  - mutation scope
```

For subagents:

```text
ChildScope <= ParentScope
```

and specifically:

```text
ChildTools   <= ParentTools
ChildSkills  <= ParentSkills
ChildMemory  <= ParentMemoryPolicy
ChildWorkspace <= ParentWorkspace
ChildAuthority <= ParentAuthority
ChildBudget <= ParentRemainingBudget
```

Ambient execution context may propagate identity but must never be treated as authorization or durable provenance.

**Priority: P0 contract; P1 implementation with subagents.**

---

## 4.7 Adopt: cancellation semantics

Cancellation should propagate through:

```text
parent run
  -> child run
  -> model call
  -> tool call
```

and become durable evidence through explicit events.

Recommended states:

```text
requested
propagated
acknowledged
forced
completed
```

**Priority: P1.**

---

# 5. ARC-AGI Findings

ARC-AGI is primarily an evaluation methodology and task corpus, not an agent runtime.

Its strongest relevance is to GAIEP's evaluation and evidence architecture.

## 5.1 Adopt: development vs held-out evaluation separation

ARC distinguishes development/training material from evaluation material and warns against repeated algorithm modification using evaluation scores as feedback.

GAIEP should formalize:

```text
Development Set
   |
   +--> optimization / iteration
   |
Candidate Freeze
   |
Held-Out Evaluation Set
   |
Measurement only
   |
Evidence
   |
Promotion
```

### Invariant

```text
HeldOutEvaluationResult
        X
CandidateOptimizationFeedback
```

Once evaluation data is consumed for optimization, that set is no longer considered held-out for the same research campaign.

**Priority: P0.**

---

## 5.2 Adopt: EvaluationSetManifest

Create a manifest containing:

```text
EvaluationSetManifest
- dataset_id
- dataset_version
- partition
- task-set hash
- selection rule
- release timestamp
- visibility policy
- evaluation cutoff
- feedback policy
```

This should be immutable for a campaign.

**Priority: P0.**

---

## 5.3 Adopt: exact correctness predicates

ARC demonstrates the value of a hard correctness predicate when the task permits one.

GAIEP evaluations should distinguish:

```text
correctness
quality
policy compliance
provenance completeness
resource usage
reproducibility
```

A system should not be considered successful merely because the process looks plausible.

**Priority: P1.**

---

## 5.4 Adopt: generalization as a first-class measurement

For GAIEP self-improvement:

```text
in-domain performance
vs
held-out performance
vs
cross-task generalization
```

should be measured separately.

For GreenZAlgo, the analogue is:

```text
training period
validation period
walk-forward period
strict OOS period
future live/shadow period
```

with leakage controls.

**Priority: P0 for evaluation design; P1 implementation.**

---

# 6. FinceptTerminal Findings

FinceptTerminal is primarily relevant to GreenZAlgo's **financial application/research layer**, not to GAIEP's core agent-governance layer.

Its architecture demonstrates a modular financial workstation with bounded contexts, a data distribution plane, AI agents/MCP, and an AI Quant Lab.

## 6.1 Adopt concept: operational DataHub vs analytical lake

Fincept's DataHub provides operational topic-scoped distribution and caching.

GreenZAlgo should retain its existing distinction:

```text
Parquet Lake
  = durable historical/analytical data

Feature Store
  = reproducible feature snapshots

Operational DataBus
  = low-latency distribution
```

Recommended architecture:

```text
Parquet Lake
     |
Feature Store
     |
Operational DataBus
     |
+----+----+----+
|         |    |
Indicators Strategies Research
```

Do not replace the Parquet lake with an operational bus.

**Priority: P1.**

---

## 6.2 Adopt concept: bounded financial contexts

Fincept separates areas such as markets, news, economics, trading, portfolio, derivatives, agents, AI chat and workflow.

GreenZAlgo should preserve domain separation:

```text
Acquisition
Normalization
Feature / Measurement
Research
Prediction
Strategy
Risk
Execution
Monitoring
```

Cross-domain interaction should prefer typed contracts/events over dependency-heavy direct imports.

**Priority: P1 architecture.**

---

## 6.3 Adopt concept: AI Quant Lab workflow

Fincept's AI Quant Lab combines Qlib and RDAgent for hypothesis generation, feature engineering, model training, backtesting, portfolio optimization, evaluation and knowledge storage.

The useful concept for GreenZAlgo is the complete research loop, but GAIEP/GreenZAlgo must insert stronger controls:

```text
Research Idea
   |
Hypothesis
   |
Universe
   |
Data Snapshot
   |
Feature / Strategy Candidate
   |
Measurement
   |
Vector Screening
   |
Event Validation
   |
Walk-Forward / OOS
   |
Stress / Monte Carlo
   |
Evidence
   |
Fingerprint
   |
Research Memory
   |
Promotion Gate
```

Fincept should be treated as a reference, not a replacement for this GreenZAlgo lifecycle.

**Priority: P1.**

---

## 6.4 Adopt concept: MCP as tool transport, not governance

Fincept's MCP/tool registry model is useful for interoperability.

GAIEP should maintain:

```text
Tool Registry
   |
Policy
   |
Approval
   |
MCP / transport adapter
   |
Tool execution
```

MCP must never become the authorization boundary merely because a tool is exposed through MCP.

**Priority: P1.**

---

## 6.5 Do not adopt as core dependency

Do not make FinceptTerminal a GAIEP or GreenZAlgo core dependency.

Reasons:

- different product architecture;
- broad desktop modular monolith scope;
- external licensing/commercial boundaries require separate review;
- GreenZAlgo already has its own proprietary research/data architecture.

Use concepts selectively or isolate any integration behind an adapter.

**Priority: DEFER direct dependency.**

---

# 7. OpenCode / OpenClaw / Pi Findings

These systems are best viewed as **agent execution infrastructure**.

## 7.1 Common GAIEP rule

None should become the GAIEP governance authority.

```text
GAIEP
  |
  +--> AgentDriver / HarnessAdapter
          |
          +--> OpenCode
          +--> Pi
          +--> DeepSeek Harness
          +--> Codex
          +--> GAIEP-native driver
```

## 7.2 OpenClaw

Useful reference areas:

- external harness lifecycle;
- ACP integration;
- agent routing;
- separation between higher-level orchestration and harness execution.

GAIEP should copy the architectural separation, not the product architecture.

**Priority: P1 reference.**

## 7.3 OpenCode

Useful primarily as a coding-agent harness target.

Potential integration path:

```text
GAIEP AgentRun
   |
PreparedExecution
   |
OpenCode Adapter
   |
OpenCode process/session
```

The adapter must return normalized GAIEP events/provenance and must not bypass GAIEP policy.

**Priority: P2 adapter after native runtime contracts stabilize.**

## 7.4 Pi

Pi's minimal/extensible runtime is useful as a reference for keeping the execution core small and extension-driven.

Potential role:

```text
PiAdapter -> AgentDriver
```

Do not import Pi abstractions into core GAIEP contracts unless an actual integration demonstrates a need.

**Priority: P2.**

---

# 8. New / Strengthened GAIEP Contracts

The external review justifies the following contracts.

## 8.1 RuntimeScope

Purpose: monotonic authority/capability scope.

```text
RuntimeScope
  context
  tools
  skills
  workspace
  model
  memory
  budget
  network
  mutation
```

---

## 8.2 PreparedModelCall

Purpose: freeze the exact model execution request before dispatch.

```text
PreparedModelCall
  run_id
  model_deployment
  context_manifest_id
  tool_manifest_id
  skill_manifest_id
  memory_manifest_id
  policy_snapshot
  capability_snapshot
  request_hash
  budget
```

---

## 8.3 RunEvent

Purpose: append-only authoritative execution provenance.

```text
RunEvent
  event_id
  run_id
  parent_event_id
  event_type
  timestamp
  actor
  payload_hash
  source_event_ids
  artifact_refs
```

---

## 8.4 ApprovalRequest / ApprovalDecision

Purpose: explicit fail-closed approval boundary.

```text
ApprovalRequest
  approval_id
  run_id
  action
  capability
  risk
  requested_at

ApprovalDecision
  approval_id
  outcome
  decision_source
  decided_at
```

Closed outcomes should be explicit rather than represented by ambiguous booleans.

---

## 8.5 EvaluationSetManifest

Purpose: immutable evaluation-set identity and leakage controls.

```text
EvaluationSetManifest
  benchmark_id
  version
  partition
  task_set_hash
  selection_rule
  visibility_policy
  feedback_policy
  cutoff
```

---

## 8.6 EvaluationCampaign

Purpose: bind evaluation to an immutable experimental configuration.

```text
EvaluationCampaign
  campaign_id
  benchmark_manifest
  candidate_id
  model_deployment
  skill_version
  context_policy
  tool_policy
  runtime_environment
  scoring_policy
  evaluation_set_manifest
  evidence_id
```

---

# 9. Revised Evaluation Architecture

```text
Candidate
   |
Research / development
   |
Development benchmark
   |
Iteration
   |
Candidate Freeze
   |
EvaluationCampaign created
   |
Immutable EvaluationSetManifest
   |
Run controlled evaluation
   |
RunEventLog
   |
Scoring
   |
Evidence
   |
Promotion / rejection
```

No candidate changes are allowed to consume the same held-out campaign as optimization feedback.

If feedback is used to modify the candidate, a new campaign/set identity is required.

---

# 10. Revised Agent Execution Architecture

```text
Task
 |
AgentRun
 |
RuntimeScope
 |
ContextEngine
 |
PreparedExecution
 |
+----------------------+
| AgentDriver           |
|                       |
| native / DSH / Pi /   |
| OpenCode / Codex      |
+----------------------+
 |
ModelRunner
 |
Existing Gateway
 |
Certified Deployment
 |
Model
```

Tool calls must follow:

```text
Tool Registry
  |
capability check
  |
policy check
  |
approval check
  |
concurrency check
  |
execution
  |
RunEvent
```

---

# 11. Revised GreenZAlgo Research Architecture

```text
Market / Meta Data
       |
       v
Data Snapshot
       |
       v
Feature Store
       |
       v
Observation / Measurement
       |
       v
Research Hypothesis
       |
       v
Candidate Strategy / Model
       |
       +--> Vector Screening
       |
       +--> Event-Driven Validation
       |
       +--> Walk-Forward / OOS
       |
       +--> Monte Carlo / Stress
       |
       v
Evidence Generator
       |
       v
Fingerprint
       |
       v
Research Memory
       |
       v
Promotion Gate
       |
       +--> Paper / Shadow
       |
       +--> Risk Gateway
       |
       +--> Execution Gateway
       |
       v
Live
       |
       v
Monitoring
       |
       v
New Evidence
```

GAIEP owns the research orchestration/intelligence layer; GreenZAlgo V4 remains authoritative for market data, trading runtime, forecasts, execution, risk, evaluation and production promotion.

---

# 12. P0 / P1 / P2 / DEFER Backlog

## P0 — implement now

### P0.1 Context Engine archaeology

Inspect the real current implementation and capture golden fixtures before changing behavior.

### P0.2 Context contracts

Freeze `ContextManifest`, selection, budgeting and compatibility contracts.

### P0.3 PreparedModelCall

Define the immutable model-dispatch boundary.

### P0.4 EvaluationSetManifest

Define immutable evaluation-set identity and held-out protection.

### P0.5 EvaluationCampaign

Bind benchmark, candidate, runtime and scoring identity.

### P0.6 RunEvent contract

Define authoritative append-only execution events.

### P0.7 RuntimeScope contract

Define monotonic capability/authority derivation.

### P0.8 Approval seam

Define fail-closed approval request/decision semantics.

---

## P1 — after P0

- RunEvent runtime implementation
- trajectory projection
- evidence projection
- artifact lineage
- cancellation propagation
- tool concurrency classes
- subagent scope enforcement
- MCP adapter boundary
- evaluation scoring engine
- benchmark leakage checks
- GreenZAlgo research adapters
- DataBus/operational event integration

---

## P2 — later

- DeepSeek Harness adapter
- Pi adapter
- OpenCode adapter
- OpenClaw/ACP integration
- richer multi-agent orchestration
- advanced benchmark suites
- general-purpose framework marketplace/registry

---

## DEFER — intentionally not needed now

- replacing the existing Gateway;
- forking DeepSeek Harness;
- replacing GAIEP with OpenClaw;
- replacing GAIEP with Pi/OpenCode;
- replacing the Parquet lake with an operational DataHub;
- making FinceptTerminal a core dependency;
- adding ARC-AGI as a production dependency;
- adding a vector database merely because one external project uses one;
- redesigning runtime around a particular LLM/model.

---

# 13. Exact Implementation Sequence

The implementation sequence remains deliberately conservative.

```text
Context Engine archaeology
        ->
golden fixtures
        ->
contracts
        ->
legacy adapter
        ->
manifest
        ->
selector
        ->
budget
        ->
sanitization
        ->
deterministic compression
        ->
runner integration
        ->
observation
        ->
compatibility certification
```

After Context Engine compatibility is established:

```text
PreparedModelCall
        ->
RunEvent contract
        ->
RuntimeScope
        ->
Approval seam
        ->
AgentDriver boundary
        ->
Tool execution normalization
        ->
Subagent runtime
        ->
EvaluationCampaign
        ->
Evidence / certification
```

Only after these contracts stabilize should external harness adapters be attempted.

---

# 14. Architectural Invariants

The following should become explicit GAIEP invariants.

### Authority

```text
Harness != Governance Authority
Model != Governance Authority
Agent != Promotion Authority
Memory != Authorization
MCP != Authorization
Ambient Context != Authorization
```

### Scope

```text
ChildScope <= ParentScope
```

### Model execution

```text
GAIEP -> Existing Gateway
```

No second provider/Gateway abstraction.

### Provenance

```text
Authoritative execution history = RunEventLog
```

### Dispatch

```text
PreparedModelCall == actual dispatched request identity
```

### Evaluation

```text
Held-out evaluation -> measurement
Held-out evaluation -X-> same-campaign optimization feedback
```

### Evidence

```text
No promotion without sufficient evidence
```

### Self-improvement

```text
generate
  -> propose
  -> authorize
  -> experiment
  -> measure
  -> learn
```

Never:

```text
AI decides
  -> AI changes itself
  -> AI promotes itself
```

---

# 15. External Reference Decision Matrix

| Reference | Adopt concepts | Integrate now | Core dependency |
|---|---|---:|---:|
| DeepSeek Harness | Yes | No | No |
| ARC-AGI | Yes | No | No |
| FinceptTerminal | Yes | No | No |
| OpenCode | Yes | No | No |
| OpenClaw | Yes | No | No |
| Pi | Yes | No | No |

The correct strategy is **contract-first, adapter-later**.

---

# 16. Final Architecture Decision

The external research strengthens rather than replaces the existing GAIEP design.

The architecture should converge on five major planes:

```text
1. GOVERNANCE
   authorization / approval / policy / promotion

2. EXECUTION
   AgentRun / RuntimeScope / AgentDriver / ModelRunner / tools

3. PROVENANCE
   RunEvent / artifacts / trajectories / checkpoints / lineage

4. EVALUATION
   Benchmark / EvaluationSetManifest / EvaluationCampaign / scoring

5. LEARNING
   Evidence / fingerprints / GreenMemory / research feedback
```

GreenZAlgo sits as the domain system consuming and producing controlled research/trading evidence, while GAIEP supplies engineering/research intelligence and orchestration.

The architecture should remain **local-first, model-agnostic, framework-neutral, evidence-driven, and fail-closed**.

---

## 17. Immediate Next Action

Do not begin DSH/OpenCode/Pi integration yet.

Proceed with the existing GAIEP Runtime VNext implementation plan, starting with **Context Engine archaeology and golden fixtures**, while incorporating the P0 contract refinements identified above.

The external frameworks should be revisited only after the internal contracts have executable tests.
