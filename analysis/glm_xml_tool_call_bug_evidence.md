# GLM-4.7 XML Tool Call Bug - Structured Evidence

## Summary

**Bug**: GLM-4.7 model inconsistently uses OpenAI function calling API, sometimes outputting tool calls as XML text instead of using the proper `tool_calls` API field.

**Impact**: 3 of 100 runs (3%) confirmed terminated prematurely due to this bug.

**Affected Model**: `zai-glm-4.7` (accounts/fireworks/models/glm-4p7)

**Affected Tasks**:

| Task                            | Iterations Before Bug          | Test Result  |
| ------------------------------- | ------------------------------ | ------------ |
| `pinterest__ktlint-1997`        | 2 successful, terminated at #3 | Failed (N/A) |
| `ankidroid__Anki-Android-16400` | 1 successful, terminated at #2 | Failed (N/A) |
| `pinterest__ktlint-1857`        | 2 successful, terminated at #3 | Failed (N/A) |

**Search Methodology**: Searched all 100 zai-glm-4.7 runs for:

- Pattern 1: `<tool_call>` XML syntax in idea.log → Found in **3 runs**
- Pattern 2: `arg_key` XML argument syntax → Found in **3 runs**
- Pattern 3: Non-final iterations with 0 tool_calls and >3s runtime → 1 additional suspicious run

---

## Evidence Chain

### EXHIBIT A: agent_log.json - Iteration Summary

**File**: `outputs/data/pinterest__ktlint-1997/zai-glm-4.7/ij1_oracle1/agent_log.json`

| Iteration | Tool Calls | Duration | Status                  |
| --------- | ---------- | -------- | ----------------------- |
| 1         | 2          | 7182ms   | ✓ EXECUTED              |
| 2         | 2          | 3866ms   | ✓ EXECUTED              |
| 3         | 0          | 5376ms   | ✗ NO TOOLS (terminated) |

**Key Observation**: Iteration 3 ran for 5376ms but produced 0 tool_calls. The model was actively generating output but tools weren't captured because they were output as text, not via the API.

---

### EXHIBIT B: idea.log - What the Model Actually Output in Iteration 3

**File**: `outputs/data/pinterest__ktlint-1997/zai-glm-4.7/ij1_oracle1/idea.log`

```
2026-01-28 02:33:03,202 [THINKING] Now I understand the issue better. Let me search for tests related to this issue to understand the expected behavior:<tool_call>list_dir<arg_key>target
2026-01-28 02:33:03,269 [THINKING] Now I understand the issue better. Let me search for tests related to this issue to understand the expected behavior:<tool_call>list_dir<arg_key>target_directory</arg_key><arg_value>/project
2026-01-28 02:33:03,303 [THINKING] Now I understand the issue better. Let me search for tests related to this issue to understand the expected behavior:<tool_call>list_dir<arg_key>target_directory</arg_key><arg_value>/project/ktlint-ru...
2026-01-28 02:33:03,356 Received finish reason: stop
2026-01-28 02:33:03,360 ========== Iteration #3 END (continue=false, 5376ms) ==========
```

**Key Finding**: The model output `<tool_call>list_dir<arg_key>target_directory</arg_key><arg_value>/project/ktlint-ru...` as TEXT in its thinking stream, not as a proper `tool_calls` API response.

---

### EXHIBIT C: Side-by-Side Comparison - Working vs Broken

#### ITERATION 1 (WORKING):

```
API Response Structure:
  tool_calls: [{id: 'chatcmpl-tool-be11...', function: {name: 'list_dir', arguments: '{"target_directory":"/project"}'}}]
  finish_reason: 'tool_calls'

Result: [TOOL:START] list_dir executed with proper arguments
```

#### ITERATION 3 (BROKEN):

```
API Response Structure:
  tool_calls: [] (empty!)
  content: '...understand the expected behavior:<tool_call>list_dir<arg_key>target_directory</arg_key>...'
  finish_reason: 'stop'

Result: No tools detected, agent terminates
```

---

### EXHIBIT D: Full XML Tool Call Text

From idea.log at timestamp 02:33:03,303:

```
[THINKING] Now I understand the issue better. Let me search for tests related to this issue to understand the expected behavior:<tool_call>list_dir<arg_key>target_directory</arg_key><arg_value>/project/ktlint-ru...
```

