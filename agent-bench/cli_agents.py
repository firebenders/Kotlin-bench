"""
CLI Agent Abstraction Layer

Provides a pluggable interface for running CLI-based coding agents
(Claude Code, Codex CLI, etc.) against Kotlin-bench tasks.

Each agent implements the CLIAgent interface:
- run(prompt, repo_path) -> AgentResult

The agent is responsible for:
1. Executing the CLI tool with the prompt
2. Capturing structured trace output (JSON)
3. Returning the result including any errors

After the agent runs, the eval harness captures the git diff separately.
"""

import json
import os
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Dict, Any, List


@dataclass
class AgentResult:
    """Result of running a CLI-based coding agent."""
    success: bool
    trace: Optional[Dict[str, Any]] = None  # Structured JSON trace from agent
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0
    error: Optional[str] = None
    
    # Agent-specific metadata
    agent_name: str = ""
    model: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)


class CLIAgent(ABC):
    """
    Base class for CLI-based coding agents.
    
    Subclasses must implement:
    - run(prompt, repo_path) -> AgentResult
    - name (property): Unique identifier for the agent
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this agent (e.g., 'claude-code', 'codex-cli')."""
        ...
    
    @abstractmethod
    def run(self, prompt: str, repo_path: str, model: str = None) -> AgentResult:
        """
        Execute the agent on a coding task.
        
        Args:
            prompt: The problem statement / task description
            repo_path: Path to the git repository (already checked out at correct commit)
            model: Optional model identifier (agent-specific)
            
        Returns:
            AgentResult with trace, stdout/stderr, and timing info
        """
        ...


class ClaudeCodeAgent(CLIAgent):
    """
    Claude Code CLI agent.
    
    Executes `claude` CLI with --dangerously-skip-permissions flag.
    Captures structured JSON output via --output-format json.
    """
    
    def __init__(self, max_turns: int = 200):
        self.max_turns = max_turns
    
    @property
    def name(self) -> str:
        return "claude-code"
    
    def run(self, prompt: str, repo_path: str, model: str = None) -> AgentResult:
        """
        Run Claude Code CLI on the given prompt in the given repo.
        
        The CLI is invoked with:
        - --dangerously-skip-permissions: Skip all permission prompts
        - --output-format json: Get structured JSON output
        - --max-turns: Limit conversation turns
        - -p: Pass prompt directly
        
        Args:
            prompt: The task description
            repo_path: Path to the git repository
            model: Claude model to use (e.g., 'claude-sonnet-4', 'claude-opus-4')
        """
        start_time = time.time()
        
        # Build the claude command
        claude_args = [
            "claude",
            "--dangerously-skip-permissions",
            "--output-format", "json",
            "--max-turns", str(self.max_turns),
            "-p", prompt,
        ]
        
        if model:
            claude_args.extend(["--model", model])
        
        # Claude Code refuses --dangerously-skip-permissions as root.
        # If running as root (e.g., in a Docker/Modal container), wrap
        # the command with `su` to run as a non-root user.
        is_root = os.getuid() == 0
        eval_user = "evaluser"
        
        if is_root:
            # Make sure the repo is accessible to evaluser
            subprocess.run(["chmod", "-R", "a+rwX", repo_path], check=False)
            # Run as non-root user via su
            # Pass env vars through, especially ANTHROPIC_API_KEY
            env_exports = []
            for key in ["ANTHROPIC_API_KEY", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "PATH", "HOME"]:
                val = os.environ.get(key)
                if val:
                    env_exports.append(f"export {key}='{val}'")
            env_exports.append("export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1")
            env_exports.append(f"export HOME=/home/{eval_user}")
            
            # Escape prompt for shell
            escaped_prompt = prompt.replace("'", "'\\''")
            
            # Rebuild as a shell command string for su
            claude_cmd_parts = [
                "claude",
                "--dangerously-skip-permissions",
                "--output-format", "json",
                "--max-turns", str(self.max_turns),
                "-p", f"'{escaped_prompt}'",
            ]
            if model:
                claude_cmd_parts.extend(["--model", model])
            
            shell_cmd = " && ".join(env_exports) + " && " + " ".join(claude_cmd_parts)
            cmd = ["su", "-s", "/bin/bash", eval_user, "-c", shell_cmd]
            print(f"  Running Claude Code CLI as '{eval_user}' (non-root)...")
        else:
            cmd = claude_args
            print(f"  Running Claude Code CLI...")
        
        print(f"    Model: {model or 'default'}")
        print(f"    Max turns: {self.max_turns}")
        print(f"    Working directory: {repo_path}")
        
        try:
            env = {**os.environ, "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"}
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
                env=env,
            )
            
            duration = time.time() - start_time
            
            # Parse structured JSON output from stdout
            trace = None
            if result.stdout:
                try:
                    trace = json.loads(result.stdout)
                except json.JSONDecodeError:
                    # stdout may contain non-JSON output before the JSON
                    # Try to find the last JSON object
                    trace = _try_extract_json(result.stdout)
            
            success = result.returncode == 0
            error = None
            if not success:
                error = f"Claude Code exited with code {result.returncode}"
                if result.stderr:
                    error += f": {result.stderr[:500]}"
            
            print(f"    Completed in {duration:.1f}s (exit code: {result.returncode})")
            
            return AgentResult(
                success=success,
                trace=trace,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_seconds=duration,
                error=error,
                agent_name=self.name,
                model=model or "default",
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"    TIMED OUT after {duration:.1f}s")
            return AgentResult(
                success=False,
                duration_seconds=duration,
                error="Agent timed out after 3600 seconds",
                agent_name=self.name,
                model=model or "default",
            )
            
        except FileNotFoundError:
            duration = time.time() - start_time
            return AgentResult(
                success=False,
                duration_seconds=duration,
                error="Claude Code CLI not found. Install with: npm install -g @anthropic-ai/claude-code",
                agent_name=self.name,
                model=model or "default",
            )
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"    ERROR: {e}")
            return AgentResult(
                success=False,
                duration_seconds=duration,
                error=str(e),
                agent_name=self.name,
                model=model or "default",
            )


