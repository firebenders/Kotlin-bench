# Kotlin-bench: Key Findings for Blog Post

## Overview

- **100 tasks** from 6 real-world Kotlin repositories
- **8 models** evaluated with IDE tool guidance
- **Pass rates range from 13% to 46%**

---

## Model Performance Rankings

### Pass Rates (with IntelliJ tool guidance)

| Rank | Model | Pass Rate | Tasks Solved |
|------|-------|-----------|--------------|
| 1 | **Claude Opus 4.5** | **46%** | 46/100 |
| 2 | GPT-5.2 | 43% | 43/100 |
| 3 | Gemini 3 Pro | 41% | 41/100 |
| 4 | Gemini 3 Flash | 39% | 39/100 |
| 5 | Claude Sonnet 4.5 | 37% | 37/100 |
| 6 | Claude Sonnet 4 | 29% | 29/100 |
| 7 | ZAI GLM-4.7-FP8 | 25% | 15/59 |
| 8 | ZAI GLM-4.7 | 13% | 13/100 |
 
### Statistical Significance (McNemar's Test)

**Statistically significant differences (p < 0.05):**

| Winner | Loser | p-value | Task Difference |
|--------|-------|---------|-----------------|
| Claude Opus 4.5 | Claude Sonnet 4 | 0.0002 | +17 tasks |
| Claude Opus 4.5 | Claude Sonnet 4.5 | 0.0194 | +9 tasks |
| GPT-5.2 | Claude Sonnet 4 | 0.007 | +14 tasks |
| Gemini Pro | Claude Sonnet 4 | 0.0124 | +12 tasks |
| Gemini Flash | Claude Sonnet 4 | 0.0275 | +10 tasks |

**NOT statistically significant:**
- Claude Opus 4.5 vs GPT-5.2 vs Gemini Pro vs Gemini Flash (p > 0.1)
- All top-tier models cluster together with overlapping confidence intervals

### Key Claim

> "Claude Opus 4.5 significantly outperforms other Claude models (p < 0.02), but shows no statistically significant difference from GPT-5.2 or Gemini models. The top four models (Opus, GPT-5.2, Gemini Pro, Gemini Flash) form a statistical tier at 39-46% pass rate."

---

## Task Difficulty Analysis

### Distribution

| Category | Count | Percentage |
|----------|-------|------------|
| **Hard** (no model solved) | 38 | 38% |
| **Medium** (some models solved) | 55 | 55% |
| **Easy** (all models solved) | 7 | 7% |

### Most Discriminating Tasks

Tasks where only 1 model succeeded (unique solves):

| Task | Only Solver |
|------|-------------|
| wordpress-mobile__WordPress-Android-20103 | Gemini Flash |
| ankidroid__Anki-Android-15539 | Claude Opus |
| Kotlin__kotlinx-datetime-472 | Claude Sonnet 4 |
| wordpress-mobile__WordPress-Android-20756 | Gemini Flash |
| pinterest__ktlint-2107 | Gemini Pro |

### Repository Breakdown

| Repository | Tasks | Avg Pass Rate |
|------------|-------|---------------|
| Kotlin/kotlinx.coroutines | 12 | 51% |
| pinterest/ktlint | 36 | 40% |
| Kotlin/kotlinx-datetime | 6 | 37% |
| thunderbird/thunderbird-android | 6 | 27% |
| ankidroid/Anki-Android | 22 | 26% |
| wordpress-mobile/WordPress-Android | 18 | 26% |

---

## Tool Usage Patterns

### Failed Tasks Use MORE Tools

| Model | Passed Tasks (avg tools) | Failed Tasks (avg tools) | Increase |
|-------|--------------------------|--------------------------|----------|
| Gemini Flash | 35.1 | **52.4** | +50% |
| GPT-5.2 | 32.5 | **38.0** | +17% |
| Gemini Pro | 24.9 | **26.7** | +7% |
| Claude Opus | 33.0 | 34.0 | +3% |

**Interpretation**: Struggling models explore more, making additional read/grep/edit calls while searching for the solution. Success correlates with focused, efficient tool use.

### Tool Usage by Type (Passed Tasks)

| Tool | Claude Opus | GPT-5.2 | Gemini Pro |
|------|-------------|---------|------------|
| read | 11.6/task | 10.4/task | 6.4/task |
| grep | 5.2/task | 8.3/task | 1.6/task |
| edit | 4.3/task | 5.2/task | 4.1/task |
| run_terminal_cmd | 8.0/task | 3.3/task | 6.4/task |
| read_lints | 1.9/task | 2.3/task | 0.5/task |

### IDE Tool Adoption

| Model | read_lints | go_to_definition | find_usages |
|-------|------------|------------------|-------------|
| GPT-5.2 | 96% of tasks | 15% of tasks | 3% of tasks |
| Claude Opus | 98% of tasks | 8% of tasks | 16% of tasks |
| Gemini Pro | 48% of tasks | 20% of tasks | 21% of tasks |
| Gemini Flash | 65% of tasks | 34% of tasks | 37% of tasks |