The model intended to call `list_dir` with `target_directory='/project/ktlint-ruleset-standard/...'` but output it as XML text instead of using the function calling API.

---

### EXHIBIT E: Other Confirmed Affected Tasks

#### 1. ankidroid\_\_Anki-Android-16400

```
[THINKING] Now let me check the preferences files and ActionButtons to understand how to add a toggle control:<tool_call>read<arg_key>file_path</arg_key><arg_value>/project/AnkiDroid/src/main/java/com/ichi2/anki...
Received finish reason: stop
========== Iteration #2 END (continue=false, 35358ms) ==========
```

#### 2. pinterest\_\_ktlint-1857

```
[THINKING] Now let me look at the import ordering helper classes to understand...<tool_call>...
Received finish reason: stop
```

---

### EXHIBIT F: Code Path - Why This Causes Termination

**File**: `HeadlessAgentLoop.kt` (lines 551-555)

```kotlin
// Check for tool calls - if no tools, we're done
val hasToolCalls = fullResponse.content.any { it.tool != null }
if (!hasToolCalls) {
    return false  // <-- TERMINATES THE AGENT LOOP
}
```

When `finish_reason='stop'` and the model outputs tool calls as TEXT:

1. `fullResponse.content` contains only text (thinking)
2. No `content.tool` entries exist
3. `hasToolCalls = false`
4. `return false` → agent loop ends prematurely

---

## Root Cause Analysis

### Mechanism

1. Model decides to call a tool (e.g., `list_dir`, `read`)
2. Instead of using the `tool_calls` API field, model outputs XML syntax in text stream:
   ```
   <tool_call>{tool_name}<arg_key>{param}</arg_key><arg_value>{value}</arg_value>
   ```
3. API returns `finish_reason='stop'` (text completion, not tool invocation)
4. Plugin sees no `tool_calls` in response structure
5. Agent loop terminates (`hasToolCalls=false` → `return false`)

### Why This Happens

The GLM-4.7 model appears to have been trained with multiple tool calling formats. It sometimes uses the correct OpenAI function calling API, but occasionally reverts to an XML-style format that was likely part of its training data.

---

## Fix Options

### Option 1: Model-side Fix (Recommended)

Fix GLM-4.7's function calling training to consistently use the OpenAI API format.

### Option 2: Prompt-side Fix

Add explicit instruction to system prompt:

```
CRITICAL: Always use the function calling API to invoke tools. NEVER output tool calls as text like <tool_call>, <arg_key>, <arg_value> or any XML/markup format. Tool calls must ONLY be made through the proper API mechanism.
```

### Option 3: Plugin-side Recovery

Parse XML tool calls from text output as a fallback mechanism and convert them to proper tool calls.

---

## JSON Summary

```json
{
  "bug_name": "GLM-4.7 XML Tool Call Format Bug",
  "affected_model": "zai-glm-4.7 (accounts/fireworks/models/glm-4p7)",
  "impact": {
    "confirmed_affected_tasks": 3,
    "total_tasks_analyzed": 100,
    "percentage": "3%"
  },
  "affected_tasks": [
    "pinterest__ktlint-1997",
    "ankidroid__Anki-Android-16400",
    "pinterest__ktlint-1857"
  ],
  "root_cause": "Model inconsistently uses OpenAI function calling API, sometimes outputting tool calls as XML text instead",
  "xml_format_observed": "<tool_call>{tool_name}<arg_key>{param}</arg_key><arg_value>{value}</arg_value>",
  "evidence_chain": [
    {
      "step": 1,
      "source": "agent_log.json",
      "finding": "Iteration shows 0 tool_calls despite model intending to call tools",
      "example": "pinterest__ktlint-1997 iteration 3: 5376ms runtime, 0 tool_calls"
    },
    {
      "step": 2,
      "source": "idea.log",
      "finding": "XML-style tool call syntax in [THINKING] text stream",
      "example": "[THINKING]...<tool_call>list_dir<arg_key>target_directory</arg_key><arg_value>/project/..."
    },
    {
      "step": 3,
      "source": "idea.log",
      "finding": "finish_reason='stop' instead of 'tool_calls'",
      "example": "Received finish reason: stop"
    },
    {
      "step": 4,
      "source": "HeadlessAgentLoop.kt:551-555",
      "finding": "hasToolCalls=false triggers early termination",
      "code": "if (!hasToolCalls) { return false }"
    }
  ]
}
```
