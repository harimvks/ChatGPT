# GAIEP-LAB Repository Architecture

**Status:** Working architecture / experimental workspace specification  
**Date:** 2026-08-21  
**Purpose:** Provide an isolated GitHub-based laboratory for GAIEP Runtime VNext development without modifying the original GreenZ repositories.

---

## 1. Objective

The original repositories remain the reference/baseline implementations:

- `harimvks/greenz-ai-platform`
- `harimvks/greenz-ai-engineering`
- `harimvks/GreenZAlgo_V4`

All experimental GAIEP work is performed under `harimvks/ChatGPT` until explicitly promoted upstream.

This prevents architectural experiments, framework trials, refactors, and rejected approaches from contaminating the working codebases.

---

## 2. Source-of-Truth Policy

```text
Original GreenZ repositories
        = upstream/reference baseline

ChatGPT / GAIEP-LAB
        = experimental implementation

Promotion to original repositories
        = explicit human decision only
```

No experiment is considered production-ready merely because it compiles or passes a subset of tests.

---

## 3. Proposed Layout

```text
ChatGPT/
│
├── GAIEP-LAB_REPOSITORY_ARCHITECTURE.md
│
├── GAIEP/
│   ├── architecture/
│   ├── implementation/
│   ├── migration/
│   ├── tests/
│   └── decisions/
│
├── GAIEP-LAB/
│   ├── README.md
│   ├── provenance/
│   │
│   ├── upstream/
│   │   ├── greenz-ai-platform/
│   │   ├── greenz-ai-engineering/
│   │   └── GreenZAlgo_V4/
│   │
│   ├── platform-vnext/
│   ├── engineering-vnext/
│   ├── algo-vnext/
│   │
│   ├── frameworks/
│   │   ├── hermes/
│   │   ├── agent-runtimes/
│   │   ├── orchestration/
│   │   └── evaluation/
│   │
│   ├── experiments/
│   └── benchmarks/
```

The exact physical reconstruction may be implemented as Git snapshots, generated mirrors, or repository branches depending on the GitHub connector capabilities available at implementation time. The logical separation is mandatory even if the physical layout changes.

---

## 4. Why Not Modify the Original Repositories

The current GreenZ repositories are valuable baselines because they contain working mechanisms and empirical behavior.

Changing them while the architecture is still being evaluated creates several problems:

```text
experimental change
      ↓
baseline contaminated
      ↓
certification comparison weakened
      ↓
rollback becomes harder
      ↓
failed ideas become mixed with working code
```

The laboratory avoids this.

---

## 5. Upstream Snapshots

Every imported repository snapshot must record:

```yaml
repository: harimvks/<repo>
branch: <branch>
commit: <commit-sha>
imported_at: <timestamp>
status: reference
```

Never label a snapshot as `latest` without recording its commit SHA.

A commit SHA is the authoritative provenance anchor.

---

## 6. Provenance Registry

Maintain a machine-readable registry such as:

```yaml
snapshots:
  greenz-ai-platform:
    repository: harimvks/greenz-ai-platform
    ref: main
    commit: <SHA>
    imported_at: <timestamp>

  greenz-ai-engineering:
    repository: harimvks/greenz-ai-engineering
    ref: main
    commit: <SHA>
    imported_at: <timestamp>

  GreenZAlgo_V4:
    repository: harimvks/GreenZAlgo_V4
    ref: main
    commit: <SHA>
    imported_at: <timestamp>
```

The registry should be updated whenever the laboratory is rebased against a newer upstream snapshot.

---

## 7. Three-Layer Working Model

```text
LAYER 1 — UPSTREAM
Current working GreenZ repositories

LAYER 2 — BASELINE MIRROR
Immutable/reconstructable snapshot used for comparison

LAYER 3 — VNEXT
Experimental implementation
```

Never make Layer 3 modifications directly against Layer 1.

---

## 8. VNext Repository Responsibilities

### `platform-vnext`

Generic AI platform infrastructure:

```text
Context contracts
Context Engine
Gateway
Model/provider abstractions
Certification interfaces
Tool contracts
Policy primitives
Observability
Evidence/provenance interfaces
```

### `engineering-vnext`

GreenZ engineering orchestration:

```text
WorkPackage
engineering Context selection
GreenSkills
coding/review workflows
corrections
validation
certification corpus
engineering-specific tools
```

### `algo-vnext`

