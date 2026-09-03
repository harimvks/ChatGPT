# GreenZAlgo V4 — Full Architecture, Design & Implementation Proposal

**Status:** Proposed implementation baseline for review
**Date:** 2026-09-03
**Purpose:** Consolidate the current GreenZAlgo V4 architecture, existing repository implementation, NIFTY forecasting design, AI/LLM research lane, data/feature lake, evidence/governance system, and deferred capabilities into one implementation-oriented specification.

> This document is a design proposal. Existing contracts and frozen architecture decisions remain authoritative where this proposal does not explicitly reopen them. New capabilities must enter through the existing registry, evidence, governance, and promotion mechanisms rather than creating parallel infrastructure.

---

## 1. Executive Architecture

GreenZAlgo V4 should be implemented as a **deterministic quantitative market-intelligence system with a bounded local AI research/engineering plane**.

The fundamental rule is:

> **AI may research, explain, classify, propose, and assist implementation; deterministic quantitative components produce the forecast, score it, and control production behaviour.**

High-level system:

```text
                           GREENZALGO V4
                                |
        +-----------------------+------------------------+
        |                        |                        |
        v                        v                        v
   DATA / LAKE              QUANTITATIVE             AI / ENGINEERING
     PLANE                     PLANE                     PLANE
        |                        |                        |
  Raw market data          Measurements              GEOS / Qwen
  Options                  Features                  Engineering AI
  Breadth                  Baselines                 Research AI
  Macro                    Challengers               Local models
  Cross-asset              Calibration               Context Engine
  Events                   Forecast                   Future agents
        |                        |                        |
        +------------------------+------------------------+
                                 |
                                 v
                         EVIDENCE / LEDGER
                                 |
                                 v
                            GOVERNANCE
                                 |
                  +--------------+--------------+
                  |                             |
                  v                             v
             Research loop                Production loop
                  |                             |
          hypothesis -> trial            approved artifact
          -> evidence -> finding         -> controlled runtime
```

The AI plane does not sit between market data and the production forecast.

---

## 2. Repository Boundaries

The current repository archaeology establishes three distinct responsibilities:

| Repository | Responsibility | Must not absorb |
|---|---|---|
| `greenz-ai-platform` | Generic AI Gateway, providers, model registry, certification, context manifest/builder, provenance, prompt registry, governance primitives, routing observability, immutable storage, doctor checks | Market-specific terminology or forecasting logic |
| `greenz-ai-engineering` | Engineering Intelligence, task execution, Qwen/model-task policy, bounded context assembly, work-package allowlists, overwrite guard, repair/autofix, certification sweep, correction capture, run manifests | Market/research authority |
| `GreenZAlgo_V4` | Market data, features, forecast models, research lifecycle, experiments, evidence, strategy/mechanism governance and production trading authority | Generic AI Gateway/runtime machinery |

The existing GAIEP mapping explicitly concludes that the missing piece is an **agentic runtime control plane**, not another Gateway, and that it should live primarily in `greenz-ai-engineering` while reusing the mature platform primitives. fileciteturn40file0L2-L3

`GreenZAlgo_V4` therefore remains the market/research authority and consumer of AI capabilities.

---

## 3. Architectural Principles

### 3.1 Deterministic production boundary

Production forecasting, calibration, risk, position decisions, and execution must not depend on an LLM response.

### 3.2 Point-in-time correctness

Every forecast input must be demonstrably available at the forecast information cutoff. Availability is a first-class property, not a comment or convention.

### 3.3 Frozen baseline means benchmark

The ATR baseline is a floor. Its lookback, quantile widths, and `p_up=0.5` are not tuning parameters. Improving the system means building a challenger that beats the baseline, not optimizing the baseline.

### 3.4 Evidence before promotion

No feature, model, regime mechanism, strategy, or AI-derived proposal becomes production authority merely because it looks plausible.

### 3.5 Registry/engine separation

Definitions are versioned data/configuration. Engines implement generic computation and must not encode individual definitions.

### 3.6 Immutable provenance

Model identity, prompt identity, context identity, execution identity, output artifact, routing event, disposition, correction and governance decisions must be reconstructable.

### 3.7 No parallel infrastructure

Do not introduce a second Gateway, second provider registry, second immutable ledger, second prompt registry, or second generic governance engine.

### 3.8 AI proposes; quantitative research decides

LLMs may identify hypotheses from accumulated evidence. The hypothesis must then be preregistered and quantitatively tested.

