# Kotlin-bench Agentic Evaluation

Run agentic evaluations against the Kotlin-bench dataset using pre-baked Docker images with IDE already indexed and Gradle synced.

## Overview

This directory contains the clean, consolidated pipeline for running agentic evaluations:

```
agent-bench/
├── run_eval.py            # Main entry point for running evaluations
├── constants.py           # Loads config from JSON, provides helpers
├── config/
│   └── anki.json          # SINGLE SOURCE OF TRUTH for Anki (used by Dockerfile + Python)
├── download_data.py       # Utility to download/refresh dataset
├── data/
│   └── kotlin_bench.json  # Dataset with 100 tasks
└── README.md              # This file
```

## Quick Start

### Prerequisites

1. **Modal CLI** installed and configured:
   ```bash
   pip install modal
   modal token new
   ```

2. **GitHub Token** secret in Modal (for building the Docker image):
   ```bash
   modal secret create github-token GITHUB_TOKEN=ghp_xxx
   ```

### Running Evaluations

```bash
# List all available Anki tasks
modal run agent-bench/run_eval.py --list-tasks

# Run a single task with GPT-5.2-Codex
modal run agent-bench/run_eval.py --task-id ankidroid__Anki-Android-16395 --model gpt-5.2-codex

# Run all Anki tasks in parallel with a specific model
modal run agent-bench/run_eval.py --all-tasks --model gpt-5.2-codex

# Run with multiple models in parallel
modal run agent-bench/run_eval.py --all-tasks --models gpt-5.2-codex,claude-sonnet-4-20250514,gpt-5.1-codex

# Run sequentially (for debugging)
modal run agent-bench/run_eval.py --all-tasks --model gpt-5.2-codex --no-parallel

# Save results to file
modal run agent-bench/run_eval.py --all-tasks --model gpt-5.2-codex --output results.json
```

### Supported Models

The evaluation system accepts any model identifier string. The model name is passed to the Firebender agent server which handles the LLM API calls. Common models include:

- **GPT Models**: `gpt-5.2-codex`, `gpt-5.1-codex`, `gpt-4.1`
- **Claude Models**: `claude-sonnet-4-20250514`, `claude-opus-4-5`, `claude-3.7-sonnet`, `claude-3.5-sonnet`
- **Gemini Models**: `gemini-2.5-pro`, `gemini-3-pro-preview`, `gemini-3-flash-preview`
- **Custom Models**: Any model identifier supported by your Firebender configuration

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Modal Container (per task)                        │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │             anki-prebaked Docker Image                          ││
│  │  ┌─────────────────────┐  ┌──────────────────────────────────┐ ││
│  │  │  Pre-indexed IDE    │  │  Anki-Android (gradle synced)    │ ││
│  │  │  + Firebender       │  │  at /project                     │ ││
│  │  └─────────────────────┘  └──────────────────────────────────┘ ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  Pipeline Steps:                                                     │
│  1. Reset to task's base_commit                                     │
│  2. Configure JDK + Android SDK (version from MAP_VERSION_TO_INSTALL)│
│  3. Run installation scripts (patch build files, etc.)              │
│  4. Start agent server (./gradlew runAgentServer)                   │
│  5. Wait for /ready endpoint                                        │
│  6. Send problem_statement to /agent/run                            │
└─────────────────────────────────────────────────────────────────────┘
```

## Dataset

The Kotlin-bench dataset contains 100 tasks across 6 repositories. Currently, we focus on **Anki-Android** tasks (22 total).

| Repo | Tasks | Status |
|------|-------|--------|
| `ankidroid/Anki-Android` | 22 | **Supported** (pre-baked image) |
| `pinterest/ktlint` | 36 | Planned |
| `wordpress-mobile/WordPress-Android` | 18 | Planned |
| `Kotlin/kotlinx.coroutines` | 12 | Planned |
| `Kotlin/kotlinx-datetime` | 6 | Planned |
| `thunderbird/thunderbird-android` | 6 | Planned |

## Task Instance Format

Each task in `data/kotlin_bench.json` has:

```json
{
  "instance_id": "ankidroid__Anki-Android-16395",
  "repo": "ankidroid/Anki-Android",
  "version": "2.18",
  "base_commit": "bbfd8f4a10c796d4b955d54530c7f11e81ca250d",
  "problem_statement": "The bug description from GitHub issue...",
  "hints_text": "Discussion and hints from maintainers...",
  "patch": "The gold patch that fixes the bug",
  "test_patch": "Test code that verifies the fix",
  "FAIL_TO_PASS": ["tests that should pass after fix"],
  "PASS_TO_PASS": ["tests that should remain passing"]
}
```

## Evaluation Result Format

Each evaluation returns:

```json
{
  "instance_id": "ankidroid__Anki-Android-16395",
  "model": "firebender",
  "success": true,
  "agent_response": { ... },
  "total_duration_seconds": 245.3,
  "setup_duration_seconds": 12.1,
  "server_startup_seconds": 180.5,
  "agent_query_seconds": 52.7,
  "log_file": "/logs/eval/ankidroid__Anki-Android-16395/agent_server.log"
}
```

## Installation Scripts

Each repo has a JSON config file in `config/` that defines:

- **jdk_version**: Correct JDK for the repo (e.g., JDK 17 for Anki, JDK 11 for coroutines)
- **install_script**: Patches build files for compatibility
- **android_sdk_packages**: Required SDK components
- **test_command**: How to run tests

Example for Anki-Android (`config/anki.json`):
```json
{
  "repo": "ankidroid/Anki-Android",
  "jdk_version": "17.0.9-tem",
  "base_commit": "bbfd8f4a10c796d4b955d54530c7f11e81ca250d",
  "install_script": "set -e\necho 'Running install script...'\n...",
  "test_command": "./gradlew :AnkiDroid:testPlayDebugUnitTest"
}
```

This JSON is read by **both**:
- **Dockerfile** (via `jq`) - runs install script before warmupProject
- **Python** (`constants.py`) - loads config for runtime use

The install scripts handle common issues like:
- Removing Amazon App Store plugin dependencies
- Fixing Java version compatibility
- Pinning unstable dependency versions
- Patching gradle.properties memory settings

## Pre-baked Docker Image

The `anki-prebaked` image (`docker/anki-prebaked/Dockerfile`) contains:

- **IntelliJ + Firebender** plugin (pre-built)
- **Anki-Android** repository (pre-cloned at `/project`)
- **JDK 17** (via SDKMAN, for the project)
- **JDK 21** (for IntelliJ itself)
- **Android SDK** (with required build tools)
- **Pre-warmed caches** (Gradle + IDE indexes from `warmupProject`)

This means agent server startup is **much faster** (~2-3 minutes vs 10+ minutes) because:
- No need to download/index the project
- Gradle dependencies are cached
- IDE indexes are pre-built

### Building the Image

The image is built automatically by Modal on first run. To manually rebuild:

```bash
export GITHUB_TOKEN=ghp_xxx
modal run docker/anki-prebaked/build_modal.py
```

## API Reference

### Agent Server Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ready` | GET | Returns readiness status (indexing + gradle sync) |
| `/agent/run` | POST | Execute agent query |
| `/health` | GET | Simple health check |

### Example Query

```bash
curl -X POST http://localhost:8742/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"query": "Fix the bug where..."}'
```

## Troubleshooting

### Image Build Fails

- Make sure `GITHUB_TOKEN` is set in Modal secrets
- The image must be built on x86_64 (Modal handles this automatically)

### Server Never Becomes Ready

Check the logs at `/logs/eval/<instance_id>/agent_server.log`:
- Gradle sync errors
- Missing SDK components
- Memory issues (increase container memory)

### Task Fails to Reset

Some tasks may have base commits that aren't in shallow clone. The pipeline will attempt to fetch the specific commit.