GreenZAlgo research/trading domain:

```text
research skills
strategy analysis
feature analysis
measurement
prediction
backtest integration
research evidence
campaign governance
```

Generic platform logic must not be copied into `algo-vnext` merely because the domain consumes it.

---

## 9. Framework Sandbox

Third-party frameworks should be evaluated separately:

```text
frameworks/
├── hermes/
├── agent-runtimes/
├── orchestration/
└── evaluation/
```

A framework is an experimental dependency until it passes the GreenZ evaluation criteria.

Do not let a framework's internal abstractions become GAIEP contracts merely because they are convenient.

---

## 10. Framework Evaluation Rule

Every candidate framework should be tested against the same questions:

```text
Does it preserve policy boundaries?
Does it support explicit tool permissions?
Does it support reproducible context?
Does it expose execution state?
Does it support checkpoints?
Does it support model abstraction?
Does it support evidence/provenance?
Can it run locally?
Can it scale to a larger server?
Can it be removed without rewriting GAIEP?
```

The final criterion is especially important.

Avoid vendor/framework lock-in at the runtime contract layer.

---

## 11. Experimental Dependencies

Experimental dependencies should be isolated from the stable platform dependency set whenever practical.

```text
stable dependencies
       ≠
experimental dependencies
```

A framework trial should not force an unrelated change across all GAIEP packages.

---

## 12. Benchmark-First Development

Before replacing an existing mechanism:

```text
baseline behavior
      ↓
benchmark
      ↓
new implementation
      ↓
benchmark again
      ↓
compare
```

The benchmark must record both quality and operational cost.

---

## 13. Baseline Metrics

At minimum:

```text
functional correctness
pytest results
ruff results
pyright results
latency
token usage
context size
model used
tool calls
failure rate
memory/resource behavior
```

For model-related experiments also record:

```text
model identifier
quantization/deployment
certification case
pass/fail/conditional
escalation
```

---

## 14. Compatibility Principle

Existing behavior is the baseline, not the enemy.

A VNext implementation is successful only when it can demonstrate:

```text
same or better correctness
same or better policy enforcement
same or better reproducibility
same or better evidence
acceptable resource cost
```

Architectural elegance alone is not a promotion criterion.

---

## 15. Change Classification

Every experiment should be classified:

```text
A — additive
B — refactor with behavioral equivalence
C — behavior-changing improvement
D — experimental alternative
E — rejected
```

Class D experiments should remain isolated until evidence supports promotion.

---

## 16. Git Strategy

The laboratory should use small, coherent commits.

Recommended pattern:

```text
lab: add AgentRun contracts
lab: add context compatibility adapter
lab: add GreenSkill registry
lab: add read-only subagent runtime
lab: add subagent security tests
lab: evaluate Hermes integration
```

Avoid giant commits containing architecture, framework changes, and unrelated cleanup.

---

## 17. Branch Strategy

When actual Git branches are available, prefer:

```text
main
  │
  ├── lab/context-engine
  ├── lab/greenskill
  ├── lab/subagent-runtime
  ├── lab/hermes-evaluation
  └── lab/model-routing
```

Merge experimental branches into a laboratory integration branch only after their tests pass.

The original repositories remain untouched.

---

## 18. No Automatic Upstream Promotion

The laboratory must never automatically push changes into:

```text
harimvks/greenz-ai-platform
harimvks/greenz-ai-engineering
harimvks/GreenZAlgo_V4
```

Promotion requires an explicit decision after review.

---

## 19. Promotion Gate

A change becomes an upstream candidate only when:

```text
[ ] architecture approved
[ ] baseline comparison completed
[ ] tests pass
[ ] security tests pass
[ ] certification regression checked
[ ] performance measured
[ ] resource impact understood
[ ] provenance recorded
[ ] rollback path defined
[ ] human approval obtained
```

---

## 20. Upstream Synchronization

When upstream changes, do not blindly overwrite VNext.

Use:

```text
new upstream commit
        ↓
compare with recorded baseline
        ↓
identify upstream changes
        ↓
rebase/merge intentionally
        ↓
rerun compatibility suite
```

This preserves both upstream improvements and experimental work.

---

## 21. File-Level Mapping

Before implementation, create a mapping:

```text
Existing file
     ↓
Current responsibility
     ↓
VNext responsibility
     ↓
Action
```

Actions:

```text
KEEP
MOVE
EXTEND
REFACTOR
REPLACE
DEPRECATE
NEW
```