### 3.9 Controlled autonomy

Future multi-agent capabilities must be bounded by task policy, tool allowlists, approval gates, checkpoints and rollback. They do not receive unrestricted production authority.

---

# 4. Data Plane

## 4.1 Data layers

```text
RAW / SOURCE
   |
   v
NORMALIZED DATA
   |
   v
POINT-IN-TIME DATA
   |
   v
MEASUREMENTS
   |
   v
FEATURE SNAPSHOTS
   |
   v
FORECAST DATASET
```

The Parquet lake is the high-throughput storage layer for market breadth, options microstructure and institutional volume-imbalance research.

### Required data families

1. Price & Structure
2. Breadth & Internals
3. Options Microstructure
4. Volatility
5. India Macro
6. Global Macro
7. Cross-Asset
8. Events

A family is metadata describing a measurement. It is **not a separate forecasting model**.

---

## 4.2 Price & Structure

Core measurements:

- OHLC
- adjusted/unadjusted close where appropriate
- returns
- log returns
- gaps
- ATR
- realized volatility
- rolling range
- trend/momentum measurements
- VWAP-related measurements where available
- session structure

Price/structure is the minimum information family for the first genuine challenger.

---

## 4.3 Breadth & Internals

The V4 breadth layer should support measurements including:

- Advance/Decline count
- Advance/Decline ratio
- Advance/Decline volume
- Advance-Decline Volume Delta (ADVD)
- Percentage Above Moving Averages (PAMA)
- new highs/new lows
- sector breadth
- constituent participation
- breadth divergence versus index return
- breadth persistence and breadth regime measurements

Breadth is not a directional oracle. It is evidence available to a model at the cutoff.

---

## 4.4 Options Microstructure

The Parquet lake should support:

- option-chain snapshots
- strike
- expiry
- call/put
- bid/ask/last where available
- volume
- open interest
- change in OI
- implied volatility
- delta/gamma/vega where derivable under a declared methodology
- skew
- skew slope
- term structure
- Delta-adjusted Put-Call Ratio (D-PCR)
- Gamma Exposure (GEX) profiles
- dealer/institutional-flow proxies where methodology is explicit

`participant_oi` must remain measurement-oriented until provenance and interpretation are sufficiently strong.

No feature should be labelled "institutional" unless the source data genuinely supports participant attribution.

---

## 4.5 Volatility

Maintain distinct volatility concepts:

- ATR
- realized volatility
- EWMA volatility
- India VIX
- implied volatility
- IV/RV ratio
- volatility rank/percentile
- skew and term structure

Do not substitute ATR for sigma without measuring their empirical relationship.

A required diagnostic is:

```text
ATR / realized_sigma
```

measured across the actual NIFTY history and regimes. This diagnostic does not change the frozen ATR baseline.

---

## 4.6 India Macro

Candidate measurements:

- RBI policy rate/events
- inflation
- GDP
- PMI
- liquidity indicators
- major domestic macro surprises
- policy-event timestamps

Macro data must carry publication/release timestamps and availability semantics.

---

## 4.7 Global Macro

Candidate measurements:

- Federal Reserve policy/rate events
- US Treasury yields
- Japan/BOJ policy and JGB yields
- DXY
- major global risk indicators

Do not use a news headline as an unstructured sentiment feature when a measurable market variable or event surprise can represent the same information more objectively.

---

## 4.8 Cross-Asset

Candidate measurements:

- USD/INR
- USD/JPY
- Brent
- Gold
- S&P 500
- Nasdaq
- major Asian/global index moves
- overnight futures where legally and operationally available

Each observation requires `observed_at` and `available_at` semantics.

---

## 4.9 Events

Events should be represented as structured observations, not merely sentiment scores.

Examples:

- Fed decision
- RBI decision
- BOJ decision
- major geopolitical escalation
- war/conflict event
- major sanctions
- major commodity shock
- large macro surprise

Suggested event representation:

```text
Event
  event_id
  event_type
  occurred_at
  announced_at
  available_at
  source
  importance
  surprise_value (when measurable)
  directionality (optional, derived)
  affected_domains
```

An event can subsequently produce measurable state changes in oil, FX, volatility, global equities, etc.

---

# 5. Point-in-Time / Availability Contract

Every forecast input must satisfy:

```text
available_at <= forecast_information_cutoff
```

This applies to:

- GIFT NIFTY
- VIX
- breadth
- option chains
- macro releases
- global yields
- cross-asset prices
- news/events

For GIFT NIFTY specifically, its own session/calendar must be respected rather than blindly applying the NSE calendar.

The feature snapshot should record:

```text
snapshot_id
as_of
information_cutoff
source_dataset_version
feature_definition_version
implementation_version
availability_policy_version
```

Replay consumes snapshots rather than silently recomputing historical features.

---

# 6. Feature Store

Canonical feature identity:

```text
Dataset Version
+ Feature Definition
+ Feature Definition Version
+ Implementation Version
```

Recommended physical organization:

```text
features/
  <feature_id>/
    <feature_definition_version>/
      <dataset_name>/
        data.parquet
```

Core interfaces remain conceptually:

```text
FeatureStore
FeatureSnapshotRepository
ParquetFeatureSnapshotRepository
```

The repository should treat a feature snapshot as an immutable research artifact.

A feature implementation must not change the meaning of an existing snapshot silently.

---

# 7. Forecast Target Contract

All forecast producers must declare the same target contract before entering a common champion/challenger pool.

Required fields include:

```text
target_type
target_formula
horizon
units
resolution_rule
information_cutoff
```

Example:

```text
Target:
  next_session_return
Horizon:
  1 trading session
Units:
  return / index points
Resolution:
  declared official-market rule
```

A model predicting a 30-minute path cannot be directly compared with a model predicting next-day close unless the target is deliberately transformed and the transformation is part of the contract.

---

# 8. NIFTY Forecast Architecture

## 8.1 Forecast lifecycle

```text
Point-in-time data
        |
        v
Market-state snapshot
        |
        +------------------------------+
        |                              |
        v                              v
Frozen baseline ladder             Challenger models
        |                              |
        +---------------+--------------+
                        |
                        v
                   Calibration
                        |
                        v
                     Forecast
                        |
                        v
                    Resolution
                        |
                        v
                Performance Ledger
                        |
                        v
                     Evidence
```

---

## 8.2 Baseline ladder

The benchmark ladder is:

```text
B0      Naive
B0.5    GIFT NIFTY
B1      ATR
B1.5    India VIX
B2      EWMA
B3      Conditional Historical Distribution

C1      Price / Trend ML
C2+     Additional information-family challengers
```

B0.5 and B1.5 are benchmark rungs. They should not automatically become model features in C1.

---

## 8.3 ATR baseline

The baseline is intentionally unfitted.

Algorithm:

1. Require at least 20 trailing daily bars.
2. Compute true range per bar:

```text
TR = max(
    high - low,
    abs(high - previous_close),
    abs(low - previous_close)
)
```

3. ATR = arithmetic mean of the 20 true ranges.
4. Generate quantiles:

```text
q05 = last_close - 2.0 * ATR
q25 = last_close - 0.7 * ATR
q50 = last_close
q75 = last_close + 0.7 * ATR
q95 = last_close + 2.0 * ATR
```

5. Set:

```text
p_up = 0.5
expected_move = ATR
model_fingerprint = "unfitted"
```

These constants are conventions, not optimization parameters.

---

# 9. Scoring

## 9.1 Pinball loss

For quantile `q` at level `alpha`:

```text
alpha * (realized - q)             if realized >= q
(1 - alpha) * (q - realized)      otherwise
```

Average across declared quantiles.

This is the correct metric for a quantile forecast because underprediction and overprediction have asymmetric costs at different quantile levels.

## 9.2 Brier score

```text
Brier = (p_up - outcome)^2
```

For the baseline `p_up=0.5`, the score is structurally 0.25. That is the directional floor a genuine directional model must beat.

## 9.3 Coverage

Record whether realized outcome falls inside `[q05, q95]`.

Also measure interval width/sharpness.

## 9.4 Resolution

Never score a forecast before its declared `resolves_at` timestamp.

Partial-window scoring creates optimistic and invalid evidence.

---

# 10. Lightweight Time-Series Challenger

A lightweight time-series model is a valid challenger, but it must be evaluated as a forecasting model, not added because it is fashionable.

Candidate class:

- Microsoft/TimesFM-family model where the exact model can reproduce the GreenZ target contract; or
- another lightweight probabilistic/time-series model with deterministic, reproducible inference.

Evaluation sequence:

```text
candidate model
    |
    v
Target-contract adapter
    |
    v
same horizon / same units / same resolution
    |
    v
same walk-forward windows
    |
    v
same scoring
```