class CodexCLIAgent(CLIAgent):
    """
    OpenAI Codex CLI agent.
    
    Uses the Codex CLI (npm install -g @openai/codex) in non-interactive
    (full-auto) mode. The CLI auto-approves all file edits and commands.
    
    Docs: https://developers.openai.com/codex/sdk/
    CLI ref: https://developers.openai.com/docs/codex/cli
    """
    
    def __init__(self, max_turns: int = 200, **kwargs):
        self.max_turns = max_turns
    
    @property
    def name(self) -> str:
        return "codex-cli"
    
    def run(self, prompt: str, repo_path: str, model: str = None) -> AgentResult:
        """
        Run Codex CLI on the given prompt.
        
        Uses `codex exec` subcommand for non-interactive/CI execution.
        Pipes prompt via stdin using `-` as the PROMPT argument.
        
        Docs: https://developers.openai.com/codex/cli/reference/
        """
        start_time = time.time()
        
        # Codex CLI requires explicit auth — it doesn't auto-read OPENAI_API_KEY.
        # Run `codex login --with-api-key` piping the key via stdin.
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            print(f"  Authenticating Codex CLI via `codex login --with-api-key`...")
            login_result = subprocess.run(
                ["codex", "login", "--with-api-key"],
                input=api_key,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if login_result.returncode != 0:
                print(f"    Warning: codex login failed: {login_result.stderr[:200]}")
            else:
                print(f"    Codex CLI authenticated successfully")
        else:
            print(f"  Warning: OPENAI_API_KEY not set, codex may fail to authenticate")
        
        # Write prompt to temp file to avoid shell escaping issues
        prompt_file = os.path.join(repo_path, ".codex_prompt.txt")
        with open(prompt_file, "w") as f:
            f.write(prompt)
        
        # Build command: `codex exec` is the non-interactive subcommand
        # --full-auto: workspace-write sandbox + on-request approvals
        # --json: emit newline-delimited JSON events to stdout
        # -: read prompt from stdin
        cmd = ["codex", "exec", "--full-auto", "--json"]
        
        if model:
            cmd.extend(["--model", model])
        
        # Pass prompt via stdin (use `-` as PROMPT arg)
        cmd.append("-")
        
        print(f"  Running Codex CLI (exec mode)...")
        print(f"    Model: {model or 'default'}")
        print(f"    Working directory: {repo_path}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=3600,
                env=os.environ.copy(),
            )
            
            duration = time.time() - start_time
            
            # Try to parse structured output
            trace = None
            if result.stdout:
                try:
                    trace = json.loads(result.stdout)
                except json.JSONDecodeError:
                    trace = _try_extract_json(result.stdout)
                    if trace is None:
                        # Store raw output as trace
                        trace = {"raw_output": result.stdout}
            
            success = result.returncode == 0
            error = None
            if not success:
                error = f"Codex CLI exited with code {result.returncode}"
                if result.stderr:
                    error += f": {result.stderr[:500]}"
            
            print(f"    Completed in {duration:.1f}s (exit code: {result.returncode})")
            
            return AgentResult(
                success=success,
                trace=trace,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_seconds=duration,
                error=error,
                agent_name=self.name,
                model=model or "default",
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"    TIMED OUT after {duration:.1f}s")
            return AgentResult(
                success=False,
                duration_seconds=duration,
                error="Agent timed out after 3600 seconds",
                agent_name=self.name,
                model=model or "default",
            )
            
        except FileNotFoundError:
            duration = time.time() - start_time
            return AgentResult(
                success=False,
                duration_seconds=duration,
                error="Codex CLI not found. Install with: npm install -g @openai/codex",
                agent_name=self.name,
                model=model or "default",
            )
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"    ERROR: {e}")
            return AgentResult(
                success=False,
                duration_seconds=duration,
                error=str(e),
                agent_name=self.name,
                model=model or "default",
            )
        finally:
            # Cleanup prompt file
            try:
                os.remove(prompt_file)
            except OSError:
                pass


