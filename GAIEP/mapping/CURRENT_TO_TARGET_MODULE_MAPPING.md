# GAIEP Runtime VNext — Current → Target Module Mapping

**Status:** Architecture / implementation mapping
**Date:** 2026-08-21
**Source repositories inspected:**
- `harimvks/greenz-ai-engineering` — Engineering Intelligence
- `harimvks/greenz-ai-platform` — generic AI runtime/platform
- `harimvks/GreenZAlgo_V4` — market/research system

**Output repository:** `harimvks/ChatGPT`

> This is a design artifact. The three source repositories were inspected but not modified.

---

## 1. Executive Finding

The source archaeology changes the implementation recommendation in an important way:

> **GAIEP Runtime VNext should be implemented primarily as an orchestration/runtime layer in `greenz-ai-engineering`, while reusing and modestly extending the already mature generic primitives in `greenz-ai-platform`. `GreenZAlgo_V4` should remain a domain consumer and source of market/research authority, not become the home of GAIEP runtime machinery.**

The current system already has substantial pieces of the target architecture:

```text
EXISTING

AI Platform
  Gateway
  Provider Registry
  Model Registry
  Certification Gate
  Context Manifest / Builder
  Provenance
  Prompt Registry
  Governance / PromotionDecision
  Routing Observability
  Doctor / drift checks
  Immutable ledger writer

AI Engineering
  Task runner
  Gateway client
  Context assembly
  Qwen lane
  Work-package allowlist
  Overwrite guard
  Auto-fix
  Certification sweep
  Comparison
  Correction capture
  Run manifests

GreenZAlgo V4
  Registry/Engine pattern
  Research preregistration
  Evidence / confidence
  Experiment ledger
  Promotion gate
  Execution runner
  Composition ring
  Deferral ledger
  Architecture fitness tests
```

The missing piece is **not a new AI Gateway**. It is the **agentic runtime control plane** that composes these existing mechanisms into bounded multi-step work.

---

## 2. Repository Boundaries — Keep Them

The ecosystem split is explicit: `greenz-ai-platform` owns the generic Gateway/provider/model/certification/provenance machinery; `greenz-ai-engineering` owns Engineering Intelligence; `GreenZAlgo_V4` owns Market Intelligence. The dividing line is what each repository is allowed to know. fileciteturn147file0

The V4 architecture additionally states that V4 does not own an AI Gateway and that Engineering Intelligence must not acquire market vocabulary. fileciteturn219file0

Therefore:

| Concern | Correct home | Target action |
|---|---|---|
| Generic model/provider routing | `greenz-ai-platform` | **REUSE** |
| Certification gate | `greenz-ai-platform` | **REUSE** |
| Model identity | `greenz-ai-platform` | **REUSE** |
| Prompt registry | `greenz-ai-platform` | **REUSE** |
| Provenance primitives | `greenz-ai-platform` | **REUSE** |
| Governance/promotion shape | `greenz-ai-platform` | **REUSE / extend only where generic** |
| Engineering task orchestration | `greenz-ai-engineering` | **EVOLVE into GAIEP Runtime** |
| Engineering context policy | `greenz-ai-engineering` initially | **EVOLVE toward reusable Context Engine** |
| Qwen lane | `greenz-ai-engineering` | **EVOLVE into model/task policy** |
| GreenSkills | `greenz-ai-engineering` | **NEW** |
| Subagent lifecycle | `greenz-ai-engineering` | **NEW** |
| Checkpoints/rollback | `greenz-ai-engineering` | **NEW** |
| Agent trajectory | `greenz-ai-engineering` + platform observability primitives | **NEW** |
| Market/research reasoning | `GreenZAlgo_V4` | **KEEP DOMAIN-LOCAL** |
| Research governance | `GreenZAlgo_V4` | **KEEP DOMAIN-LOCAL** |
| Strategy/Mechanism promotion authority | `GreenZAlgo_V4` | **KEEP DOMAIN-LOCAL** |
| Production release promotion | `GreenZAlgo_V4` | **KEEP OPERATOR/GIT CONTROLLED** |

---

## 3. `greenz-ai-platform` — Current Surface

### 3.1 Gateway