The model must not receive future observations through context construction.

Engineering metrics should be recorded separately:

- inference latency
- memory consumption
- model artifact size
- reproducibility
- stability
- cold-start time

These are not substitutes for forecast skill.

---

# 11. Challenger Family Design

Do not create independent "technical", "fundamental", "sentiment", and "news" models.

Use information-family ablations.

### C1 — Price & Structure

```text
Price/structure features -> LightGBM quantile models
```

### C2 — Price + Breadth

```text
C1 + Breadth & Internals
```

### C3 — Price + Options

```text
C1 + Options Microstructure
```

### C4 — Price + Volatility

```text
C1 + Volatility
```

### C5 — Price + India Macro

### C6 — Price + Global Macro

### C7 — Price + Cross-Asset

### C8 — Price + Events

### C9 — Only after ablations: winning combinations

A family earns inclusion only if it demonstrates incremental out-of-sample value under the declared evaluation protocol.

---

# 12. LightGBM Quantile Model

The current ML stack is deliberately small:

- `lightgbm`
- `numpy`

No assumption should be made that ARIMA, GARCH, statsmodels, torch, sklearn, Prophet, transformers, or another time-series stack exists on the forecast runtime.

The fitting surface is currently represented by the quantile model/artifact machinery. Model artifacts must contain enough identity to reproduce:

```text
model_id
model_version
quantile_level
feature_definition_version
dataset_version
implementation_version
training_window
training_cutoff
hyperparameters
random_seed
runtime/library versions
artifact hash
```

Production runtime should load a validated artifact; it should not fit a research model dynamically.

---

# 13. Model Artifact / Deployment Boundary

Research environment:

```text
Mac / research machine
    |
    v
training / experimentation
    |
    v
versioned model artifact
    |
    v
validation + governance
    |
    v
production runtime
```

If a future model such as GARCH requires a new dependency, that dependency belongs in the research environment unless and until a deliberate production-runtime decision is approved.

Do not accidentally add a research stack to the VPS merely because a researcher used it on the Mac.

---

# 14. AI / LLM Architecture

## 14.1 Role of LLMs

The local LLM is an **evidence researcher and engineering assistant**.

It may:

- analyse forecast errors;
- cluster failures;
- review market-state relationships;
- analyse research documents;
- inspect code;
- propose hypotheses;
- generate experiment specifications;
- review experiment results;
- propose implementation changes;
- assist with documentation.

It may not:

- directly generate the production forecast;
- override calibration;
- modify risk rules at runtime;
- promote a model based on its own judgement;
- bypass certification;
- bypass Git/approval control.

---

## 14.2 Current AI architecture

Existing platform/engineering components already include:

```text
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
  Doctor
  Immutable ledger

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
```

The current GAIEP mapping recommends reusing these rather than creating duplicates. fileciteturn40file0L2-L3

---

# 15. Local Model Strategy

The local Mac is the preferred research/engineering environment.

Model selection should be capability-driven rather than hard-coded.

Candidate classes include:

```text
Primary reasoning/research:
  Qwen3.8 27B MLX 4-bit / 3-bit TextOnly candidate

Fast utility:
  Qwen3.5 9B / smaller candidate

Engineering specialist:
  coding-specialist candidate if benchmark evidence justifies it
```

The model registry remains authoritative for model identity, version, quantization, context window, runtime version and role.

On a 24 GB M4 Pro, heavy models should not be assumed to coexist safely in memory. Benchmark:

- reasoning quality
- coding quality
- structured output reliability
- context handling
- tokens/sec
- peak unified memory
- stability

Do not choose the biggest model by default.

---

# 16. GEOS and Future Agent Runtime

The current GEOS/Qwen lane should remain the controlled execution mechanism.

The future architecture can evolve toward:

```text
Agent Runtime
    |
    +--> Task Executor
    +--> Context Engine
    +--> Model/Task Policy
    +--> Tool Policy
    +--> Checkpoints
    +--> Rollback
    +--> Trajectory / provenance
    |
    v
Existing Gateway
```

The existing mapping specifically recommends evolving `run_task()` rather than replacing it and reusing the platform Gateway, certification, context, provenance and immutable storage. fileciteturn40file0L2-L3

---

# 17. PraisonAI / Multi-Agent Orchestration

PraisonAI is architecturally interesting but should remain **deferred** until the existing trigger for multi-agent orchestration is satisfied.

If later adopted:

