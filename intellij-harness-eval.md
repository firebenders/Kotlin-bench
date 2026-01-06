# PRD: Kotlin-bench in a Headless Firebender IntelliJ Agent Harness

## Owner

Firebender Core / Agent Platform

## Status

Proposed → Build

## Motivation / Why This Exists

Firebender’s differentiation is **IDE-native, agentic coding** inside IntelliJ / Android Studio. Existing benchmarks (Kotlin-bench, SWE-bench) do **not** reflect:

* semantic IDE tools (PSI, refactors)
* agent loops
* real time-to-green
* tool discipline vs text edits
* cost and latency under realistic usage

We need:

1. A **headless, reproducible IntelliJ agent environment**
2. A **clean, UI-independent agent loop**
3. A way to **run Kotlin-bench through Firebender as an agent**
4. A **behavioral comparison across models**
5. A **data foundation** for future training (optional)

This PRD defines how to build that system.

---

## Goals

### Primary Goals

* Run Kotlin-bench tasks through a **real IntelliJ agent loop**
* Compare models on:

  * correctness
  * semantic tool usage
  * speed (steps, time)
  * cost
* Identify **behavioral gaps** Firebender can close for users

### Secondary Goals

* Produce a **Firebender-native agent benchmark**
* Generate **clean agent traces** usable for SFT/DPO/RL later
* Create **marketing-ready comparisons** (IDE agent vs raw LLM)

---

## Non-Goals (Explicit)

* No model fine-tuning in this phase
* No RL loop in this phase
* No claim of generalization or “model intelligence”
* No dependency on user data (this is offline / synthetic)

---

## Key Design Principles

1. **Agent loop must be UI-independent**
2. **Headless ≠ fake** (must be real IntelliJ + real indexing)
3. **Traces must be first-class artifacts**
4. **Harness behavior > raw accuracy**
5. **Training is optional and downstream**

---

## High-Level Architecture

```
Kotlin-bench Task
        ↓
Headless IntelliJ VM (Modal)
        ↓
Firebender Agent Loop (Headless)
        ↓
Firebender Tool API (Semantic + Text)
        ↓
Model (GLM-4.7, GLM-4.5-Air, etc.)
        ↓
Agent Trace + Metrics
        ↓
Analysis & Comparison
```

---

## 1. Agent Loop Architecture (Critical Change)

### Problem

The current `AgentLoop` is tightly coupled to:

* UI state
* tool window lifecycle
* user interactions

This makes it:

* impossible to run headless
* hard to log clean traces
* hard to reason about correctness

### Requirement

We need a **pure, headless agent loop** that:

* has no UI dependencies
* can be invoked from:

  * IntelliJ UI
  * headless scripts
  * benchmarks
* emits deterministic, structured traces

---

### Decision: **Headless Firebender Agent (Recommended)**

We will implement a **headless agent loop inside Firebender**, not an external script.

#### Why this is the right choice

* Reuses **exact same tool implementations**
* Guarantees behavioral parity with production
* Avoids divergence between “benchmark agent” and “real agent”
* Lets UI become a thin client on top of the same loop

---

### Agent Loop Interface (Proposed)

```kotlin
interface AgentRunner {
  fun run(
    task: AgentTask,
    model: ModelConfig,
    tools: ToolConfig,
    limits: AgentLimits
  ): AgentResult
}
```

Where:

```kotlin
data class AgentTask(
  val description: String,
  val repoPath: String,
  val entryPoint: File?,
)

data class AgentResult(
  val success: Boolean,
  val finalDiagnostics: List<Diagnostic>,
  val trace: AgentTrace,
)
```

The **UI calls this**, and so does **headless infra**.

---

### Agent Trace (First-Class)

Every run produces a structured trace:

```json
{
  "model": "glm-4.7",
  "task_id": "kotlin-bench-42",
  "steps": [
    {
      "step": 1,
      "state": {...},
      "action": {
        "type": "tool_call",
        "tool": "goToDefinition",
        "args": {...}
      },
      "outcome": {...},
      "latency_ms": 312
    }
  ],
  "metrics": {
    "steps": 12,
    "tokens": 8421,
    "tool_calls": {
      "renameSymbol": 1,
      "goToDefinition": 3,
      "gradle": 0
    },
    "wall_time_ms": 12453
  }
}
```