**Current:** `gateway/gateway.py`

The Gateway already performs capability-tag filtering, classification/cloud eligibility, certified-registry selection, model resolution, provider invocation and failover. `ReasoningRequest.capability_tag` is intentionally a bare string; the platform does not own a closed capability vocabulary. fileciteturn137file0

**Target:** **REUSE unchanged as the model-routing boundary.**

Do not create `GAIEPModelGateway` or a second provider abstraction.

The agent runtime should submit a `ReasoningRequest` to this Gateway and receive a routed result.

### 3.2 Provider Registry

**Current:** `providers/registry.py` + `providers/registry_loader.py`

Provider entries contain provider/tier/capability/model reference/call options/certification requirement. Certification is intentionally scoped to the capability registration rather than the bare model. fileciteturn172file0

**Target:** **REUSE.**

This is particularly important for the three-model architecture: the same underlying model may be eligible for different capabilities with different certification requirements.

### 3.3 Model Registry

**Current:** `models/types.py` + `models/registry_loader.py`

Model identity is separated from provider/runtime state. `ModelRegistryEntry` contains model name/version/quantization/context window/runtime version and optional role. fileciteturn148file0

The split is an accepted architectural decision and `schema_version: 2` is enforced. fileciteturn161file0

**Target:** **REUSE.**

The runtime must never hard-code `qwen3.6:27b` or any future model name. Model selection remains registry + certification evidence.

### 3.4 Certification

**Current:** `certification/types.py`, `gate.py`, `ledger.py`, `scorers/`

The platform deliberately separates pure certification types/scorers from I/O and enforces the scorer trust boundary. fileciteturn217file0

The gate filters candidates using current certification records. fileciteturn233file0

**Target:** **REUSE as the hard model eligibility boundary.**

GAIEP must never interpret a model as "good enough" merely because another agent says so.

### 3.5 Context Manifest

**Current:** `context/manifest.py`

`ContextManifest` wraps deterministic request context with classification and `redaction_checked`. fileciteturn138file0

**Target:** **REUSE, then extend carefully.**

The current manifest is the correct lower-level contract. The Hermes-inspired Context Engine should sit above it and decide what goes into a manifest.

### 3.6 Context Builder

**Current:** `context/builder.py`

`ContextBuilderBase` already implements deterministic serialization, hard payload budget, forbidden-content scanning, hashing and classification stamping. The builder itself creates the `ContextManifest`, so callers cannot falsely assert `redaction_checked=True`. fileciteturn146file0

**Target:** **STRONGLY REUSE.**

This is one of the best existing foundations for the Hermes-inspired Context Engine.

Recommended evolution:

```text
ContextBuilderBase
        |
        +--> ContextSelector
        +--> ContextBudgeter
        +--> ContextCompressor
        +--> ContextManifest
```

Do not replace the current base with a generic "conversation memory" abstraction.

### 3.7 Provenance

**Current:** `provenance/response_log.py`, `disposition.py`, `correction.py`

`AIResponseLog` is append-only and records model options, context identity, prompt identity, outcome, hashes, artifact reference and `execution_id`. fileciteturn159file0

Disposition is intentionally a separate immutable record rather than mutating the response log. fileciteturn175file0

Correction is a generic capture primitive; whether a correction becomes training data is intentionally a downstream dataset decision. fileciteturn218file0

**Target:** **REUSE.**

This is already the basis for the eventual `TrajectoryRecord` evidence chain.

### 3.8 Prompt Registry

**Current:** `prompt_registry/types.py`, `ledger.py`

Prompt identity and immutable prompt revisions are already separated. The platform explicitly rejected a universal KnowledgeAsset/status abstraction. fileciteturn158file0 fileciteturn245file0

**Target:** **REUSE.**

GreenSkills should not replace Prompt Registry. A skill may reference prompts; it is a procedural asset, not another prompt version.

### 3.9 Governance

**Current:** `governance/types.py`, `ledger.py`

`PromotionDecision` is a generic, evidence-backed, scoped decision with checks, rationale, authority and immutable persistence. fileciteturn142file0 fileciteturn188file0

**Target:** **REUSE as artifact-governance primitive.**