class CodexSDKAgent(CLIAgent):
    """
    OpenAI Codex SDK agent.
    
    Uses the @openai/codex-sdk TypeScript library for programmatic control
    with better trace capture. Runs via a small Node.js wrapper script.
    
    Docs: https://developers.openai.com/codex/sdk/
    """
    
    def __init__(self, max_turns: int = 200, **kwargs):
        self.max_turns = max_turns
    
    @property
    def name(self) -> str:
        return "codex-sdk"
    
    def run(self, prompt: str, repo_path: str, model: str = None) -> AgentResult:
        """
        Run Codex via the TypeScript SDK wrapper.
        
        Uses codex_runner.js which:
        1. Creates a Codex instance
        2. Starts a thread
        3. Runs the prompt
        4. Outputs structured JSON with the result and trace
        """
        start_time = time.time()
        
        # Locate the runner script
        runner_candidates = [
            os.path.join(os.path.dirname(__file__), "codex_runner.js"),
            "/root/agent-bench/codex_runner.js",
        ]
        runner_path = None
        for candidate in runner_candidates:
            if os.path.exists(candidate):
                runner_path = candidate
                break
        
        if not runner_path:
            return AgentResult(
                success=False,
                duration_seconds=0,
                error="codex_runner.js not found",
                agent_name=self.name,
                model=model or "default",
            )
        
        # Write prompt to temp file
        prompt_file = os.path.join(repo_path, ".codex_prompt.txt")
        with open(prompt_file, "w") as f:
            f.write(prompt)
        
        cmd = ["node", runner_path, "--prompt-file", prompt_file]
        if model:
            cmd.extend(["--model", model])
        
        print(f"  Running Codex SDK...")
        print(f"    Model: {model or 'default'}")
        print(f"    Working directory: {repo_path}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=3600,
                env=os.environ.copy(),
            )
            
            duration = time.time() - start_time
            
            # Parse structured JSON output
            trace = None
            if result.stdout:
                try:
                    trace = json.loads(result.stdout)
                except json.JSONDecodeError:
                    trace = _try_extract_json(result.stdout)
                    if trace is None:
                        trace = {"raw_output": result.stdout}
            
            success = result.returncode == 0
            error = None
            if not success:
                error = f"Codex SDK exited with code {result.returncode}"
                if result.stderr:
                    error += f": {result.stderr[:500]}"
            
            print(f"    Completed in {duration:.1f}s (exit code: {result.returncode})")
            
            return AgentResult(
                success=success,
                trace=trace,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_seconds=duration,
                error=error,
                agent_name=self.name,
                model=model or "default",
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"    TIMED OUT after {duration:.1f}s")
            return AgentResult(
                success=False,
                duration_seconds=duration,
                error="Agent timed out after 3600 seconds",
                agent_name=self.name,
                model=model or "default",
            )
            
        except FileNotFoundError:
            duration = time.time() - start_time
            return AgentResult(
                success=False,
                duration_seconds=duration,
                error="Node.js not found or codex_runner.js missing",
                agent_name=self.name,
                model=model or "default",
            )
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"    ERROR: {e}")
            return AgentResult(
                success=False,
                duration_seconds=duration,
                error=str(e),
                agent_name=self.name,
                model=model or "default",
            )
        finally:
            try:
                os.remove(prompt_file)
            except OSError:
                pass