```text
PraisonAI / equivalent orchestrator
             |
             v
        bounded tools
             |
             v
       GEOS-controlled execution
             |
             v
       GreenZAlgo research API
```

It must not become:

```text
LLM agent -> production forecast -> trade
```

No second Gateway or second governance system should be created around it.

---

# 18. Research Lifecycle

The canonical research loop is:

```text
Research Idea
     |
     v
Hypothesis
     |
     v
Campaign / Preregistration
     |
     v
Feature Snapshot
     |
     v
Trial
     |
     v
Backtest / Walk-forward / Paper Session
     |
     v
Performance Series
     |
     v
Performance Claim
     |
     v
Finding
     |
     v
Mechanism
     |
     v
Governance / Promotion
```

Existing research machinery should remain authoritative. In particular:

- `Window` is the statistical research boundary;
- `WindowView` enforces that boundary;
- `ResearchScope` partitions claims/findings by scope;
- `TradingStyle` belongs in the scope/style definition rather than being pushed into unrelated core objects;
- no new generic `ResearchProfile`, mega-registry or research mega-module should be introduced merely to organize these concepts.

---

# 19. AI-Assisted Research Loop

The correct interaction between AI and quantitative research is:

```text
Resolved forecasts
       |
       v
Performance ledger
       |
       v
Evidence corpus
       |
       v
Qwen research analysis
       |
       v
Candidate hypothesis
       |
       v
Human/system preregistration
       |
       v
Quantitative trial
       |
       v
Evidence
       |
       v
Finding / mechanism
```

This makes the LLM useful without making it an untestable oracle.

---

# 20. Research Memory

GreenMemory/vector DB/knowledge graph should remain deferred where the current architecture has explicitly deferred them.

When reopened, memory must be built on existing evidence/provenance identities rather than becoming an alternative truth store.

A future memory item should reference:

```text
source artifact
source execution
feature/model identity
research scope
window/trial
finding/mechanism
confidence/evidence
```

The AI must be able to distinguish:

```text
FACT / OBSERVATION
HYPOTHESIS
EXPERIMENT RESULT
INFERENCE
UNRESOLVED CLAIM
```

---

# 21. Provenance

Every AI-assisted action should be traceable through the existing platform primitives.

Minimum chain:

```text
Agent task
  |
  v
Context manifest
  |
  v
Prompt identity
  |
  v
Model identity
  |
  v
Gateway execution_id
  |
  v
Routing event
  |
  v
AI response artifact
  |
  v
Disposition / correction
  |
  v
Trajectory / task outcome
```

The existing platform already records model options, context identity, prompt identity, outcome, hashes, artifact references and execution identity; this should be reused rather than duplicated. fileciteturn40file0L2-L3

---

# 22. Context Engine

The current `ContextBuilderBase` already provides the important safety primitives:

- deterministic serialization
- payload budget
- forbidden-content scanning
- hashing
- classification
- redaction stamping

The future context engine should evolve around it:

```text
Context Request
      |
      v
Context Selector
      |
      v
Context Budgeter
      |
      v
Context Compressor
      |
      v
ContextBuilderBase
      |
      v
ContextManifest
```

Do not replace it with a generic conversation-memory abstraction.

Context selection must be task-aware and bounded.

For repository tasks, prefer:

```text
relevant files
+ interfaces
+ tests
+ registry definitions
+ recent failure evidence
```

over indiscriminate whole-repository ingestion.

---

# 23. Agent Safety / Tool Policy

Each agent/task must declare:

```text
task_type
risk_level
allowed_tools
allowed_paths
sensitive_paths
preferred_capabilities
approval_required
max_steps
max_repairs
max_inference_budget
```

Sensitive operations:

- production configuration changes
- model promotion
- trading configuration
- data deletion
- ledger mutation
- credential access
- external side effects

must require explicit approval and/or a stronger governance gate.

---

# 24. Checkpoints and Rollback

For future multi-step engineering agents:

```text
start execution
     |
     v
checkpoint 0
     |
     v
step
     |
     v
checkpoint N
     |
     +---- failure --> rollback
     |
     v
validation
     |
     v
artifact / PR
```

Never rely on an LLM to remember its previous state.

The checkpoint should contain:

```text
execution_id
repository/ref
work-package id
changed-file hashes
tool calls
model execution ids
validation results
```

---

# 25. Testing Architecture

Testing is divided into four layers.

## 25.1 Pure unit tests

