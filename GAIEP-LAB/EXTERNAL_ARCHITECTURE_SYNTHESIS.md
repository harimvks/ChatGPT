# GAIEP VNext — External Architecture Synthesis

**Status:** Research / architecture decision input  
**Scope:** DeepSeek Harness, ARC-AGI, FinceptTerminal, MarkItDown, OpenCode, OpenClaw, Pi  
**Repository:** `harimvks/ChatGPT` / `GAIEP-LAB`  
**Decision principle:** External projects are references or isolated adapters; GAIEP remains authoritative.

---

## 1. Executive Summary

The external architecture review strengthens the current GAIEP direction and identifies several contracts that should be explicit before deeper runtime implementation.

| Reference | Primary value to GAIEP / GreenZAlgo |
|---|---|
| DeepSeek Harness | Agent runtime, plugin seams, sessions/events, approval, scoped capabilities |
| ARC-AGI | Evaluation discipline, held-out testing, exact scoring, anti-overfitting methodology |
| FinceptTerminal | Financial workstation, quant research, market data, MCP, AI-quant workflows |
| MarkItDown | Heterogeneous document ingestion, canonical conversion, converter registry/plugins |
| OpenCode | Coding-agent execution / harness reference |
| OpenClaw | Agent orchestration, ACP, external harness lifecycle and routing |
| Pi | Minimal/extensible coding-agent runtime and replaceable agent loop |

### Core conclusion

Do **not** fork or make any external project the GAIEP core.

GAIEP should expose stable internal contracts around:

1. `AgentRun`
2. `RuntimeScope`
3. `ContextEngine`
4. `PreparedModelCall`
5. `AgentDriver` / `HarnessAdapter`
6. `ToolRegistry` + policy
7. `ApprovalRequest` / `ApprovalDecision`
8. append-only `RunEvent` provenance
9. `RawSource` / `CanonicalArtifact` / `ContextArtifact`
10. `EvaluationCampaign`
11. `EvaluationSetManifest`
12. Evidence / certification / promotion
13. GreenMemory / research memory

External implementations can then sit behind those boundaries.

---

## 2. Existing GAIEP Architectural Invariants

The current GAIEP design already separates model execution, tools, context, skills, memory, mutation authority, evidence, and governance.

`AgentRun` is the durable identity tying together execution, context, tools, skills, memory, workspace scope, and evidence.

The existing platform Gateway already performs model/provider/deployment routing. **GAIEP must not build a second model provider/Gateway abstraction.** GAIEP calls the existing Gateway and remains model-agnostic.

The Parquet lake and Feature Store remain authoritative for GreenZAlgo historical/analytical data. Operational buses are complementary, not replacements.

External frameworks must remain isolated until an actual integration demonstrates compatibility with GAIEP contracts.

---

# 3. Target Architecture

```text
                              GAIEP
                                |
          +---------------------+---------------------+
          |                     |                     |
      Governance             Evidence             Research
          |                     |                     |
          +---------------------+---------------------+
                                |
                         AgentRun Contract
                                |
                          RuntimeScope
                                |
                 +--------------+--------------+
                 |                             |
          ContextEngine                   PolicyEngine
                 |                             |
                 +--------------+--------------+
                                |
                     Prepared Execution
                                |
                         AgentDriver API
                                |
       +------------------------+------------------------+
       |             |             |             |        |
    native          DSH          Pi        OpenCode     Codex
       |             |             |             |        |
       +------------------------+------------------------+
                                |
                           ModelRunner
                                |
                        Existing Gateway
                                |
                       Certified Deployment
                                |
                              Model
                                |
                 +--------------+--------------+
                 |                             |
               Tools                       Subagents
                 |                             |
                 +--------------+--------------+
                                |
                         Append-only RunEvent
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

A separate ingestion plane feeds the Context Engine:

```text
Raw Source
   |
Source Identity / Hash
   |
Ingestion Adapter Registry
   |
Converter / Parser
   |
Canonical Artifact
   |
Metadata / Fingerprint
   |
Corpus Store
   |
Context Engine
   |
Context Artifact
   |
