# Kotlin-bench Qualitative Analysis

*A deep dive into how different AI models approach coding tasks*

## Executive Summary

This analysis examines agent conversations across 8 models on 100 Kotlin tasks. By comparing how models reason, explore codebases, and implement solutions, we identify key behavioral differences that correlate with success.

**Key Findings:**
- **Solution approach matters more than finding the right location** - Models often identify the same files but choose different implementation strategies
- **Test writing significantly improves pass rates** - Models that add tests alongside fixes succeed more often
- **Depth of reasoning correlates with success** - Detailed step-by-step analysis before coding leads to better outcomes
- **Over-engineering is a common failure mode** - Simpler, targeted fixes often outperform complex refactors

---

## Case Studies

### Case Study 1: Thunderbird Unified Inbox (thunderbird-android-8903)

**Task**: Auto-enable unified inbox when second account is added

**Result**: Only **Opus 4.5** solved this task

#### Comparison of Approaches

| Model | Approach | Patch Size | Tests Added | Result |
|-------|----------|------------|-------------|--------|
| Opus 4.5 | Changed `> 1` to `== 2`, added docs + 5 unit tests | 94 lines | Yes | **PASS** |
| Gemini Pro 3 | Changed `> 1` to `== 2` only | 14 lines | No | FAIL |
| Sonnet 4 | Same core fix | ~15 lines | No | FAIL |

**Analysis**: All models identified the same root cause and made the same logical fix. The critical difference was **Opus wrote comprehensive unit tests** that validated the edge cases (0 accounts, 1 account, 2 accounts, 3+ accounts). The tests likely matched what the evaluation expected.

**Opus's Reasoning (from thinking blocks)**:
> "The issue is that when the first account is added, the size is now 1... when the second account is added, the size is now 2, and unified inbox SHOULD be shown. But based on the bug report, it seems like the check is happening BEFORE the account is fully saved..."

This detailed analysis led to a more thorough solution with proper test coverage.

---

### Case Study 2: ktlint Import Ordering (pinterest-ktlint-1996)

**Task**: Fix inconsistent multiline string indentation for properties vs functions

**Result**: Only **Gemini Pro 3** solved this task

#### Comparison of Approaches

| Model | Approach | Result |
|-------|----------|--------|
| Gemini Pro 3 | Added `alternativeExpectedIndent` variable to track both valid indent patterns | **PASS** |
| Opus 4.5 | Modified `isRawStringLiteralFunctionBodyExpression()` to include PROPERTY type | FAIL |