- feature calculations
- target calculation
- ATR
- quantile scoring
- calibration
- registry parsing
- availability rules
- schema validation

## 25.2 Contract tests

- Gateway request/response
- model registry
- certification gate
- context manifest
- provenance
- immutable storage
- feature snapshot identity
- forecast target identity

## 25.3 Research integrity tests

- no future data
- no leakage through resampling
- no leakage through GIFT NIFTY session handling
- no leakage through macro publication timestamps
- no leakage through option snapshots
- identical target contract across compared models
- replay consumes frozen snapshots

## 25.4 Architecture fitness tests

- V4 does not implement a second Gateway
- engineering does not import market vocabulary
- production forecast path has no LLM dependency
- deferred components remain absent until reopened
- registry definitions remain separated from engines
- immutable ledgers cannot be overwritten

---

# 26. Observability

Production and research observability should distinguish:

### Data health

- source freshness
- missingness
- timestamp anomalies
- schema drift
- calendar anomalies

### Feature health

- snapshot completeness
- stale feature rate
- distribution drift
- unexpected nulls
- implementation-version changes

### Model health

- inference latency
- artifact integrity
- prediction distribution
- calibration drift
- quantile crossing
- coverage

### Forecast health

- Pinball loss
- Brier
- interval coverage
- sharpness
- bias
- regime-specific performance

### AI health

- model routing
- latency
- context size
- memory
- failures
- correction rate
- task success rate

AI health must not be confused with forecast skill.

---

# 27. Production Forecast Runtime

The production runtime should be deliberately small:

```text
Scheduler / trigger
       |
       v
Load approved dataset snapshot
       |
       v
Load approved feature snapshots
       |
       v
Validate availability cutoff
       |
       v
Load approved model artifacts
       |
       v
Generate forecast
       |
       v
Calibration / validation checks
       |
       v
Persist forecast artifact
       |
       v
Later: resolve
       |
       v
Performance ledger
```

No LLM call is required anywhere in this path.

---

# 28. Research Runtime

Research runtime is separate:

```text
Research campaign
       |
       v
Dataset / feature snapshot
       |
       v
Trial specification
       |
       v
Model execution
       |
       v
Backtest / walk-forward
       |
       v
Evidence generator
       |
       v
Performance claim
       |
       v
Finding / mechanism
```

AI may assist before, during and after research but cannot silently alter the declared trial.

---

# 29. Promotion Gates

A candidate model must pass, at minimum:

1. schema/contract validation;
2. point-in-time validation;
3. reproducibility validation;
4. adequate evaluation sample;
5. baseline comparison;
6. walk-forward evidence;
7. calibration/coverage checks;
8. stability checks;
9. artifact/provenance checks;
10. governance approval.

Promotion must be based on evidence, not LLM narrative.

A model can be statistically better but operationally rejected if it violates latency, memory, reproducibility or governance requirements.

---

# 30. Research Sample-Size Discipline

Never tune a model against two resolutions, one model, one scope and zero performance/evidence records.

Early results are useful as plumbing validation only.

Performance-ledger evidence should accumulate before:

- hyperparameter tuning
- family selection
- regime discovery
- ensemble weighting
- model promotion

The system should distinguish:

```text
plumbing evidence
vs
model-selection evidence
```

---

# 31. Regime Architecture

Regime detection is deferred until the relevant trigger/evidence threshold is satisfied.

When implemented, prefer:

```text
P(regime_1 | state)
P(regime_2 | state)
...
P(regime_n | state)
```

rather than a single hard label.

The regime definition must have a canonical registry identity and version.

Before implementation, correct any governance/documentation reference that points to the wrong measurement/ledger row. A regime gate is not enforceable if its cited prerequisite does not actually represent regime state.

---

# 32. Forecast Attribution

Forecast attribution should be added only after a challenger demonstrates genuine skill.

Possible attribution dimensions:

```text
Price / Structure
Breadth
Options
Volatility
India Macro
Global Macro
Cross-Asset
Events
```

Do not build attribution for an unskilled model and then use the explanations as evidence of skill.

Attribution is explanatory evidence, not proof of predictive causality.

---

# 33. Failure Clustering

Failure clustering is a strong future AI/research capability.

Input:

```text
forecast
actual
market state
feature state
model state
regime/state probabilities
```

Output:

```text
failure cluster
candidate mechanism
supporting examples
counterexamples
confidence
```

The LLM can assist with semantic clustering, but quantitative clustering and statistical validation should remain reproducible.