GAIEP may use it for promotion of prompts/skills/model candidates where appropriate, but it must not use generic platform governance to override GreenZAlgo's domain-specific Strategy/Mechanism promotion rules.

### 3.10 Observability

**Current:** `observability/types.py`, `ledger.py`

`RoutingEvent` records each routing attempt, including provider/model/tier/classification/latency/failure/execution identity. fileciteturn155file0

The ledger is immutable and keyed by an explicit event ID. fileciteturn164file0

**Target:** **REUSE as the routing-observability substrate.**

GAIEP trajectory events should reference Gateway `execution_id` rather than duplicate routing logic.

### 3.11 Immutable Storage

**Current:** `storage/immutable.py`

One shared write path validates opaque record IDs and uses atomic `open("x")`, preventing path traversal and TOCTOU overwrite races. fileciteturn165file0

**Target:** **REUSE.**

Do not build another GAIEP ledger writer.

### 3.12 Doctor

**Current:** `doctor/checks.py`

Seven consistency checks cover certification shape, ranking metrics, model references, installed models, unreferenced models, digest drift and runtime-version drift. fileciteturn170file0

`greenz-ai-engineering/runner/doctor.py` is the consumer-side wiring that loads the real registry/certification ledger/runtime and reports skipped checks explicitly. fileciteturn169file0

**Target:** **REUSE and extend the same pure-check + consumer-wiring pattern for GAIEP runtime health.**

---

## 4. `greenz-ai-engineering` — Current Surface

### 4.1 Task Runner

**Current:** `runner/run_task.py`

This is already an orchestration loop:

```text
load work package
  -> build bounded context
  -> Gateway model call
  -> parse file map
  -> allowlist filter
  -> overwrite guard
  -> write
  -> gate
  -> bounded repair loop
  -> run manifest
```

The model call is injected, and the default implementation is Gateway-routed rather than raw Ollama. fileciteturn136file0

**Target:** **EVOLVE, not replace.**

`run_task()` should become one execution strategy under the future Agent Runtime rather than remain the entire runtime.

Proposed:

```text
AgentRuntime.run()
    |
    +--> TaskExecutor / WorkPackageExecutor
             |
             +--> current run_task machinery
```

### 4.2 Gateway Client

**Current:** `runner/gateway_client.py`

It constructs the real platform Gateway, loads certified registry/model registry, performs context redaction, emits routing events and returns model execution provenance. fileciteturn140file0

**Target:** **KEEP as Engineering composition adapter.**

Do not move all of this into the generic platform. Product-specific composition belongs here.

### 4.3 Engineering Context Builder

**Current:** `runner/context.py`

It assembles system prompt, work package, specification files, API surfaces, registries and coding standards. It already has explicit source/document budgets and recognizes the difference between documents and source files. fileciteturn150file0

The critical current constraint is real: V4 source files can exceed the old whole-file budget, and `orchestration/pipeline.py` is approximately 91K characters. V4 has already proposed splitting that file into stage modules. fileciteturn204file0

**Target:** **EVOLVE into the first concrete Context Selector/Assembler.**

Do not simply increase the global context window. The runtime needs a selection policy.

### 4.4 Qwen Lane

**Current:** `runner/qwen_lane.py`

The lane validates bounded task types, risk, allowlists, sensitive paths and required escalation. It now also covers platform-specific packages. fileciteturn151file0

**Target:** **EVOLVE into Model/Task Policy.**

Qwen Lane should become a policy profile, not the architecture's universal model router.

Target concept:

```text
TaskPolicy
├── capability
├── risk
├── allowed_toolsets
├── sensitive_zones
├── preferred_models
├── escalation_policy
└── approval_policy
```

The current Qwen-specific rules can become one policy implementation.

### 4.5 Certification Sweep

**Current:** `runner/sweep/`

Discovery, planning, execution and comparison are already separate. Discovery answers what would run before spending inference; execution records every completed run including failures; comparison only compares like-for-like and never promotes. fileciteturn243file0 fileciteturn235file0 fileciteturn236file0

**Target:** **REUSE.**

This becomes the empirical source for model routing policy. It should not be rewritten as an agent feature.

### 4.6 Correction Capture