**Analysis**: Both models understood the issue (properties weren't being treated like functions for indentation). But they chose **different implementation strategies**:

- **Gemini Pro 3**: Added flexibility by tracking an alternative valid indent, checking against both options
- **Opus 4.5**: Tried to extend the existing function check to also match properties

Gemini's approach was more robust because it didn't assume properties and functions should be treated identically everywhere - it just allowed for the alternative indent where appropriate.

---

### Case Study 3: AnkiDroid SVG Object Access (ankidroid-Anki-Android-15871)

**Task**: Fix JavaScript access to SVG content in WebView

**Result**: Only **GPT-5.2** solved this task

#### Comparison of Approaches

| Model | Approach | Key Insight | Result |
|-------|----------|-------------|--------|
| GPT-5.2 | Remove `<object>` from file:// rewriting | "Rewriting makes it cross-origin" | **PASS** |
| Opus 4.5 | Add CORS headers to asset loader | Trying to enable cross-origin | FAIL |

**Analysis**: This is a fascinating case of **problem vs symptom** addressing:

- **GPT-5.2's reasoning**: "When the card is loaded from `http://127.0.0.1/...`, rewriting the object to `file:///...` makes it cross-origin and causes `object.contentDocument` to be null"

GPT identified that the **root cause** was unnecessarily rewriting object URLs, which broke same-origin policy. The fix was to simply not rewrite them.

- **Opus's approach**: Tried to work around the cross-origin issue by adding CORS headers

Opus attacked the symptom (cross-origin blocking) rather than the cause (unnecessary URL rewriting). The simpler solution won.

---

### Case Study 4: Failed by All - kotlinx-datetime Error Messages (Kotlin-kotlinx-datetime-360)

**Task**: Improve error messages to include input strings

**Result**: **No model passed**

#### What Everyone Tried

| Model | Changes Made |
|-------|--------------|
| Opus 4.5 | Changed "One"→"one", added input to exception message |
| Gemini Pro 3 | Same changes + added tests |
| Sonnet 4.5 | Similar approach |
| GPT-5.2 | Similar approach |

**Analysis**: All models made logically correct changes that would improve error messages. The failure suggests:
1. The expected error format was very specific (exact string matching)
2. Models didn't capture all the edge cases required by tests
3. The task may have required understanding multiple interconnected files

This represents a case where **the obvious fix wasn't enough** - the tests likely expected very specific formatting or additional changes.

---

## Behavioral Patterns

### 1. Reasoning Depth

**High performers** (Opus, Gemini Pro 3) exhibit detailed step-by-step reasoning:

```
Opus on ktlint-1857:
"With config `*, |, javax.**, java.**, |, kotlinx.**, kotlin.**`:
- Index 0: `*` (ALL_OTHER_IMPORTS_ENTRY)
- Index 1: `|` (BLANK_LINE_ENTRY)
- Index 2: `javax.**`
...
If imports only match `java.**` (index 3), then for the first import:
1. index1 = -1, index2 = 3
2. Loop checks indices 0, 1, 2
3. At index 1, finds BLANK_LINE_ENTRY
4. Adds a blank line before the first import (incorrect!)"
```

**Low performers** (GLM-4.7) show shallow analysis:
```
"Let me search for relevant information in the CHANGELOG..."
"Now let me search for git history to understand what changed..."
```

### 2. Exploration vs Exploitation

| Model | Avg Tool Calls | Exploration Style |
|-------|----------------|-------------------|
| Gemini Flash 3 | 56/task | Broad (heavy list_dir usage) |
| Opus 4.5 | 28/task | Targeted (more grep, less listing) |
| GLM-4.7 | 11/task | Minimal exploration |

**Observation**: Gemini Flash uses 2x more tool calls than Opus but has lower pass rate. This suggests **targeted exploration beats exhaustive exploration**.

### 3. Test Writing Correlation

Models that write tests alongside fixes have higher unique solve rates:

| Model | Unique Solves | Typically Adds Tests |
|-------|---------------|---------------------|
| Gemini Pro 3 | 3 | Yes |
| Opus 4.5 | 2 | Yes |
| Gemini Flash 3 | 2 | Sometimes |
| GPT-5.2 | 1 | Yes |
| Sonnet 4 | 1 | No |

### 4. Patch Size Analysis

| Outcome | Avg Lines Changed |
|---------|-------------------|
| Pass | 36-58 lines |
| Fail | 62-133 lines |

**Models change MORE code when failing**. This suggests over-engineering or making unnecessary changes correlates with failure.

---

## Model-Specific Insights

### Claude Opus 4.5 (39% pass rate - Best)
**Strengths:**
- Deep algorithmic reasoning
- Comprehensive test writing
- Clear documentation in code

**Weaknesses:**
- Sometimes over-engineers solutions
- Occasionally chooses complex approaches when simple ones suffice

### Gemini Pro 3 (38% pass rate - Second)
**Strengths:**
- Practical, targeted fixes
- Good at finding non-obvious solutions
- 3 unique solves (most of any model)

**Weaknesses:**
- Less thorough testing
- Sometimes misses edge cases

### GPT-5.2 (33% pass rate)
**Strengths:**
- Excellent root cause analysis
- Clean, minimal patches
- Strong on cross-origin/security issues

**Weaknesses:**
- Less exploration of codebase
- Fewer tool calls may miss context

### GLM-4.7 (12% pass rate - Lowest)
**Weaknesses:**
- Insufficient exploration (only 11 tool calls avg)
- Shallow reasoning
- Often gives up too early
- Poor test coverage

---

## Common Failure Patterns

### 1. Wrong Abstraction Level
Models fix the symptom rather than the cause. Example: Adding CORS headers instead of not breaking same-origin.

### 2. Incomplete Test Coverage
Making the logical fix but not writing tests that match expected behavior.

### 3. Over-Modification
Changing multiple files when a single-file fix would suffice. Larger patches correlate with failure.

### 4. Insufficient Context Gathering
Not reading enough of the codebase to understand interdependencies.

### 5. Premature Implementation
Starting to code before fully understanding the problem. High performers spend more turns analyzing before editing.

---

## Recommendations for Agent Improvement

1. **Enforce test writing** - Require agents to add/modify tests for any fix
2. **Prefer minimal changes** - Score against patch size; simpler is often better
3. **Deeper reasoning before action** - Encourage multi-step analysis before first edit
4. **Root cause vs symptom detection** - Train to identify if a fix addresses cause or symptom
5. **Targeted exploration** - Use grep/search before list_dir; be specific about what you're looking for

---

## Methodology

This analysis examined:
- Agent log JSON files containing full conversation history
- Patch diffs comparing actual code changes
- Test results indicating pass/fail
- Tool call patterns and frequencies

Focus was placed on:
- Unique solves (tasks only one model passed)
- High-variance tasks (some passed, some failed)
- Hard tasks (all models failed)

Conversations were analyzed for reasoning patterns, exploration strategies, and implementation approaches.