PreparedModelCall
```

---

# 4. DeepSeek Harness Findings

DeepSeek Harness is the strongest external reference for the agent execution substrate.

## 4.1 Adopt: replaceable Agent Driver

DeepSeek separates the public agent abstraction from the concrete agent loop. This validates separating GAIEP's `AgentRun` / agent contract from its runtime implementation.

```text
AgentRun / Agent Contract
          |
          v
     AgentDriver
          |
     +----+----+----+----+
     |    |    |    |    |
    DSH  Pi OpenCode Codex native
```

The driver executes a prepared run. It does not become the governance authority.

**Priority: P0 architectural contract; P1 implementation.**

## 4.2 Adopt: provider-neutral model boundary

Keep:

```text
GAIEP -> existing Gateway -> certified deployment -> model
```

Do not import a second provider abstraction into GAIEP. If DSH is integrated, create an adapter around DSH rather than allowing its provider layer to become a second GAIEP Gateway.

**Priority: DEFER direct DSH integration.**

## 4.3 Adopt: immutable PreparedModelCall

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

Preparation occurs before dispatch. Downstream layers must not silently rewrite the request.

**Invariant:** `PreparedModelCall == dispatched request identity`.

**Priority: P0.**

## 4.4 Adopt: append-only RunEvent model

GAIEP should evolve toward an append-only typed execution log:

```text
run.created
run.authorized
context.committed
model.requested
model.started
model.completed
tool.called
tool.completed
approval.requested
approval.decided
checkpoint.created
validation.completed
artifact.created
evidence.created
disposition.finalized
run.cancelled
```

Derived projections include model-visible trajectory, execution summary, artifact lineage, evidence graph, cost/latency metrics, and failure corpus.

`TrajectoryRecord` should become a projection rather than the sole source of truth.

**Priority: P0 design; P1 implementation after Context Engine.**

## 4.5 Adopt: formal Approval seam

```text
ApprovalRequest -> ApprovalService -> ApprovalDecision
```

Approval is not authorization:

```text
Authorization = is this action permitted?
Approval      = if approval is required, was this specific action approved?
```

Approval must fail closed and be durably auditable.

**Priority: P0 contract; P1 runtime.**

## 4.6 Adopt: RuntimeScope

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

For subagents:

```text
ChildScope <= ParentScope
ChildTools <= ParentTools
ChildSkills <= ParentSkills
ChildMemory <= ParentMemoryPolicy
ChildWorkspace <= ParentWorkspace
ChildAuthority <= ParentAuthority
ChildBudget <= ParentRemainingBudget
```

Ambient context may propagate identity but is never authorization or durable provenance.

**Priority: P0 contract; P1 implementation with subagents.**

## 4.7 Adopt: cancellation semantics

Cancellation propagates through:

```text
parent run -> child run -> model call -> tool call
```

Recommended states: `requested`, `propagated`, `acknowledged`, `forced`, `completed`.

**Priority: P1.**

---

# 5. ARC-AGI Findings

ARC-AGI is primarily an evaluation methodology and task corpus, not an agent runtime. Its strongest relevance is evaluation and evidence integrity.

## 5.1 Adopt: development vs held-out evaluation

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

**Invariant:** a held-out result cannot become same-campaign optimization feedback. If feedback changes the candidate, create a new campaign/set identity.

**Priority: P0.**

## 5.2 Adopt: EvaluationSetManifest

```text
EvaluationSetManifest
- dataset_id
- dataset_version
- partition
- task_set_hash
- selection_rule
- release_timestamp
- visibility_policy
- evaluation_cutoff
- feedback_policy
```

Immutable for a campaign.

**Priority: P0.**

## 5.3 Adopt: exact correctness predicates

Evaluations should distinguish correctness, quality, policy compliance, provenance completeness, resource usage, and reproducibility.

**Priority: P1.**

## 5.4 Adopt: generalization as a first-class measurement

```text
in-domain performance
held-out performance
cross-task / cross-regime generalization
```

For GreenZAlgo the analogue is training period, validation period, walk-forward period, strict OOS period, and future live/shadow period, with leakage controls.

**Priority: P0 design; P1 implementation.**

---

# 6. FinceptTerminal Findings

FinceptTerminal is primarily relevant to GreenZAlgo's financial application/research layer, not GAIEP's core governance layer.

## 6.1 Adopt concept: operational DataHub vs analytical lake

Retain:

```text
Parquet Lake       = durable historical / analytical data
Feature Store      = reproducible feature snapshots
Operational DataBus = low-latency distribution
```

Recommended flow:

```text
Parquet Lake -> Feature Store -> Operational DataBus
                                  |
                           +------+------+
                           |      |      |
                       Indicators Strategies Research