**Current:** `corrections/capture.py`

Every Gateway response is automatically logged with a real output artifact; human/AI disposition is explicit and correction capture is paired with a CORRECTED disposition. fileciteturn149file0

**Target:** **REUSE.**

This is the eventual source for correction-derived benchmark cases and GreenSkills candidates.

### 4.7 Doctor

**Current:** `runner/doctor.py`

It is the consumer-specific door into platform doctor checks and includes real runtime/model-digest checks when the runtime is reachable, explicitly reporting skipped checks otherwise. fileciteturn169file0

**Target:** **EXTEND** with Agent Runtime checks, but keep pure checks in the platform where they are generic.

---

## 5. `GreenZAlgo_V4` — Current Surface Relevant to GAIEP

### 5.1 M0 is already the correct conceptual boundary

V4 explicitly treats the AI-assisted build lane as a governed subsystem. Its M0 exit test requires certified-model routing and prohibits routing to a model without a passing record. The implementation is deliberately split across the three repositories. fileciteturn226file0

**Target:** **KEEP M0 as the V4 consumer-side contract.**

GAIEP should satisfy M0; M0 should not absorb GAIEP implementation.

### 5.2 Registry–Engine pattern

V4's C2 defines a strong pattern: YAML definitions are versioned/reviewable; engines are stateless and do not encode individual definitions. There are now five live V4 registry instances, with R4 Dataset and R7 Benchmark owned by the AI platform. fileciteturn156file0

**Target:** GAIEP should use the same conceptual pattern for skills/task policies where useful:

```text
GreenSkillDefinition.yaml
       |
       v
SkillRegistry
       |
       v
SkillEngine / runtime loader
```

But **do not put GreenSkills in V4**. Engineering skills belong to `greenz-ai-engineering`; domain research procedures remain V4-specific.

### 5.3 Research Registry

`claim/registry/loader.py` loads preregistered hypotheses and refuses declarations above PROPOSED. fileciteturn179file0

**Target:** **KEEP.**

GAIEP may help propose hypotheses, but must invoke the V4 research interfaces rather than bypassing preregistration.

### 5.4 Strategy Registry

`decision/registry/loader.py` loads Strategies/StructurePlans and requires caller-supplied corroborated mechanisms. The loader does not decide corroboration itself. fileciteturn180file0 fileciteturn205file0

**Target:** **KEEP DOMAIN AUTHORITY IN V4.**

GAIEP can propose strategy changes, never silently promote them.

### 5.5 Claim / Confidence

V4's confidence is computed from evidence and never authored; the implementation is pure and as-of aware. fileciteturn187file0

The Mechanism contract deliberately has no stored confidence field. fileciteturn189file0

**Target:** **KEEP.**

GAIEP must treat computed confidence/evidence as authoritative V4 outputs, not reinterpret them through LLM confidence.

### 5.6 Research Window / Trial Ledger

The research governance layer makes evaluation contamination a ledger fact. `Window` is frozen; effective purpose is derived from Trial history rather than manually mutated. fileciteturn197file0 fileciteturn190file0

Trials record which windows they used and which earlier trials they cite, with ledger-boundary validation. fileciteturn195file0 fileciteturn193file0

**Target:** **KEEP.**

This becomes critical when GAIEP starts proposing research experiments: agent trajectory must not become an ungoverned side-channel for research state.

### 5.7 Discovery

V4's discovery engine deliberately has a small search space and reaches the lake only through `WindowView`, with an architecture test enforcing that boundary. fileciteturn231file0

**Target:** **KEEP.**

GAIEP can invoke discovery as a governed tool, not replace its lake-access controls.

### 5.8 Execution Runner

`execution/engine/runner.py` is intentionally one runner across replay/paper/live, does not branch on clock mode and checks risk unconditionally. fileciteturn183file0

**Target:** **KEEP.**

GAIEP must never create a second execution path merely because an agent is involved.

### 5.9 Orchestration Ring

V4's `orchestration/` is explicitly an adapter/composition ring. ADR-0010 says the ring may compose/adapt/persist but may not declare new domain nouns, enums, schemas or invariants. fileciteturn201file0 fileciteturn211file0