This prevents duplicate implementations.

---

## 22. Existing Context Architecture Must Be Reused

The current platform already provides important context primitives.

Therefore VNext should initially:

```text
reuse existing contracts
      ↓
wrap/extend where required
      ↓
add missing selection/budget/compression behavior
```

Do not create a second unrelated `ContextManifest` or prompt abstraction.

The actual platform code should remain the reference for integration decisions.

---

## 23. Existing Engineering Context Must Be Preserved

The engineering repository already has GreenZ-specific context construction.

The VNext design should extract reusable responsibilities rather than discard them.

Conceptually:

```text
Engineering WorkPackage
        ↓
engineering context selectors
        ↓
platform Context Engine
        ↓
ContextManifest
```

This keeps domain knowledge in the engineering layer while keeping generic context mechanics in the platform.

---

## 24. Experimental GreenSkills

First skills should mirror existing engineering workflows:

```text
python-implementation
python-refactor
python-debug
python-testing
python-code-review
python-review-audit
```

Their initial definitions should be based on actual current prompts/workflows rather than invented abstractions.

---

## 25. Experimental Subagents

First subagent experiments should be read-only:

```text
code-review child
security-review child
test-review child
architecture-review child
```

No shared mutable workspace initially.

---

## 26. Model Experimentation

The laboratory is the correct location to test:

```text
Qwen variants
coding specialists
DeepSeek
GLM
Kimi
Devstral
other Hugging Face coding models
API models
```

But the unit of evidence should remain:

```text
Model × Skill × Corpus × Hardware/Deployment
```

This is more informative than a generic model leaderboard.

---

## 27. Mac Resource Isolation

The laboratory must explicitly record local resource assumptions.

```text
model
quantization
resident memory
peak memory
concurrency
latency
crash/OOM status
```

A candidate that is theoretically capable but unstable on the current Mac should not be promoted to default local routing.

---

## 28. Future AI Server

The laboratory should also support a future larger server.

The same benchmarks can be rerun with:

```text
larger RAM
GPU acceleration
higher concurrency
larger models
```

The architecture should change deployment configuration, not application contracts.

---

## 29. GreenZAlgo Isolation

Trading/research experiments should not introduce generic AI runtime changes directly into the platform.

Instead:

```text
GreenZAlgo skill/domain requirement
        ↓
platform contract
        ↓
platform implementation
```

This keeps the platform reusable.

---

## 30. Research Evidence

For GreenZAlgo experiments, store:

```text
experiment ID
code revision
data snapshot
feature revision
model revision
parameters
results
validation
conclusion
```

This aligns GAIEP experiments with the existing GreenZ research/evidence philosophy.

---

## 31. Reproducibility Requirement

Every important experiment should be rerunnable from:

```text
repository commit
configuration
input corpus/data
model identifier
skill version
context version
tool version
```

If an experiment cannot be reconstructed, it should not be treated as strong evidence.

---

## 32. Documentation Hierarchy

```text
GAIEP master architecture
        ↓
Architecture decision records
        ↓
Implementation specifications
        ↓
Repository/file mapping
        ↓
Code
        ↓
Tests / benchmarks
        ↓
Experiment evidence
```

Code should not silently contradict an approved contract; if implementation forces a design change, record the decision.

---

## 33. What We Build First

The first actual laboratory implementation should be:

```text
1. repository provenance
2. baseline file inventory
3. file-level responsibility map
4. compatibility harness
5. AgentRun contracts
6. Context Engine integration
7. first GreenSkill
8. read-only Subagent Runtime
```

Do not start with a framework rewrite.

---

## 34. Immediate Milestone

The immediate milestone is:

> **Reconstruct enough of the three repositories to create a trustworthy baseline and map every relevant existing mechanism to GAIEP Runtime VNext before changing implementation behavior.**

The result should answer:

```text
What already exists?
Where does it live?
What must remain unchanged?
What can be extracted?
What must move?
What genuinely needs to be added?
Which framework experiments are justified?
```

---

## 35. Final Principle

```text
Original repositories
      = protected evidence / baseline

ChatGPT / GAIEP-LAB
      = controlled experimentation

Benchmarks
      = evidence

Architecture decisions
      = constraints

Promotion
      = deliberate engineering decision
```

This gives GreenZ a safe environment in which GAIEP can evolve aggressively without destabilizing the current systems.
