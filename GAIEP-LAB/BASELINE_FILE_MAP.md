# GAIEP-LAB Initial Baseline File Map

**Baseline commits:** see `provenance/UPSTREAM_SNAPSHOTS.yaml`.

This is an initial mapping from the actual repositories. It is intentionally conservative: existing mechanisms are marked KEEP/EXTEND until the complete source inventory proves otherwise.

| Upstream | Existing component | Current role | VNext disposition |
|---|---|---|---|
| greenz-ai-platform | `context/manifest.py` | `AIRequestContext`, `ContextManifest`, prompt-builder protocol | KEEP; extend for VNext contracts |
| greenz-ai-platform | `context/builder.py` | reusable deterministic/bounded context builder base | KEEP; extend rather than replace |
| greenz-ai-platform | `context/redaction.py` | forbidden-content/redaction mechanism | KEEP; integrate with Context Engine |
| greenz-ai-platform | `context/prompt_builder.py` | provider-facing prompt rendering protocol | KEEP; adapter boundary |
| greenz-ai-platform | `gateway/gateway.py` | capability routing, local-first selection, fail-closed behavior, visible failover | KEEP; become Model Gateway boundary |
| greenz-ai-platform | `certification/gate.py` | certification-aware registry filtering/ranking | KEEP; expose ModelPolicy eligibility |
| greenz-ai-platform | `models/*` | model identity/registry/training-candidate concepts | KEEP; extend only where required |
| greenz-ai-platform | `provenance/*` | response/disposition/correction provenance | KEEP; integrate with Evidence |
| greenz-ai-platform | `observability/*` | routing events/metrics | KEEP; extend to AgentRun/subagent events |
| greenz-ai-platform | `governance/*` | promotion decision mechanisms | KEEP; become Governance boundary |
| greenz-ai-platform | `storage/*` | immutable YAML ledger write path | KEEP; do not duplicate |
| greenz-ai-engineering | `runner/run_task.py` | task orchestration: context → Gateway → parse → write → gate → repair → manifest | EXTEND into AgentRun composition root |
| greenz-ai-engineering | `runner/context.py` | GreenZ engineering-specific context selection/assembly | EXTEND as domain context selector feeding platform Context Engine |
| greenz-ai-engineering | `runner/gateway_client.py` | actual Gateway-routed model call seam | KEEP; adapt to AgentRun/ModelPolicy |
| greenz-ai-engineering | `runner/qwen_lane.py` | bounded Qwen task policy and sensitive-path controls | KEEP initially; migrate toward Skill/ModelPolicy evidence |
| greenz-ai-engineering | `runner/allowlist.py` | file/path write authority | KEEP; map into WorkspaceScope/ToolPolicy |
| greenz-ai-engineering | `runner/overwrite_guard.py` | destructive rewrite protection | KEEP; hard validation gate |
| greenz-ai-engineering | `runner/gate.py` | ruff/pyright/pytest validation and repair loop | KEEP; expose Validation evidence |
| greenz-ai-engineering | `runner/config.py` | runner-specific endpoint/timeouts/context budget | KEEP; separate runtime policy from model identity |
| greenz-ai-engineering | `corrections/*` | correction/disposition capture | KEEP; feed Evidence/Governance |
| greenz-ai-engineering | `benchmarks/*` + `corpus/*` | certification/evaluation corpus | KEEP; become Skill × Model evaluation substrate |
| greenz-ai-engineering | `prompts/*` | engineering procedure/instructions | EXTEND into GreenSkill definitions; do not blindly duplicate prompt content |
| GreenZAlgo_V4 | `src/greenzalgo/platform/*` | shared substrate boundary; modules may depend on platform | KEEP; domain-side integration boundary |
| GreenZAlgo_V4 | `src/greenzalgo/interfaces/*` | domain interfaces | KEEP; consume platform contracts through adapters |
| GreenZAlgo_V4 | `src/greenzalgo/modules/*` | isolated domain modules | KEEP; GAIEP integration stays above/beside module boundaries |
| GreenZAlgo_V4 | `src/greenzalgo/orchestration/*` | domain orchestration namespace | REVIEW; candidate consumer of GAIEP AgentRun/Skills |
| GreenZAlgo_V4 | `architecture/*` | V4 architecture and domain decisions | KEEP; source of domain constraints |
| GreenZAlgo_V4 | `tests/architecture/*` | mechanical dependency/architecture fitness tests | KEEP; reuse principles in GAIEP integration tests |
| GreenZAlgo_V4 | `benchmarks/*`, `runs/*` | research/measurement evidence | KEEP; connect through Evidence rather than importing generic runtime logic |

## Important findings from the first audit

### 1. The platform already owns the generic context primitives

The platform has `AIRequestContext`, `ContextManifest`, `PromptBuilder`, and `ContextBuilderBase`. A second generic `ContextManifest` should **not** be introduced. citehttps://github.com/harimvks/greenz-ai-platform/blob/main/context/manifest.py

### 2. Engineering owns domain context selection

`runner/context.py` contains GreenZ engineering-specific selection logic and module-layout knowledge. The correct VNext direction is to keep that knowledge in engineering while delegating generic serialization, budgets, redaction, and manifest construction to the platform Context Engine. citehttps://github.com/harimvks/greenz-ai-engineering/blob/main/runner/context.py

### 3. Gateway routing is already a real boundary

The platform Gateway already performs capability-based selection, local-first/eligibility checks, and ordered failover. VNext should formalize this as the Model Gateway rather than replace it. citehttps://github.com/harimvks/greenz-ai-platform/blob/main/gateway/gateway.py

### 4. Certification is already upstream of Gateway selection

`certification/gate.py` is the certification-aware filtering point. This should remain outside generic Skill execution and outside the Context Engine. citehttps://github.com/harimvks/greenz-ai-platform/blob/main/certification/gate.py

### 5. Engineering already has strong safety gates

The runner includes an allowlist, overwrite guard, quality gate, and Gateway client. These should be treated as existing safety assets, not replaced by a new agent framework. citehttps://github.com/harimvks/greenz-ai-engineering/blob/main/runner/allowlist.py citehttps://github.com/harimvks/greenz-ai-engineering/blob/main/runner/overwrite_guard.py citehttps://github.com/harimvks/greenz-ai-engineering/blob/main/runner/gate.py

### 6. GreenZAlgo V4 has its own architecture enforcement

V4 explicitly separates `platform/` from `modules/`, and its architecture tests mechanically enforce dependency boundaries. GAIEP integration should respect this rather than introduce generic runtime dependencies into individual modules. citehttps://github.com/harimvks/GreenZAlgo_V4/blob/main/tests/architecture/test_dependency_rule.py

## First implementation rule

Do **not** implement a new Context Engine by copying `runner/context.py` into `platform-vnext`.

Instead:

```text
engineering runner/context.py
        ↓
extract selection/domain knowledge
        ↓
platform ContextBuilderBase / ContextManifest
        ↓
new AgentRun Context Engine orchestration
```

Likewise, do not replace the Gateway, certification gate, overwrite guard, or quality gate until a benchmark demonstrates a concrete deficiency.