**Target:** **Use this as the GreenZ-side precedent for GAIEP AgentRuntime orchestration.**

The agent runtime should compose existing domain/platform services; it should not become a dumping ground for new domain state.

### 5.10 Pipeline Size / Context Pressure

V4's `orchestration/pipeline.py` is ~91K characters and already exceeds the engineering lane's 32K source-file ceiling. ADR-0011 proposes moving each stage into its own file while retaining a thin dispatcher. fileciteturn204file0

**Target:** **ADOPT the same principle in GAIEP Context Design:** source decomposition and context selection are complementary. Do not solve source-growth problems by blindly increasing prompt budgets.

### 5.11 Research Promotion

V4's `orchestration/promotion.py` requires both deterministic evidence preconditions and a named signatory; the machine can refuse but cannot promote on its own. fileciteturn185file0

**Target:** **HARD GAIEP INVARIANT.**

An agent may prepare promotion evidence, but domain promotion remains V4 authority.

### 5.12 Release / VPS Boundary

ADR-0014 establishes that code, configs, strategy declarations, measurement logic and approved model artifacts reach the VPS only as an operator-initiated Git release; no scp/sync inbox/manual working tree. fileciteturn166file0

ADR-0013 defines TEST and PROD runtime slots on one VPS with a common lake and structurally prevents TEST from reaching live order authority. fileciteturn167file0

**Target:** **GAIEP must not bypass this.**

A future VPS agent tool may prepare a release, but promotion remains the operator/Git release path.

---

## 6. Target GAIEP Runtime Package Map

The current architecture suggests this target in `greenz-ai-engineering`:

```text
greenz-ai-engineering/
└── runtime/
    ├── agent/
    │   ├── runtime.py          # bounded agent loop
    │   ├── run.py              # AgentRun identity
    │   └── state.py            # explicit lifecycle
    │
    ├── context/
    │   ├── selector.py         # what context to include
    │   ├── budget.py           # token/byte budget
    │   ├── compressor.py       # deterministic/controlled compression
    │   ├── manifest.py         # runtime selection manifest
    │   └── sources.py          # repository/memory/skill/task sources
    │
    ├── tools/
    │   ├── registry.py         # tool declarations
    │   ├── policy.py           # visibility != permission
    │   ├── executor.py         # controlled execution
    │   └── toolsets.py         # CODING/REVIEW/RESEARCH/etc.
    │
    ├── skills/
    │   ├── registry.py
    │   ├── loader.py
    │   ├── resolver.py
    │   └── types.py
    │
    ├── subagents/
    │   ├── manager.py
    │   ├── policy.py
    │   └── handles.py
    │
    ├── checkpoints/
    │   ├── manager.py
    │   └── rollback.py
    │
    ├── trajectory/
    │   ├── events.py
    │   ├── ledger.py
    │   └── manifest.py
    │
    ├── policy/
    │   ├── task_policy.py
    │   ├── model_policy.py
    │   └── escalation.py
    │
    └── sessions/
        ├── session.py
        └── registry.py
```

This is a **target package map**, not a commitment to create every file. The implementation phase should challenge each package before creating it.

---

## 7. Core Target Contracts

### 7.1 AgentRun

```text
AgentRun
  run_id
  task_id
  capability
  parent_run_id
  model deployment
  context_manifest_id
  tool_manifest_id
  skill_manifest_id
  workspace_scope
  status
  started_at
  finished_at
```

### 7.2 WorkspaceScope

```text
WorkspaceScope
  readonly_roots
  writable_roots
  allowed_commands
  network_policy
  secret_policy
  environment
```

For the current Mac development target:

```text
READ ONLY
~/greenz-ai-engineering
~/greenz-ai-platform
~/GreenZAlgo_V4

READ + WRITE
~/ChatGPT
```

The source repositories must remain read-only during design work.

### 7.3 ToolManifest

Every tool should declare:

```text
tool_id
version
permission_class
risk_class
workspace_scope
network_policy
approval_policy
result_limits
audit_required
```

### 7.4 SkillManifest

```text
skill_id
version
capability
applicability
prerequisites
toolsets
model_policy
validation_policy
evidence_policy
promotion_state
```