```

Do not replace the Parquet lake with an operational bus.

**Priority: P1.**

## 6.2 Adopt concept: bounded financial contexts

Preserve:

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

Prefer typed contracts/events over dependency-heavy direct imports.

**Priority: P1.**

## 6.3 Adopt concept: AI Quant Lab workflow

Use the research-loop pattern:

```text
Research Idea -> Hypothesis -> Universe -> Data Snapshot
-> Feature / Strategy Candidate -> Measurement -> Screening
-> Event Validation -> Walk-Forward / OOS -> Stress / Monte Carlo
-> Evidence -> Fingerprint -> Research Memory -> Promotion Gate
```

GAIEP/GreenZAlgo must retain stronger point-in-time, provenance, evidence and promotion controls.

**Priority: P1.**

## 6.4 Adopt concept: MCP as tool transport, not governance

```text
Tool Registry -> Policy -> Approval -> MCP/transport -> Tool execution
```

MCP is interoperability, not authorization.

**Priority: P1.**

## 6.5 Do not adopt as core dependency

Do not make FinceptTerminal a GAIEP or GreenZAlgo core dependency. Use concepts selectively or isolate integrations behind adapters.

**Priority: DEFER direct dependency.**

---

# 7. MarkItDown Findings

MarkItDown is primarily relevant to the **GAIEP ingestion and corpus/context plane**. It is a document/file-to-Markdown conversion framework with a converter registry and plugin architecture.

## 7.1 Adopt concept: converter registry

Use the architectural pattern, not the external API as a GAIEP contract:

```text
IngestionService
      |
DocumentTypeRegistry
      |
 +----+-----+-----+-----+
 |          |           |
 PDF       DOCX        XLSX      other adapters
 |          |           |
 +----------+-----------+
            |
      Canonical Artifact
```

Converters should be replaceable and independently versioned.

**Priority: P0 architecture; P1 implementation.**

## 7.2 Adopt: RawSource -> CanonicalArtifact -> ContextArtifact

Do not make Markdown the system of record.

```text
RawSource
  = immutable original bytes / source response

CanonicalArtifact
  = deterministic normalized representation

ContextArtifact
  = selected material actually supplied to an AgentRun
```

Lineage:

```text
RawSource
  -> converter/version/policy
  -> CanonicalArtifact
  -> fingerprint / metadata
  -> Corpus Store
  -> ContextEngine
  -> ContextArtifact
  -> PreparedModelCall
```

This prevents arbitrary document formats from leaking into the Context Engine.

**Priority: P0.**

## 7.3 Adopt: conversion provenance

Each canonical artifact should retain:

```text
source_hash
converter_id
converter_version
conversion_policy_hash
canonical_content_hash
```

This should be incorporated into corpus fingerprints and evidence lineage.

**Priority: P0.**

## 7.4 Do not collapse conversion and semantic extraction

Conversion should be followed by separate stages where needed:

```text
conversion -> segmentation -> metadata extraction
-> entity/fact extraction -> chunking -> fingerprinting -> retrieval/indexing
```

Structured documents should retain structured representations where lossless preservation matters; Markdown is a representation, not necessarily canonical truth.

**Priority: P1.**

## 7.5 Network policy

URL-capable ingestion must remain behind GAIEP network/tool policy:

```text
Agent/request -> network policy -> approved fetcher -> RawSource -> converter
```

An external URL must not become implicit unrestricted network access.

**Priority: P0.**

## 7.6 Recommended GAIEP ingestion contracts

```text
SourceArtifact
- source_id
- source_uri/path
- media_type
- filename
- content_hash
- source_timestamp