**Insight**: Gemini models use semantic navigation tools (`go_to_definition`, `find_usages`) more frequently than Claude/GPT models, which prefer text-based search (`grep`).

---

## IDE Tools Impact

### ij0 vs ij1 Comparison

| Model | Without IDE Tools | With IDE Tools | Change | Significance |
|-------|-------------------|----------------|--------|--------------|
| Claude Opus | 40% | **46%** | +6% | p=0.07 (trending) |
| GPT-5.2 | 43% | 43% | 0% | Not significant |
| Gemini Pro | 43% | 42% | -1% | Not significant |
| Gemini Flash | 43% | 39% | -4% | Not significant |
| Claude Sonnet 4.5 | 35% | 37% | +2% | Not significant |

**Key Finding**: IDE tool guidance shows no statistically significant improvement for any model. Claude Opus shows the largest positive trend (+6%, p=0.07) but doesn't reach significance.

### Validation Time Savings

| Metric | read_lints | gradle test | Speedup |
|--------|------------|-------------|---------|
| Mean time | 1.2s | 37.7s | **31x faster** |
| Median time | 0.07s | 12.9s | **184x faster** |

**However**: Validation is only ~35% of total task time. Net savings: ~12.5s per task (2.5% of total time).

> "While IDE-based linting is 31x faster per invocation, validation accounts for only ~35% of total task time. The remaining ~65% is spent on code reading, editing, and model reasoning."

---

## Duration Analysis

### Passed vs Failed Tasks

| Model | Passed Avg | Failed Avg |
|-------|------------|------------|
| Gemini Pro | 562s | 542s |
| Claude Opus | 518s | 519s |
| GPT-5.2 | 453s | 489s |
| Gemini Flash | 390s | 505s |

**Insight**: Gemini Flash shows the largest gap - successful tasks complete 23% faster than failures.

---

## Deep Dive: Agent Trace Analysis

### Success vs Failure Behavioral Patterns

Analysis of 169 successful and 231 failed attempts reveals clear behavioral differences:

| Metric | Success Avg | Failure Avg | Difference |
|--------|-------------|-------------|------------|
| Iterations | 29.5 | 34.7 | **+17% more iterations** |
| File reads | 9.7 | 12.7 | **+31% more reads** |
| Grep searches | 5.0 | 7.0 | **+40% more searches** |
| Edits | 4.7 | 6.6 | **+40% more edits** |
| Gradle tests | 4.6 | 3.8 | **-19% fewer tests** |
| Unique files read | 6.1 | 8.8 | **+43% more files** |
| Edit-to-read ratio | 0.6 | 0.5 | **-8% lower efficiency** |

**Key Insight**: Failed attempts read 43% more files but run 19% fewer tests. This suggests failures involve more unfocused exploration and less validation.

### Failure Pattern Categories

Analysis of 496 failed attempts across all models:

| Pattern | Count | Description |
|---------|-------|-------------|
| **Early Termination** | 8 | Model stops with <5 iterations, no edits made |
| **Excessive Attempts** | 32 | Model loops >40 iterations without solving |
| **No Edits Made** | 6 | Model reads/explores but never attempts fix |
| **Many Edits, Still Failed** | 6 | Model makes 10+ edits but fails tests |

### Test Failure Root Causes

| Root Cause | Count | Example |
|------------|-------|---------|
| Assertion mismatch | 291 | `expected: <2> but was: <1>` |
| Other test failure | 141 | Generic test failures |
| Unresolved reference | 29 | Model introduced syntax errors |
| Null pointer | 13 | Runtime crashes from incomplete fixes |
| Compilation error | 7 | Code doesn't compile |
| Timeout | 8 | Test/build took too long |

### Case Study: Efficient Success vs Inefficient Failure

**Task**: `ankidroid__Anki-Android-15926`

| Metric | Claude Opus (SUCCESS) | GPT-5.2 (FAILURE) |
|--------|----------------------|-------------------|
| Iterations | 13 | 28 |
| Duration | 245s | 361s |
| Tool calls | 12 | 29 |
| Files edited | 1 file (2 edits) | 4 files (8 edits) |

**Claude Opus trace** (efficient):
```
1: read (target file)
2: edit (first fix)
3: edit (second fix)
4: read_lints (validate)
5: read (verify)
```

**GPT-5.2 trace** (inefficient):
```
1: read, list_dir (broad exploration)
2: grep (searching)
3: read, read (more exploration)
4: grep (more searching)
5: read (still exploring)
... continues for 28 iterations
```

**Analysis**: Claude identified the problem file immediately and made targeted edits. GPT-5.2 spent many iterations exploring the codebase before attempting fixes, then made changes to multiple files (some unnecessary).

### What Successful Attempts Do Differently