### 7.5 ContextManifest

The existing platform `ContextManifest` remains the lower-level provider context. GAIEP adds a selection manifest describing *why* each source was selected.

```text
selected_sources
excluded_sources
selection_reason
budget
compression_events
source_hashes
skill_refs
memory_refs
tool_schema_refs
```

Do not store hidden chain-of-thought.

### 7.6 TrajectoryRecord

Only observable runtime events:

```text
agent.started
context.selected
context.compressed
model.requested
model.completed
tool.visible
tool.called
tool.completed
file.read
file.write
checkpoint.created
subagent.started
subagent.completed
validation.started
validation.completed
escalation.occurred
evidence.created
disposition.recorded
```

---

## 8. Current → Target Decision Matrix

| Current implementation | Target disposition | Why |
|---|---|---|
| `platform.gateway.Gateway` | **KEEP** | already the correct routing authority |
| `platform.providers.*` | **KEEP** | generic provider mechanism |
| `platform.models.*` | **KEEP** | model identity is already separated correctly |
| `platform.certification.*` | **KEEP** | hard evidence boundary |
| `platform.context.manifest` | **KEEP** | correct lower-level context contract |
| `platform.context.builder` | **KEEP + EXTEND** | strong deterministic/redaction base |
| `platform.provenance.*` | **KEEP** | already captures model/context/prompt/output lineage |
| `platform.prompt_registry.*` | **KEEP** | prompt identity/version already solved |
| `platform.governance.*` | **KEEP** | generic artifact promotion mechanism |
| `platform.observability.*` | **KEEP** | routing telemetry already exists |
| `platform.storage.immutable` | **KEEP** | safe common ledger writer |
| `platform.doctor` | **KEEP + EXTEND** | ideal generic health-check pattern |
| `engineering.runner.run_task` | **EVOLVE** | become one executor under Agent Runtime |
| `engineering.runner.context` | **EVOLVE** | become Context Engine implementation |
| `engineering.runner.qwen_lane` | **EVOLVE** | become task/model policy profile |
| `engineering.runner.sweep` | **KEEP** | empirical certification machinery |
| `engineering.corrections` | **KEEP** | high-value feedback signal |
| `GreenZAlgo M0` | **KEEP** | consumer-side AI governance contract |
| `GreenZAlgo R1-R8 registries` | **KEEP** | domain registry-engine architecture |
| `GreenZAlgo claim/research governance` | **KEEP** | research authority remains domain-local |
| `GreenZAlgo execution runner` | **KEEP** | no second agent-specific execution path |
| `GreenZAlgo orchestration ring` | **KEEP PRINCIPLE** | composition-only precedent |
| Hermes ContextEngine concepts | **ADAPT** | context selection/compression/budgeting |
| Hermes Tool Registry concepts | **ADAPT** | tool discovery + controlled permissions |
| Hermes Skills | **ADAPT** | GreenSkills, versioned and governed |
| Hermes Subagents | **ADAPT** | bounded child authority |
| Hermes Checkpoints | **ADAPT** | integrate with Git/workspace checkpoints |
| Hermes Sessions | **ADAPT** | explicit AgentRun/session identity |
| Hermes generic memory | **REJECT AS-IS** | GreenMemory must retain GreenZ provenance/authority rules |
| Hermes generic autonomous learning | **REJECT AS-IS** | promotion/evidence must remain governed |

---

## 9. Three Critical Architecture Corrections

### Correction A — Do not build another Gateway

The existing platform Gateway is already materially mature: certification, classification, model registry, provider registry, failover and observability are integrated. fileciteturn137file0

**GAIEP Runtime is above the Gateway.**

```text
Agent Runtime
      |
      v
ReasoningRequest
      |
      v
AI Platform Gateway
      |
      v
Certified Provider
```

### Correction B — Context Engine is more important than "memory"

The current Engineering context builder already exposes the key failure mode: large repository files and growing orchestration modules can exceed context limits. fileciteturn150file0

The target should therefore prioritize:

1. source selection
2. budget allocation
3. API-surface extraction
4. targeted full-file reads
5. deterministic compression
6. provenance of selected context

before sophisticated semantic memory retrieval.