CanonicalArtifact
- artifact_id
- source_id
- converter_id
- converter_version
- conversion_policy_hash
- representation
- representation_hash
```

A future `ContextArtifact` should reference the canonical artifact and selection/projection metadata.

**Priority: P0 contract; P1 implementation.**

## 7.7 Dependency decision

**Do not make MarkItDown a core GAIEP dependency yet.** Evaluate it behind `IngestionAdapter` and retain the ability to use native or other converters where structured fidelity, licensing, performance or provenance requirements differ.

**Priority: DEFER direct dependency; P1 isolated evaluation.**

---

# 8. OpenCode / OpenClaw / Pi Findings

These systems are agent execution infrastructure, not GAIEP governance.

## 8.1 Common rule

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

## 8.2 OpenClaw

Useful references: external harness lifecycle, ACP integration, agent routing, and separation between orchestration and harness execution.

Copy the separation, not the product architecture.

**Priority: P1 reference.**

## 8.3 OpenCode

```text
GAIEP AgentRun -> PreparedExecution -> OpenCode Adapter
-> OpenCode process/session -> normalized GAIEP RunEvents
```

The adapter must not bypass GAIEP policy or provenance.

**Priority: P2.**

## 8.4 Pi

Pi is useful as a reference for a small, extensible execution core.

```text
PiAdapter -> AgentDriver
```

Do not import Pi abstractions into core GAIEP contracts without an actual integration need.

**Priority: P2.**

---

# 9. New / Strengthened GAIEP Contracts

## 9.1 RuntimeScope

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

Purpose: monotonic authority/capability scope.

## 9.2 PreparedModelCall

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

Purpose: freeze exact model-dispatch identity.

## 9.3 RunEvent

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

Purpose: authoritative append-only execution provenance.

## 9.4 ApprovalRequest / ApprovalDecision

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

Closed outcomes should be explicit rather than ambiguous booleans.

## 9.5 RawSource / CanonicalArtifact / ContextArtifact

```text
RawSource
  immutable source identity + bytes/response

CanonicalArtifact
  normalized representation + converter provenance

ContextArtifact
  selected/derived material supplied to an AgentRun
```

Purpose: keep ingestion, corpus truth and model context distinct.

## 9.6 EvaluationSetManifest

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

Purpose: immutable evaluation-set identity and leakage controls.

## 9.7 EvaluationCampaign

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

Purpose: bind evaluation to an immutable experimental configuration.

---

# 10. Revised Ingestion + Context Architecture

```text
External Sources
      |
      v
RawSource Registry
      |
      v
IngestionAdapter Registry
      |
      +--> MarkItDown-style converters
      +--> native structured parsers
      +--> domain-specific adapters
      |
      v
CanonicalArtifact
      |
      +--> metadata
      +--> fingerprint
      +--> source lineage
      |
      v
Corpus Store
      |
      v
ContextEngine
      |
      v
ContextArtifact
      |
      v
PreparedModelCall
```

`ContextEngine` should consume canonical artifacts and corpus metadata. It should not be responsible for understanding every external file format.

---

# 11. Revised Agent Execution Architecture

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
+-------------------------------+
| AgentDriver                    |
| native / DSH / Pi / OpenCode  |
| / Codex                        |
+-------------------------------+
 |
ModelRunner
 |
Existing Gateway
 |
Certified Deployment
 |
Model
```

Tool calls:

```text
Tool Registry -> capability check -> policy check -> approval check
-> concurrency check -> execution -> RunEvent
```

---

# 12. Revised Evaluation Architecture

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

---

# 13. Revised GreenZAlgo Research Architecture

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
       +--> Event-Driven Validation
       +--> Walk-Forward / OOS
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
       +--> Risk Gateway
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

GAIEP owns research orchestration/intelligence and governance. GreenZAlgo V4 remains authoritative for market data, trading runtime, forecasts, execution, risk, evaluation and production promotion.

---

# 14. P0 / P1 / P2 / DEFER Backlog

## P0 — implement/contract now