# =============================================================================
# Agent Registry
# =============================================================================

AGENT_REGISTRY: Dict[str, type] = {
    "claude-code": ClaudeCodeAgent,
    "codex-cli": CodexCLIAgent,
    "codex-sdk": CodexSDKAgent,
}


def get_agent(agent_name: str, **kwargs) -> CLIAgent:
    """
    Get an agent instance by name.
    
    Args:
        agent_name: Name of the agent (e.g., 'claude-code', 'codex-cli')
        **kwargs: Additional arguments passed to agent constructor
        
    Returns:
        CLIAgent instance
        
    Raises:
        ValueError: If agent_name is not registered
    """
    if agent_name not in AGENT_REGISTRY:
        available = ", ".join(AGENT_REGISTRY.keys())
        raise ValueError(f"Unknown agent: {agent_name}. Available agents: {available}")
    
    return AGENT_REGISTRY[agent_name](**kwargs)


def list_agents() -> List[str]:
    """Return list of registered agent names."""
    return list(AGENT_REGISTRY.keys())


# =============================================================================
# Utility Functions
# =============================================================================

def _try_extract_json(text: str) -> Optional[dict]:
    """
    Try to extract a JSON object from text that may contain non-JSON content.
    
    Searches for the last complete JSON object in the text.
    """
    # Try parsing from the end (most likely location for structured output)
    text = text.strip()
    
    # Try the whole string first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON starting from last '{' or '['
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        last_end = text.rfind(end_char)
        if last_end == -1:
            continue
            
        # Search backwards for matching start
        depth = 0
        for i in range(last_end, -1, -1):
            if text[i] == end_char:
                depth += 1
            elif text[i] == start_char:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[i:last_end + 1])
                    except json.JSONDecodeError:
                        break
    
    return None


def capture_git_diff(repo_path: str) -> str:
    """
    Capture the git diff of all changes in the repository.
    
    Args:
        repo_path: Path to the git repository
        
    Returns:
        Git diff string (empty string if no changes or error)
    """
    try:
        result = subprocess.run(
            ["git", "diff"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout or ""
    except Exception as e:
        print(f"    Warning: Failed to capture git diff: {e}")
        return ""