### Correction C — Agent trajectory must not become a second governance ledger

Use existing platform ledgers where they already represent the fact:

```text
RoutingEvent       -> model routing
AIResponseLog      -> model response
Disposition        -> review verdict
Correction         -> human/AI correction
CertificationRecord-> model capability evidence
PromotionDecision  -> platform artifact promotion
V4 Trial/Evidence  -> research evidence
V4 Promotion      -> domain research authority
```

Trajectory should connect these events, not duplicate them.

---

## 10. Cross-Repository Data Flow

```text
                     GAIEP Agent Runtime
                             |
          +------------------+------------------+
          |                  |                  |
       Context             Tools             Skills
          |                  |                  |
          +------------------+------------------+
                             |
                             v
                    AI Platform Gateway
                             |
                +------------+------------+
                |            |            |
              Model      Certification  Routing
                |            |            |
                +------------+------------+
                             |
                             v
                       Agent Response
                             |
             +---------------+---------------+
             |               |               |
        ResponseLog     Validation       Trajectory
             |               |               |
             v               v               v
        Correction      Evidence       AgentRun history
                             |
                 +-----------+-----------+
                 |                       |
                 v                       v
          Engineering work          V4 research tools
                 |                       |
                 v                       v
           code/tests/docs       Mechanism/Trial/Evidence
```

The V4 side remains governed by its own authority chain:

```text
Pattern
  -> Claim / Mechanism
  -> Evidence / Confidence
  -> Decision / Strategy
  -> Execution
```

V4 explicitly states that authority direction must never reverse. fileciteturn234file0

---

## 11. What Must NOT Move Into `greenz-ai-platform`

The platform's current genericity fitness rule is valuable and should remain strict.

Do **not** move these into Platform:

```text
NIFTY
options
Greeks
Strategy
Mechanism
Window
Trial
MarketAccess
Broker
Paper/Live trading authority
V4 research windows
V4 confidence formula
V4 promotion semantics
```

The platform can provide generic mechanisms for these concepts only where a second product independently needs the same mechanism.

This preserves the ecosystem rule that the platform knows neither markets nor the GreenZ product. fileciteturn131file0

---

## 12. Mac / VPS Execution Boundary

Current V4 decisions make the deployment boundary explicit: versioned logic/artifacts reach the VPS through operator-initiated Git promotion, and TEST/PROD are separate runtime slots on one VPS with a shared lake. fileciteturn166file0 fileciteturn167file0

Therefore:

```text
MAC
  GAIEP development
  local model inference
  research / engineering
  patch generation
  certification
  release preparation

       |
       | git release — operator initiated
       v

VPS
  TEST
  PROD
  scheduled runtime
  forecast/inference artifacts
  trading execution
```

An agent may prepare a release, but must not silently push/promote it to PROD.

---

## 13. Implementation Order

### P0 — Runtime contracts

Build only:

- `AgentRun`
- `WorkspaceScope`
- `ToolManifest`
- `SkillManifest`
- `ContextSelectionManifest`
- `Checkpoint`
- `TrajectoryEvent`
- `SubagentHandle`

No autonomous loop yet.

### P1 — Context Engine

Refactor the current `runner/context.py` behind:

```text
ContextSelector
ContextBudgeter
ContextCompressor
ContextManifest
```

Preserve the current fail-closed behavior.

### P2 — Tool Registry

Wrap existing:

- filesystem allowlist
- overwrite guard
- validation commands
- Git inspection
- Gateway invocation

Do not expose arbitrary shell execution.

### P3 — Checkpoint + Trajectory

Every consequential mutation gets a checkpoint and observable event sequence.

### P4 — GreenSkills

Extract repeated engineering workflows from existing prompts/templates/task runner into versioned skills.

### P5 — Subagents

Implement bounded child runs only after tool/policy/checkpoint contracts are stable.

### P6 — Multi-model orchestration

Only now implement:

- primary model
- challenger model
- reviewer model
- cost-aware escalation
- disagreement handling

Routing remains certification-backed.

### P7 — V4 research integration

Expose V4 research mechanisms as governed tools, not as direct filesystem mutation.

### P8 — Mac/VPS federation