1. Context Engine archaeology and golden fixtures.
2. Freeze `ContextManifest`, selection, budgeting and compatibility contracts.
3. Define `PreparedModelCall`.
4. Define `RunEvent`.
5. Define `RuntimeScope`.
6. Define fail-closed `ApprovalRequest` / `ApprovalDecision`.
7. Define `EvaluationSetManifest` and held-out protection.
8. Define `EvaluationCampaign`.
9. Define ingestion identity boundary: `RawSource` / `CanonicalArtifact` / `ContextArtifact`.
10. Ensure network-capable ingestion is policy-controlled.

## P1 — after P0

- RunEvent runtime implementation
- trajectory/evidence projections
- artifact lineage
- cancellation propagation
- tool concurrency classes
- subagent scope enforcement
- MCP adapter boundary
- evaluation scoring engine
- benchmark leakage checks
- GreenZAlgo research adapters
- DataBus/operational event integration
- isolated MarkItDown evaluation
- converter registry and canonical-artifact implementation

## P2 — later

- DeepSeek Harness adapter
- Pi adapter
- OpenCode adapter
- OpenClaw/ACP integration
- richer multi-agent orchestration
- advanced benchmark suites
- additional ingestion/converter plugins

## DEFER — intentionally not needed now

- replacing the existing Gateway;
- forking DeepSeek Harness;
- replacing GAIEP with OpenClaw;
- replacing GAIEP with Pi/OpenCode;
- replacing the Parquet lake with an operational DataHub;
- making FinceptTerminal a core dependency;
- making MarkItDown a mandatory core dependency;
- adding ARC-AGI as a production dependency;
- adding a vector database merely because an external project uses one;
- redesigning runtime around a particular LLM/model.

---

# 15. Exact Implementation Sequence

The implementation sequence remains conservative:

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
RawSource / CanonicalArtifact ingestion boundary
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

Only after these contracts stabilize should external harness or converter adapters be attempted.

---

# 16. Architectural Invariants

### Authority

```text
Harness != Governance Authority
Model != Governance Authority
Agent != Promotion Authority
Memory != Authorization
MCP != Authorization
Ambient Context != Authorization
Converter != Governance Authority
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

### Ingestion provenance

```text
RawSource -> CanonicalArtifact -> ContextArtifact
```

Each transformation must retain source identity and derivation metadata.

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

# 17. External Reference Decision Matrix

| Reference | Adopt concepts | Integrate now | Core dependency |
|---|---|---:|---:|
| DeepSeek Harness | Yes | No | No |
| ARC-AGI | Yes | No | No |
| FinceptTerminal | Yes | No | No |
| MarkItDown | Yes | No | No |
| OpenCode | Yes | No | No |
| OpenClaw | Yes | No | No |
| Pi | Yes | No | No |

The strategy remains **contract-first, adapter-later**.

---

# 18. Final Architecture Decision

The external research strengthens rather than replaces the existing GAIEP design.

The architecture converges on six major planes:

```text
1. INGESTION
   RawSource / converters / CanonicalArtifact / ContextArtifact

2. GOVERNANCE
   authorization / approval / policy / promotion

3. EXECUTION
   AgentRun / RuntimeScope / AgentDriver / ModelRunner / tools

4. PROVENANCE
   RunEvent / artifacts / trajectories / checkpoints / lineage

5. EVALUATION
   Benchmark / EvaluationSetManifest / EvaluationCampaign / scoring

6. LEARNING
   Evidence / fingerprints / GreenMemory / research feedback
```

GreenZAlgo sits as the domain system consuming and producing controlled research/trading evidence, while GAIEP supplies engineering/research intelligence and orchestration.

The architecture remains **local-first, model-agnostic, framework-neutral, evidence-driven, and fail-closed**.

---

## 19. Immediate Next Action

Do not begin DSH/OpenCode/Pi integration yet.

Proceed with the existing GAIEP Runtime VNext implementation plan, starting with **Context Engine archaeology and golden fixtures**, while incorporating the P0 contract refinements above.

In parallel, define the ingestion boundary so document conversion can be evaluated without contaminating the core contracts. MarkItDown should be evaluated as an isolated converter implementation only after the `RawSource -> CanonicalArtifact -> ContextArtifact` contracts are stable.

External frameworks should be revisited only after internal contracts have executable tests.