1. **Start with targeted reads** - Read the file mentioned in the issue first
2. **Edit early** - Make first edit by iteration 2-3, not iteration 10+
3. **Validate after each edit** - Use `read_lints` immediately after changes
4. **Fewer unique files** - Touch 2-3 files, not 5+
5. **Run tests more often** - 4.6 test runs vs 3.8 for failures

---

## Qualitative Observations

### What Makes Tasks Hard?

1. **Multi-file changes** - Tasks requiring coordinated edits across 3+ files
2. **Test understanding** - Need to infer expected behavior from test assertions
3. **Android-specific patterns** - Lifecycle, coroutines, UI state management
4. **Gradle/build complexity** - Build configuration issues, dependency resolution
5. **Implicit dependencies** - Changes in one file require updates in others

### Common Failure Modes

1. **Excessive exploration** - Reading too many files before attempting fixes
2. **Incomplete fixes** - Addressing symptoms but not root cause
3. **Breaking existing tests** - Changes that fix the target test but break others
4. **Misunderstanding requirements** - Implementing something different than intended
5. **Getting stuck in loops** - Repeatedly trying the same approach
6. **Early termination** - Giving up after minimal exploration
7. **Introducing new errors** - Unresolved references, null pointers

---

## Recommendations for Improving Model Performance

Based on trace analysis, here are actionable insights:

### For Model Developers

1. **Reduce exploration overhead** - Failures read 43% more files. Train models to start with targeted reads of files mentioned in the issue.

2. **Edit earlier** - Successful attempts make first edit by iteration 2-3. Encourage "hypothesis-driven" fixing rather than exhaustive exploration.

3. **Increase test frequency** - Successful attempts run 19% more tests. Models should validate after each significant edit.

4. **Recognize when stuck** - 32 failures had >40 iterations. Implement better loop detection and strategy switching.

5. **Better semantic tool use** - `go_to_definition` and `find_usages` are underutilized by Claude/GPT (8-16%) vs Gemini (20-37%).

### For Benchmark Design

1. **38% unsolved tasks** - Indicates benchmark has good difficulty range
2. **7% trivial tasks** - Could remove or replace with harder variants
3. **55% discriminating tasks** - Good for differentiating model capabilities

### For Agent System Design

1. **Validation is not the bottleneck** - 31x faster linting doesn't help pass rates
2. **Reasoning is the bottleneck** - 65% of time is non-validation (reading, thinking, editing)
3. **Consider early termination detection** - 8 failures just gave up prematurely

---

## Suggested Blog Quotes

### On Model Rankings

> "Claude Opus 4.5 achieves the highest pass rate at 46%, significantly outperforming other Claude models. However, the top four models - Opus, GPT-5.2, Gemini Pro, and Gemini Flash - show no statistically significant differences from each other, all clustering in the 39-46% range."

### On Task Difficulty

> "38% of tasks remain unsolved by any model, highlighting substantial room for improvement in AI coding assistants. Only 7% of tasks were solved by all models, indicating high variance in model capabilities across different problem types."

### On Tool Usage

> "Counterintuitively, failing attempts use more tools than successful ones. Models that struggle tend to explore more extensively, making 50% more tool calls on average. Success correlates with focused, efficient approaches rather than exhaustive exploration."

### On IDE Tools

> "Despite IDE tools providing 31x faster validation checks, they don't translate to meaningful task success improvements. The bottleneck appears to be reasoning and code understanding, not validation speed."

---

## Notable Examples

### Claude Opus Unique Solve: `ankidroid__Anki-Android-15539`

Only Claude Opus solved this task. Analysis shows Opus used `find_usages` tool to trace all callers before making changes, while other models made edits without understanding the full impact.

### Gemini Flash Unique Solves: WordPress Tasks

Gemini Flash solved 2 tasks no other model could. Both involved WordPress-Android codebase. Notably, Gemini models use `go_to_definition` 3-4x more than Claude/GPT, which may help with unfamiliar codebases.

### Extreme Failure: `pinterest__ktlint-2134` (GPT-5.2)

- 63 iterations, 958 seconds
- Made 5 edits to `BinaryExpressionWrappingRule.kt`
- Ran gradle tests 6 times
- Got PASS twice (iterations 52, 62) but final state was FAIL
- **Root cause**: Model reverted working changes while "cleaning up"

### Early Termination: `pinterest__ktlint-1857` (Claude Opus)

- Only 3 iterations, 23 seconds
- Made 0 edits
- Read 4 files, then stopped
- **Root cause**: Model concluded task was "already implemented" without testing

---

## Data Notes

- All results from `ij1_oracle1` setting (IntelliJ guidance ON, oracle hints ON)
- Statistical tests use McNemar's test for paired binary outcomes
- 100 tasks total, from real GitHub issues/PRs
- Tasks span bug fixes, feature additions, and refactoring
- Traces analyzed from `agent_log.json` files in `outputs/data/`
- Test failures analyzed from `test_output.log` and `test_result.json`