Only after the local runtime is stable should the same tool/policy model be extended to VPS workers.

---

## 14. First Concrete Implementation Target

The first implementation should **not** be the full autonomous agent.

It should be:

```text
GAIEP Runtime Shell

AgentRun
  |
  +--> Context Engine
  |
  +--> Tool Registry
  |
  +--> existing Gateway
  |
  +--> existing run_task executor
  |
  +--> validation
  |
  +--> checkpoint
  |
  +--> trajectory
  |
  v
Evidence / Result
```

A single coding task should be able to execute through this shell and produce:

```text
AgentRun
ContextManifest
RoutingEvent
AIResponseLog
ValidationResult
Checkpoint
Trajectory
RunManifest
```

before we add subagents or complex memory.

---

## 15. Existing Design Strengths We Should Preserve

The source archaeology shows several GreenZ design principles that are actually stronger than the generic Hermes architecture and should become GAIEP invariants:

1. **Fail closed.** The Gateway refuses unscanned context and uncertified/ineligible routing. fileciteturn137file0
2. **Immutable evidence.** Certification, routing and governance records are append-only. fileciteturn237file0
3. **Explicit provenance.** Response logs carry context/prompt/model identity and output artifact references. fileciteturn159file0
4. **No silent substitution.** Gateway failover exposes `failed_over_from`. fileciteturn137file0
5. **Machine-checkable governance.** Doctor and architecture tests enforce rules instead of relying solely on prose. fileciteturn170file0
6. **Definitions vs engines.** V4's Registry–Engine pattern is a powerful model for skills/policies. fileciteturn156file0
7. **Proposal ≠ promotion.** V4 research promotion requires evidence plus a named signatory. fileciteturn185file0
8. **No hidden second execution path.** V4's runner is intentionally shared across modes. fileciteturn183file0
9. **No domain leakage.** Platform remains product-agnostic. fileciteturn131file0
10. **Operator-controlled release.** VPS changes arrive through Git promotion, not agent-side file copying. fileciteturn166file0

---

## 16. Open Questions Before Coding

These should be resolved by implementation evidence, not prematurely encoded:

1. Does `AgentRun` belong entirely in Engineering or should its pure contract eventually move to Platform after a second consumer appears?
2. Which trajectory events belong in the generic Platform observability layer versus Engineering-specific storage?
3. Should GreenSkills be stored in Engineering or in the proposed data/asset repository when/if that repository becomes real?
4. What is the minimum context-selection algorithm that beats the current static `runner/context.py` without introducing semantic-search complexity prematurely?
5. What is the minimum checkpoint abstraction that works for Git-backed code changes and later for V4 research artifacts?
6. How should a subagent's authority be represented so `child authority ⊆ parent authority` is mechanically checked?
7. Which model-policy decisions belong in provider registry YAML versus task-policy YAML?
8. How should API/cloud models be certified differently from local models while retaining the same evidence contract?
9. When a second real product consumes `greenz-ai-engineering`, which currently GreenZ-specific context/skill assumptions must be externalized? The ecosystem explicitly defers that question until the second consumer becomes real. fileciteturn229file0

---

## 17. Bottom Line

The archaeology does **not** justify a rewrite.

It justifies a controlled evolutionary layer:

```text
Current GreenZ AI stack
        |
        | already mature
        v
+-------------------------+
| Existing Platform       |
| Gateway / Certification |
| Model / Provider        |
| Context / Provenance    |
| Governance / Observe    |
+------------+------------+
             |
             v
+-------------------------+
| GAIEP Runtime VNext     |
| AgentRun                |
| Context Engine          |
| Tool Registry           |
| GreenSkills             |
| Checkpoints             |
| Subagents               |
| Trajectory              |
+------------+------------+
             |
             v
+-------------------------+
| Engineering Intelligence|
| existing runner/sweep   |
| prompts/corpus/review   |
+------------+------------+
             |
             v
+-------------------------+
| GreenZAlgo V4           |
| Research / Market AI    |
| Strategy / Execution    |
+-------------------------+
```

**The first coding milestone should therefore be the runtime contract layer + a thin AgentRuntime shell, not a new model router, not a new memory system, and not a wholesale Hermes port.**