This trace is the **core artifact**.

---

## 2. Headless IntelliJ Infrastructure (Modal)

### Requirement

We must run **real IntelliJ**, not mocks.

### Modal VM Responsibilities

Each VM must:

1. Boot Linux + Xvfb
2. Launch IntelliJ / Android Studio
3. Install Firebender plugin
4. Open Kotlin-bench project
5. Wait for:

  * indexing complete
  * PSI ready
6. Expose a control interface:

  * start agent
  * query diagnostics
  * call tools
7. Run agent loop
8. Persist traces to storage
9. Tear down cleanly

---

### Infra Details

* **VM per task** (for determinism)
* Warm VM pool later (not required for v1)
* Indexing readiness detected via:

  * IntelliJ indexing API
  * “Dumb mode” exit
* All runs are **non-interactive**

---

### Output Artifacts

Each run must emit:

* `agent_trace.json`
* `metrics.json`
* logs (stderr/stdout)
* final diagnostics snapshot

Stored in:

* S3 / GCS / Modal Volume

---

## 3. Kotlin-bench Execution

### Task Definition

For each Kotlin-bench task:

* Load repo at failing commit
* Open project in IntelliJ
* Run agent with:

  * identical system prompt
  * identical tools
  * identical limits

---

### Models to Run

Initial set:

* GLM-4.7
* GLM-4.5-Air
* (optional) Claude / GPT-4-class as ceiling

Each model:

* same agent loop
* same tool set
* same step limits

Multiple runs per task (K=3–5) for variance.

---

## 4. Metrics & Analysis

### Primary Metrics

#### Correctness

* task solved (yes/no)
* tests passing (yes/no)

#### Tool Discipline (Primary Signal)

* % correct semantic tool usage
* % manual edits when semantic tools exist
* % unnecessary Gradle runs

#### Efficiency

* agent steps
* wall-clock time
* token usage

#### Cost

* $ / task
* GPU seconds

---

### Failure Taxonomy

Each failure labeled as:

* wrong tool choice
* over-editing
* semantic refactor error
* reasoning / understanding error
* infinite loop / thrashing

---

### Visualization

We will generate:

* Pareto frontier plots:

  * cost vs accuracy
  * speed vs tool correctness
* per-tool usage histograms
* step-by-step behavior comparisons

---

## 5. Decision Output

This project must answer:

1. **Is there a behavioral gap between models?**
2. **Is that gap policy-based or capacity-based?**
3. **Is there a clear Pareto frontier winner?**
4. **What behaviors add the most user value if fixed?**

---

## 6. Training (Explicitly Out of Scope, But Enabled)

This system must produce data sufficient for:

* SFT (behavior cloning)
* DPO (preference optimization)
* RL (later)

But **no training happens in this PRD**.

---

## Success Criteria

This project is successful if:

* We can reproducibly run Kotlin-bench in IntelliJ headlessly
* We can compare models on **behavior, speed, and cost**
* We can clearly articulate:

  * where Firebender adds value
  * where models fail inside the IDE
* We have high-quality agent traces for future use

---

## Risks & Mitigations

### Risk: IntelliJ headless instability

Mitigation:

* strict readiness checks
* aggressive timeouts
* VM-level isolation

### Risk: Agent loop divergence from UI behavior

Mitigation:

* single shared agent loop
* UI becomes a thin wrapper

### Risk: Over-interpreting benchmark results

Mitigation:

* clear framing: **behavioral analysis**, not intelligence claims

---

## Final Framing (Internal)

> This project upgrades Kotlin-bench from a static LLM benchmark into a real IDE-native agent benchmark, giving Firebender deep insight into model behavior, performance, and user value — and laying the groundwork for targeted training later.

---

If you want next, I can:

* sketch the **exact AgentRunner refactor**
* define the **headless IntelliJ control protocol**
* help break this into **engineering tickets**
* or design the **analysis dashboard** that leadership and marketing can actually use