---

# 34. What NOT to Implement

The following should not be introduced merely for architectural completeness:

- second AI Gateway
- second model/provider registry
- universal KnowledgeAsset abstraction
- research mega-module
- generic ResearchProfile when existing scope machinery is sufficient
- LLM inside production forecast path
- unrestricted autonomous trading agent
- giant always-loaded repository context
- vector DB before its trigger
- knowledge graph before its trigger
- multi-agent orchestration before its trigger
- GARCH dependency on production VPS without an explicit decision
- tuning of the frozen ATR baseline
- sentiment score as an unexplained catch-all macro/news variable
- model comparisons across incompatible targets/horizons

---

# 35. Implementation Phases

## Phase 0 — Architecture hygiene

1. Correct stale/incorrect architecture citations.
2. Establish the canonical information-family vocabulary.
3. Verify registry ownership and repository boundaries.
4. Verify deferred items and triggers.
5. Verify forecast target contract.

**Exit:** architecture consistency tests pass.

---

## Phase 1 — Data/availability hardening

1. Complete point-in-time metadata.
2. Validate trading calendars.
3. Validate GIFT NIFTY availability/session handling.
4. Validate India VIX timestamps.
5. Validate macro publication timestamps.
6. Validate options snapshot timestamps.
7. Implement/reconcile feature snapshot identity.
8. Build replay from frozen snapshots.

**Exit:** no known leakage paths.

---

## Phase 2 — Baseline evidence

1. Reproduce ATR baseline exactly.
2. Implement/validate B0.
3. Implement/validate B0.5 GIFT NIFTY.
4. Implement/validate B1.5 India VIX.
5. Implement B2 EWMA.
6. Implement B3 conditional historical distribution.
7. Measure coverage, sharpness and Pinball.
8. Measure ATR/sigma relationship.

**Exit:** baseline ladder is reproducible and scored.

---

## Phase 3 — C1 LightGBM

1. Define price/structure feature contract.
2. Build training dataset from frozen snapshots.
3. Fit one model per declared quantile.
4. Produce versioned model artifact.
5. Run walk-forward evaluation.
6. Compare with complete baseline ladder.
7. Record PerformanceSeries/Claims.

**Exit:** C1 either demonstrates skill or is rejected; no tuning by hindsight.

---

## Phase 4 — Time-series challenger

1. Select lightweight TimesFM-family candidate or equivalent.
2. Build target-contract adapter.
3. Verify horizon/units/resolution.
4. Evaluate identical windows.
5. Compare Pinball/coverage/sharpness.
6. Record engineering cost separately.

**Exit:** quantitative decision on whether the TS model adds value.

---

## Phase 5 — Information-family ablations

Run one family at a time:

```text
C1 + Breadth
C1 + Options
C1 + Volatility
C1 + India Macro
C1 + Global Macro
C1 + Cross-Asset
C1 + Events
```

Each arm is preregistered.

**Exit:** incremental-value map of the information families.

---

## Phase 6 — Research AI integration

1. Expose read-only research APIs/tools.
2. Connect Qwen through the existing Gateway.
3. Use existing provenance/context mechanisms.
4. Build forecast-error analysis workflow.
5. Build hypothesis proposal workflow.
6. Require preregistration before trials.

**Exit:** AI produces auditable hypotheses without affecting production forecasts.

---

## Phase 7 — Agent runtime evolution

Only after the deferred trigger is met:

1. Evolve `run_task()` into an Agent Runtime execution strategy.
2. Add task policies.
3. Add bounded tools.
4. Add checkpoints.
5. Add rollback.
6. Add trajectory records.
7. Reuse Gateway/model registry/certification/provenance.
8. Evaluate PraisonAI or another orchestrator as an adapter, not as the authority.

**Exit:** bounded multi-step AI work is reproducible and governable.

---

# 36. Proposed Module Ownership

```text
GREENZALGO_V4
├── data/
├── datasets/
├── features/
├── measurements/
├── forecasts/
├── models/
├── calibration/
├── resolution/
├── performance/
├── research/
├── evidence/
├── governance/
└── runtime/

GREENZ-AI-PLATFORM
├── gateway/
├── providers/
├── models/
├── certification/
├── context/
├── provenance/
├── prompt_registry/
├── governance/
├── observability/
├── storage/
└── doctor/

GREENZ-AI-ENGINEERING
├── runner/
├── task execution
├── context composition
├── task/model policy
├── Qwen lane
├── sweep/
├── corrections/
├── skills/
└── future agent runtime
```

