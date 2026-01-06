# Firebender Agent Sandbox

This directory contains tools for running the Firebender IntelliJ agent in a sandbox environment, both locally and on Modal.

## Overview

The sandbox provides:
1. **Xvfb virtual display** - Runs IntelliJ without a physical display while preserving full IDE functionality
2. **Agent server mode** - Starts Firebender with an HTTP API for programmatic control
3. **Structured responses** - Get JSON responses from agent queries

## Quick Start

### Local Testing (with display)

On macOS or Linux with a GUI:

```bash
# Clone and run a test query
python swebench/harness/firebender_sandbox_local.py \
    --query "What files are in the src directory?"
```

### Local Testing (headless - Linux only)

On a Linux server without a display:

```bash
# Install Xvfb if not present
sudo apt-get install xvfb

# Run headless
python swebench/harness/firebender_sandbox_local.py \
    --headless \
    --query "What files are in the src directory?"
```

### Modal Cloud

```bash
# Run the sandbox on Modal
modal run swebench/harness/firebender_sandbox_modal.py

# With custom query
modal run swebench/harness/firebender_sandbox_modal.py \
    --query "Add logs to AutocompleteCache.kt"
```

## How It Works

### 1. Repository Setup

The sandbox clones the Firebender plugin from:
- **Repo**: `https://github.com/firebenders/android-studio-copilot.git`
- **Branch**: `aman/firebender-harness`

### 2. Virtual Display (Xvfb)

IntelliJ requires a display even in headless mode. We use Xvfb (X Virtual Framebuffer) to provide this:

```bash
Xvfb :99 -screen 0 1920x1080x24 -ac -nolisten tcp
```

This creates a virtual 1920x1080 display that IntelliJ can render to without any visible output.

### 3. Agent Server

The IDE is started with environment variables that enable the agent server:

```bash
FIREBENDER_AGENT_SERVER=true \
FIREBENDER_AGENT_SERVER_PORT=8742 \
./gradlew runIde
```

### 4. HTTP API

Once running, you can interact with the agent via HTTP:

```bash
# Run an agent query
curl -s -X POST http://localhost:8742/agent/run \
    -H "Content-Type: application/json" \
    -d '{"query": "Add logs to AutocompleteCache.kt"}' | jq .
```

## Files

| File | Description |
|------|-------------|
| `firebender_sandbox_modal.py` | Modal cloud sandbox with Xvfb and IDE setup |
| `firebender_sandbox_local.py` | Local testing script (no Modal required) |

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FIREBENDER_AGENT_SERVER` | Enable agent server mode | `true` |
| `FIREBENDER_AGENT_SERVER_PORT` | HTTP server port | `8742` |
| `DISPLAY` | X11 display (set by Xvfb) | `:99` |

### Timeouts

- **IDE Startup**: 300 seconds (5 minutes) - IntelliJ needs time to index
- **Query**: 120 seconds (2 minutes) - Agent task completion

## Troubleshooting

### IDE fails to start

1. Check the log file in `logs/` directory
2. Ensure Java 17+ is installed
3. On Linux, verify Xvfb is running: `ps aux | grep Xvfb`

### Agent server not responding

1. Wait longer - IDE indexing can take several minutes
2. Check if the agent server endpoint exists in the harness branch
3. Verify the port isn't already in use: `lsof -i :8742`

### Modal timeout

Increase the timeout in the Modal function decorator or use:
```bash
modal run swebench/harness/firebender_sandbox_modal.py --ide-timeout 600
```

## Development

To iterate on the sandbox:

1. Start with local testing to verify the setup works
2. Use `--query` to test different agent capabilities
3. Check logs for errors and agent behavior
4. Deploy to Modal for CI/automated testing

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Modal Container                     │
│                                                      │
│  ┌──────────────┐     ┌───────────────────────────┐ │
│  │    Xvfb      │────>│   IntelliJ IDE            │ │
│  │  (Display)   │     │   + Firebender Plugin     │ │
│  └──────────────┘     │   + Agent Server (:8742)  │ │
│                       └───────────────────────────┘ │
│                                 │                    │
│                                 ▼                    │
│                       ┌───────────────────────────┐ │
│                       │   HTTP Agent API          │ │
│                       │   POST /agent/run         │ │
│                       └───────────────────────────┘ │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   Test Script /       │
              │   Kotlin-bench Task   │
              └───────────────────────┘
```