The exact existing paths should be preserved where already implemented; this is a target ownership map, not permission to reorganize repositories gratuitously.

---

# 37. API/Contract Shape

A forecast request should conceptually contain:

```text
ForecastRequest
  instrument
  target_contract
  information_cutoff
  feature_snapshot_id
  model_declaration_id
  calibration_version
```

A forecast artifact should contain:

```text
ForecastArtifact
  forecast_id
  instrument
  target_contract
  information_cutoff
  resolves_at
  model_declaration_id
  model_artifact_id
  feature_snapshot_id
  quantiles
  p_up
  expected_move
  calibration_id
  created_at
  implementation_version
  artifact_hash
```

A resolution artifact should contain:

```text
Resolution
  forecast_id
  realized_value
  resolved_at
  resolution_rule
  scoring_version
```

A performance record should reference the immutable forecast and resolution identities.

---

# 38. Research Scope and Style

The existing research architecture should continue using the established separation:

```text
Window
   |
   v
WindowView
   |
   v
Trial / PerformanceSeries
   |
   v
PerformanceClaim
   |
   v
Finding
```

`ResearchScope` partitions claims/findings by:

```text
scope_id
TradingStyle
versioned style definition
```

Do not push TradingStyle into Window/Forecast/ModelDeclaration unless a future architecture decision explicitly reopens that boundary.

---

# 39. Definition of Done

The V4 forecast architecture is ready for serious model research only when:

- data is point-in-time correct;
- feature snapshots are immutable/versioned;
- target contracts are explicit;
- baseline ladder is reproducible;
- resolution is exact;
- scoring is delayed until resolution;
- performance evidence is sufficient;
- LightGBM challenger is reproducible;
- time-series challenger can be evaluated under the same target;
- family ablations are preregistered;
- AI remains outside the production forecast path;
- all AI calls are provenance-traceable;
- promotion is evidence-backed;
- architecture fitness tests prevent boundary drift.

---

# 40. Final Target State

```text
                              +----------------------+
                              |   LOCAL AI RESEARCH  |
                              | Qwen / future agents |
                              +----------+-----------+
                                         |
                                   hypotheses /
                                    analysis
                                         |
                                         v
+----------------+       +-------------------------------+       +----------------+
| DATA SOURCES   | ----> | POINT-IN-TIME DATA / FEATURES | ----> | FORECAST ENGINE|
| price          |       | Parquet lake                  |       | B0..B3         |
| options        |       | snapshot identity             |       | C1 LightGBM    |
| breadth        |       | availability                  |       | Cx TS / family |
| macro          |       +-------------------------------+       +-------+--------+
| cross-asset    |                                                        |
| events         |                                                        v
+----------------+                                                 CALIBRATION
                                                                         |
                                                                         v
                                                                    FORECAST
                                                                         |
                                                                         v
                                                                    RESOLUTION
                                                                         |
                                                                         v
                                                               PERFORMANCE / EVIDENCE
                                                                         |
                                        +--------------------------------+----------------+
                                        |                                                 |
                                        v                                                 v
                               RESEARCH FINDING                                GOVERNANCE / PROMOTION
                                        |                                                 |
                                        v                                                 v
                                NEW HYPOTHESIS                              APPROVED PRODUCTION ARTIFACT
                                        |                                                 |
                                        +---------------------> TRIAL <-------------------+
```

The resulting system is deliberately asymmetric:

- **data and quantitative code are authoritative for numbers;**
- **research governance is authoritative for conclusions;**
- **the AI layer is authoritative for neither.**

That separation gives GreenZAlgo V4 the ability to become substantially more intelligent without turning the forecast engine into an opaque AI dependency.

---

## Implementation Authority

Before implementation, reconcile each proposed change against the existing authoritative repository contracts and architecture/deferral ledgers. Where this proposal describes a future capability, it must not be interpreted as an instruction to activate that capability before its trigger.

The existing GAIEP source-archaeology mapping is the primary reference for the AI-platform/engineering boundary and explicitly recommends reuse of the existing Gateway, model registry, certification, context, provenance, governance, observability and immutable-storage primitives rather than rebuilding them. fileciteturn40file0L2-L3

**Recommended immediate work:** Phase 0 → Phase 1 → Phase 2 → C1, before adding new orchestration or memory infrastructure.
