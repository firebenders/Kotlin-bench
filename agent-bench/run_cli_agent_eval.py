"""
CLI Agent Evaluation Runner for Kotlin-bench

Runs CLI-based coding agents (Claude Code, Codex CLI, etc.) against
Kotlin-bench tasks and compares their file modifications to ground truth.

Unlike the main run_eval.py which uses Docker + IntelliJ + Firebender,
this script runs agents directly on the codebase with just git.

Pipeline:
1. Load dataset and filter tasks
2. For each task:
   a. Clone repo and checkout base commit
   b. Run install scripts (JDK setup, build file patches)
   c. Run the CLI agent with the task prompt
   d. Capture git diff and agent trace
   e. Compare modified files to gold patch
   f. Optionally run tests (apply test_patch, run gradle)
3. Generate report with file-level accuracy metrics

Output Structure:
    outputs/cli_agent_data/
    ├── {instance_id}/
    │   └── {agent_name}/
    │       └── {model}/
    │           └── {rules|no-rules}/
    │               ├── agent_patch.diff       # Git diff of agent changes
    │               ├── agent_trace.json       # Structured JSON trace from agent
    │               ├── agent_stdout.log       # Raw stdout
    │               ├── file_comparison.json   # Precision/recall metrics
    │               ├── test_result.json       # Test pass/fail (if tests run)
    │               └── test_output.log        # Test execution logs
    └── cli_agent_report.json                  # Consolidated report

Rules:
    Per-repo rules files live in agent-bench/rules/{repo_key}.md
    (e.g., ankidroid__Anki-Android.md). When --rules is passed, the matching
    file is written as CLAUDE.md in the project root before the agent runs.
    
    Results are stored under "rules" or "no-rules" subdirectories so both
    can coexist and be compared in the report.

Usage:
    # Run without rules (baseline)
    modal run agent-bench/run_cli_agent_eval.py --all-tasks --repo anki --agent claude-code --model claude-sonnet-4

    # Run with per-repo rules
    modal run agent-bench/run_cli_agent_eval.py --all-tasks --repo anki --agent claude-code --model claude-sonnet-4 --rules

    # List tasks
    modal run agent-bench/run_cli_agent_eval.py --list-tasks

    # Also run tests (off by default, just file comparison)
    modal run agent-bench/run_cli_agent_eval.py --all-tasks --agent claude-code --model claude-sonnet-4 --run-tests
"""

import modal
import os
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv

# =============================================================================
# Fix Python import path
# =============================================================================
_this_file = Path(__file__).resolve()
_this_dir = _this_file.parent

load_dotenv()

# Add agent-bench directory to path for imports
_candidate_paths = [
    _this_dir,
    _this_dir / "agent-bench",
    Path("/root/agent-bench"),
]

for _p in _candidate_paths:
    if (_p / "constants.py").exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
        break

from constants import (
    get_install_specs,
    get_test_command,
    is_android_project,
)

# =============================================================================
# Modal Configuration
# =============================================================================

app = modal.App("kotlin-bench-cli-agent-eval")

# Volume for storing results
eval_volume = modal.Volume.from_name("kotlin-bench-cli-agent", create_if_missing=True)

# GitHub token secret
github_secret = modal.Secret.from_name("github-token")

# Anthropic API key for Claude Code
anthropic_secret = modal.Secret.from_name("anthropic-api-key")

# OpenAI API key for Codex CLI/SDK
openai_secret = modal.Secret.from_name("openai-api-key")

# Non-root user for Claude Code (it refuses --dangerously-skip-permissions as root)
EVAL_USER = "evaluser"
EVAL_USER_HOME = f"/home/{EVAL_USER}"

# Base image with git, Node.js (for Claude Code CLI), and Python
cli_agent_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "curl", "unzip", "zip", "wget", "sudo")
    # Install Node.js 20 (needed for Claude Code CLI)
    .run_commands(
        "curl -fsSL https://deb.nodesource.com/setup_20.x | bash -",
        "apt-get install -y nodejs",
    )
    # Install Claude Code CLI + Codex CLI + Codex SDK
    .run_commands(
        "npm install -g @anthropic-ai/claude-code",
        "npm install -g @openai/codex",
        "npm install -g @openai/codex-sdk",
    )
    # Install SDKMAN + common JDKs (non-interactive)
    .env({"SDKMAN_DIR": "/root/.sdkman"})
    .run_commands(
        'export SDKMAN_DIR="/root/.sdkman" && curl -s "https://get.sdkman.io?rcupdate=false" | bash',
    )
    .run_commands(
        'bash -c "source /root/.sdkman/bin/sdkman-init.sh && '
        'sed -i \"s/sdkman_auto_answer=false/sdkman_auto_answer=true/\" /root/.sdkman/etc/config && '
        'sdk install java 17.0.9-tem && '
        'sdk install java 11.0.20-tem && '
        'sdk install java 8.0.392-zulu"',
    )
    # Create non-root user for running Claude Code
    .run_commands(
        f"useradd -m -s /bin/bash {EVAL_USER}",
        f"echo '{EVAL_USER} ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers",
        # Give evaluser access to SDKMAN JDKs
        f"chmod -R a+rx /root/.sdkman",
    )
    .pip_install("python-dotenv")
    .add_local_dir(
        local_path=Path(__file__).parent,
        remote_path="/root/agent-bench",
    )
)

# Lightweight image for utility functions
util_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("python-dotenv")
    .add_local_dir(
        local_path=Path(__file__).parent,
        remote_path="/root/agent-bench",
    )
)

# =============================================================================
# Constants
# =============================================================================

EVAL_VOLUME_PATH = "/eval-cli-agent"
LOCAL_OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"
CLI_AGENT_DATA_DIR = LOCAL_OUTPUTS_DIR / "cli_agent_data"

# Rules directory (versioned rule files)
RULES_DIR = Path(__file__).parent / "rules"

# Repo GitHub URLs
REPO_GITHUB_URLS = {
    "ankidroid/Anki-Android": "https://github.com/ankidroid/Anki-Android.git",
    "wordpress-mobile/WordPress-Android": "https://github.com/wordpress-mobile/WordPress-Android.git",
    "pinterest/ktlint": "https://github.com/pinterest/ktlint.git",
    "Kotlin/kotlinx.coroutines": "https://github.com/Kotlin/kotlinx.coroutines.git",
    "thunderbird/thunderbird-android": "https://github.com/thunderbird/thunderbird-android.git",
    "Kotlin/kotlinx-datetime": "https://github.com/Kotlin/kotlinx-datetime.git",
}

REPO_SHORT_NAMES = {
    "anki": "ankidroid/Anki-Android",
    "wordpress": "wordpress-mobile/WordPress-Android",
    "ktlint": "pinterest/ktlint",
    "coroutines": "Kotlin/kotlinx.coroutines",
    "thunderbird": "thunderbird/thunderbird-android",
    "datetime": "Kotlin/kotlinx-datetime",
}

# Test framework commands per repo
MAP_REPO_TO_TEST_FRAMEWORK = {
    "wordpress-mobile/WordPress-Android": "./gradlew :WordPress:testWordPressVanillaDebugUnitTest",
    "ankidroid/Anki-Android": "./gradlew :AnkiDroid:testPlayDebugUnitTest",
    "pinterest/ktlint": "./gradlew :ktlint-ruleset-standard:test",
    "Kotlin/kotlinx.coroutines": "./gradlew :kotlinx-coroutines-core:jvmTest",
    "thunderbird/thunderbird-android": "./gradlew test",
    "Kotlin/kotlinx-datetime": "./gradlew :kotlinx-datetime:jvmTest",
}

# File extensions to exclude from test directives
NON_TEST_EXTS = [
    ".json", ".png", "csv", ".txt", ".md", ".jpg",
    ".jpeg", ".pkl", ".yml", ".yaml", ".toml",
]

SDKMAN_JAVA_PATH = "/root/.sdkman/candidates/java"

# Timeouts
AGENT_TIMEOUT = 3600  # 1 hour for agent
TEST_TIMEOUT = 1800   # 30 minutes for tests
SETUP_TIMEOUT = 300   # 5 minutes for setup
MODAL_TASK_TIMEOUT = 7200  # 2 hours total per task

# =============================================================================
# Rules Management (per-repo)
# =============================================================================

def _repo_to_rules_key(repo: str) -> str:
    """Convert repo name (e.g., 'ankidroid/Anki-Android') to rules filename key."""
    return repo.replace("/", "__")


def load_repo_rules(repo: str) -> Optional[str]:
    """
    Load per-repo rules from agent-bench/rules/{repo_key}.md.
    
    Args:
        repo: Repository name (e.g., 'ankidroid/Anki-Android')
    
    Returns:
        Rules content as a string, or None if no rules file exists for this repo.
    """
    key = _repo_to_rules_key(repo)
    candidates = [
        RULES_DIR / f"{key}.md",
        Path("/root/agent-bench/rules") / f"{key}.md",
    ]
    
    for path in candidates:
        if path.exists():
            content = path.read_text()
            print(f"  Loaded rules for '{repo}' from {path} ({len(content)} chars)")
            return content
    
    print(f"  No rules file found for '{repo}' (looked for {key}.md)")
    return None


def list_repo_rules() -> list:
    """List repos that have rules files."""
    repos = []
    for candidate_dir in [RULES_DIR, Path("/root/agent-bench/rules")]:
        if candidate_dir.exists():
            for f in sorted(candidate_dir.glob("*.md")):
                repo_key = f.stem
                if repo_key not in repos:
                    repos.append(repo_key)
    return repos


def write_project_rules(rules_content: str, project_path: str):
    """
    Write rules as CLAUDE.md in the project root for Claude Code to pick up.
    
    For Claude Code, this is "project memory" - loaded automatically at
    the start of every session.
    """
    claude_md_path = os.path.join(project_path, "CLAUDE.md")
    with open(claude_md_path, "w") as f:
        f.write(rules_content)
    print(f"    Wrote CLAUDE.md ({len(rules_content)} chars) to {project_path}")


# =============================================================================
# Task Data Structures (mirrored from run_eval.py for independence)
# =============================================================================

@dataclass
class TaskInstance:
    """A single evaluation task from Kotlin-bench."""
    instance_id: str
    repo: str
    version: str
    base_commit: str
    problem_statement: str
    hints_text: str = ""
    patch: Optional[str] = None  # Gold patch
    test_patch: Optional[str] = None
    FAIL_TO_PASS: List[str] = field(default_factory=list)
    PASS_TO_PASS: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "TaskInstance":
        return cls(
            instance_id=data.get("instance_id", "unknown"),
            repo=data.get("repo", ""),
            version=data.get("version", ""),
            base_commit=data.get("base_commit", ""),
            problem_statement=data.get("problem_statement", ""),
            hints_text=data.get("hints_text", ""),
            patch=data.get("patch"),
            test_patch=data.get("test_patch"),
            FAIL_TO_PASS=data.get("FAIL_TO_PASS", []),
            PASS_TO_PASS=data.get("PASS_TO_PASS", []),
        )

    def to_dict(self) -> dict:
        return asdict(self)


# =============================================================================
# Dataset Loading
# =============================================================================

def load_tasks(repos: List[str] = None) -> List[TaskInstance]:
    """Load tasks from the Kotlin-bench dataset."""
    dataset_path = Path(__file__).parent / "data" / "kotlin_bench.json"

    if not dataset_path.exists():
        # Try Modal container path
        dataset_path = Path("/root/agent-bench/data/kotlin_bench.json")
        if not dataset_path.exists():
            print(f"Dataset not found")
            return []

    with open(dataset_path) as f:
        all_tasks = json.load(f)

    resolved_repos = None
    if repos:
        resolved_repos = [REPO_SHORT_NAMES.get(r, r) for r in repos]

    if resolved_repos:
        tasks = [
            TaskInstance.from_dict(t)
            for t in all_tasks
            if t.get("repo") in resolved_repos
        ]
        print(f"Loaded {len(tasks)} tasks from {', '.join(resolved_repos)}")
    else:
        tasks = [TaskInstance.from_dict(t) for t in all_tasks]
        print(f"Loaded {len(tasks)} tasks (all repos)")

    return tasks


def get_task_by_id(task_id: str, repos: List[str] = None) -> Optional[TaskInstance]:
    """Get a specific task by instance_id."""
    tasks = load_tasks(repos)
    for task in tasks:
        if task.instance_id == task_id:
            return task
    return None


# =============================================================================
# Prompt Generation
# =============================================================================

def generate_eval_prompt(task: TaskInstance) -> str:
    """
    Generate the prompt for an evaluation task.

    Creates a well-structured prompt with the problem statement
    but excludes gold patch and test patch.
    """
    lines = []

    # Header with repo context
    lines.append(f"You are working on the {task.repo} repository.")
    lines.append(f"The codebase is at version {task.version} (commit: {task.base_commit[:8]}).")
    lines.append("")

    # Main problem statement
    lines.append("## Issue to Resolve")
    lines.append("")
    lines.append(task.problem_statement.strip())
    lines.append("")

    # Include hints if available
    if task.hints_text and task.hints_text.strip():
        lines.append("## Additional Context from Issue Discussion")
        lines.append("")
        lines.append(task.hints_text.strip())
        lines.append("")

    # Instructions
    lines.append("## Instructions")
    lines.append("")
    lines.append("Please analyze this issue and implement a fix. Make the necessary code changes to resolve the problem described above.")
    lines.append("")
    lines.append("Focus on:")
    lines.append("- Understanding the root cause of the issue")
    lines.append("- Making minimal, targeted changes to fix the problem")
    lines.append("- Ensuring your changes don't break existing functionality")
    lines.append("")

    # Evaluation context
    lines.append("## Important Evaluation Notes")
    lines.append("")
    lines.append("**Your work will be evaluated by running hidden tests that you do not have access to.** These tests will verify that your fix correctly addresses the issue. You should be confident in your solution before finishing.")
    lines.append("**If you write tests to verify your changes, create them in NEW test files only** - do NOT modify existing test files")
    lines.append("")

    # Critical restrictions
    lines.append("## CRITICAL RESTRICTIONS")
    lines.append("")
    lines.append("**NEVER use git commands.** Do not run `git status`, `git diff`, `git checkout`, `git reset`, or ANY other git commands. Using git will corrupt the evaluation environment and invalidate your entire submission. All file operations should be done through normal file editing and reading tools, not git.")

    return "\n".join(lines)


# =============================================================================
# Patch / File Utilities
# =============================================================================

def extract_files_from_patch(patch_content: str) -> List[str]:
    """Extract all file paths from a git diff patch."""
    if not patch_content:
        return []
    diff_pat = r"diff --git a/.* b/(.*)"
    return re.findall(diff_pat, patch_content)


def compare_file_sets(agent_patch: str, gold_patch: str) -> dict:
    """
    Compare files modified by agent vs ground truth gold patch.

    Returns precision, recall, and F1 score based on file-level matches.
    """
    agent_files = set(extract_files_from_patch(agent_patch))
    gold_files = set(extract_files_from_patch(gold_patch))

    # Remove CLAUDE.md from agent files (injected as project rules)
    agent_files.discard("CLAUDE.md")

    # Remove test files from gold_files for comparison
    # (agents shouldn't be expected to modify test files)
    gold_files_no_tests = {
        f for f in gold_files
        if not any(part in f.lower() for part in ["test/", "tests/", "test_", "_test."])
    }

    matched = agent_files & gold_files_no_tests

    precision = len(matched) / len(agent_files) if agent_files else 0.0
    recall = len(matched) / len(gold_files_no_tests) if gold_files_no_tests else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "agent_files": sorted(agent_files),
        "gold_files": sorted(gold_files),
        "gold_files_no_tests": sorted(gold_files_no_tests),
        "matched_files": sorted(matched),
        "extra_files": sorted(agent_files - gold_files_no_tests),
        "missing_files": sorted(gold_files_no_tests - agent_files),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "agent_file_count": len(agent_files),
        "gold_file_count": len(gold_files_no_tests),
        "matched_count": len(matched),
    }


def apply_patch(patch_content: str, project_path: str, patch_name: str = "patch") -> tuple:
    """Apply a patch to the repository. Returns (success, error_message)."""
    if not patch_content:
        return True, None

    patch_path = f"/tmp/{patch_name}_{os.getpid()}.patch"
    with open(patch_path, "w") as f:
        f.write(patch_content)

    result = subprocess.run(
        ["git", "apply", "--verbose", patch_path],
        cwd=project_path,
        capture_output=True,
        text=True,
    )

    try:
        os.remove(patch_path)
    except OSError:
        pass

    if result.returncode != 0:
        # Try with --3way as fallback
        with open(patch_path, "w") as f:
            f.write(patch_content)
        result = subprocess.run(
            ["git", "apply", "--3way", patch_path],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        try:
            os.remove(patch_path)
        except OSError:
            pass

        if result.returncode != 0:
            return False, f"Patch apply failed: {result.stderr[:500]}"

    return True, None


def reset_files_to_commit(files: List[str], commit: str, project_path: str) -> tuple:
    """Reset specific files to their state at a given commit."""
    if not files:
        return True, None

    errors = []
    for filepath in files:
        try:
            result = subprocess.run(
                ["git", "checkout", commit, "--", filepath],
                cwd=project_path,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                errors.append(f"{filepath}: {result.stderr.strip()}")
        except Exception as e:
            errors.append(f"{filepath}: {e}")

    if errors:
        return False, "; ".join(errors)
    return True, None


def capture_git_diff(repo_path: str) -> str:
    """Capture git diff of all changes in the repository, excluding CLAUDE.md."""
    try:
        # Include both staged and unstaged changes, excluding CLAUDE.md
        # which we write as project rules for the agent
        result = subprocess.run(
            ["git", "diff", "HEAD", "--", ".", ":(exclude)CLAUDE.md"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout or ""
    except Exception as e:
        print(f"    Warning: Failed to capture git diff: {e}")
        return ""


# =============================================================================
# Test Execution
# =============================================================================

def get_test_directives(instance: dict) -> list:
    """Get test directives from the test_patch."""
    diff_pat = r"diff --git a/.* b/(.*)"
    test_patch = instance.get("test_patch", "")
    if not test_patch:
        return []

    directives = re.findall(diff_pat, test_patch)
    directives = [
        d for d in directives if not any(d.endswith(ext) for ext in NON_TEST_EXTS)
    ]
    directives = [
        d for d in directives
        if (d.rsplit('.', 1)[0] if '.' in d else d).endswith('Test')
    ]

    repo = instance.get("repo", "")

    if repo == "ankidroid/Anki-Android":
        directives = [d for d in directives if d.startswith("AnkiDroid/src/test")]
    if repo == "pinterest/ktlint":
        directives = [d for d in directives if d.startswith("ktlint-ruleset-standard/src/test/kotlin")]
    if repo == "Kotlin/kotlinx.coroutines":
        directives_transformed = []
        for d in directives:
            if d.startswith("kotlinx-coroutines-core"):
                file_name = d.split("/")[-1]
                if file_name.endswith(".kt"):
                    file_name = file_name[:-3]
                elif file_name.endswith(".java"):
                    file_name = file_name[:-5]
                directives_transformed.append(f'"*.{file_name}"')
        directives = directives_transformed
    if repo == "Kotlin/kotlinx-datetime":
        directives = [d for d in directives if d.startswith("core/common/test")]

    return directives


def get_test_cmd(instance: dict) -> Optional[str]:
    """Generate the test command for a task instance."""
    directives = get_test_directives(instance)
    directives_transformed = []
    repo = instance.get("repo", "")

    for d in directives:
        if d.endswith(".kt") or d.endswith(".java"):
            d = d[:-3] if d.endswith(".kt") else d
            d = d[:-5] if d.endswith(".java") else d

            if "src/test/java/" in d:
                package_path = d.split("src/test/java/")[-1].replace("/", ".")
                directives_transformed.append(package_path)
            elif "src/test/kotlin/" in d:
                package_path = d.split("src/test/kotlin/")[-1].replace("/", ".")
                directives_transformed.append(package_path)
            else:
                package_path = d.replace("/", ".")
                directives_transformed.append(package_path)
        else:
            directives_transformed.append(d)

    if directives_transformed:
        test_type = MAP_REPO_TO_TEST_FRAMEWORK.get(repo, "./gradlew test")
        if repo in ("Kotlin/kotlinx.coroutines", "Kotlin/kotlinx-datetime", "thunderbird/thunderbird-android"):
            return test_type
        else:
            formatted_directives = " --tests " + " --tests ".join(directives_transformed)
            return test_type + formatted_directives
    else:
        return None


def run_tests(task: TaskInstance, project_path: str, env: dict) -> dict:
    """
    Run tests for a task.

    Steps:
    1. Reset test files to base commit
    2. Apply test_patch
    3. Run test command
    """
    start_time = time.time()

    # Reset test files
    test_files = extract_files_from_patch(task.test_patch)
    if test_files:
        reset_files_to_commit(test_files, task.base_commit, project_path)

    # Apply test patch
    success, error = apply_patch(task.test_patch, project_path, "test")
    if not success:
        return {
            "passed": False,
            "error": f"test patch apply failed: {error}",
            "duration_seconds": time.time() - start_time,
        }

    # Get test command
    task_dict = task.to_dict()
    test_cmd = get_test_cmd(task_dict)
    if not test_cmd:
        test_cmd = MAP_REPO_TO_TEST_FRAMEWORK.get(task.repo, "./gradlew test")

    print(f"    Test command: {test_cmd}")

    try:
        result = subprocess.run(
            test_cmd,
            shell=True,
            cwd=project_path,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=TEST_TIMEOUT,
        )

        duration = time.time() - start_time
        passed = result.returncode == 0
        print(f"    Tests {'PASSED' if passed else 'FAILED'} in {duration:.1f}s")

        return {
            "passed": passed,
            "error": None if passed else "Tests failed (see test_output.log)",
            "duration_seconds": duration,
            "return_code": result.returncode,
            "output": result.stdout or "",
        }

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print(f"    Tests TIMED OUT after {TEST_TIMEOUT}s")
        return {
            "passed": False,
            "error": f"Tests timed out after {TEST_TIMEOUT} seconds",
            "duration_seconds": duration,
        }
    except Exception as e:
        duration = time.time() - start_time
        print(f"    Tests ERROR: {e}")
        return {
            "passed": False,
            "error": str(e),
            "duration_seconds": duration,
        }


# =============================================================================
# Repository Setup
# =============================================================================

def clone_and_checkout(repo: str, base_commit: str, project_path: str) -> bool:
    """
    Clone repo and checkout the base commit.

    Args:
        repo: Full repo name (e.g., 'ankidroid/Anki-Android')
        base_commit: Git commit hash to checkout
        project_path: Where to clone the repo
    """
    github_url = REPO_GITHUB_URLS.get(repo)
    if not github_url:
        print(f"  Unknown repo: {repo}")
        return False

    print(f"  Cloning {repo}...")

    try:
        # Clone with depth 1 first (fast)
        result = subprocess.run(
            ["git", "clone", "--depth", "1", github_url, project_path],
            capture_output=True,
            text=True,
            timeout=SETUP_TIMEOUT,
        )

        if result.returncode != 0:
            print(f"  Clone failed: {result.stderr[:300]}")
            return False

        # Fetch the specific commit
        print(f"  Fetching commit {base_commit[:8]}...")
        subprocess.run(
            ["git", "fetch", "--depth=1", "origin", base_commit],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=SETUP_TIMEOUT,
        )

        # Checkout the base commit
        result = subprocess.run(
            ["git", "-c", "advice.detachedHead=false", "checkout", base_commit],
            cwd=project_path,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            # If commit not in shallow clone, do a full fetch
            print(f"  Shallow fetch failed, doing unshallow...")
            subprocess.run(
                ["git", "fetch", "--unshallow"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=600,
            )
            result = subprocess.run(
                ["git", "-c", "advice.detachedHead=false", "checkout", base_commit],
                cwd=project_path,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(f"  Checkout failed: {result.stderr[:300]}")
                return False

        print(f"  Successfully checked out {base_commit[:8]}")
        return True

    except subprocess.TimeoutExpired:
        print(f"  Clone/checkout timed out")
        return False
    except Exception as e:
        print(f"  Clone/checkout error: {e}")
        return False


def setup_environment(task: TaskInstance, project_path: str) -> dict:
    """
    Set up the build environment (JDK, Android SDK, install scripts).

    Returns the environment variables dict.
    """
    env = os.environ.copy()

    specs = get_install_specs(task.repo, task.version)
    jdk_version = specs.get("jdk_version", "17.0.9-tem")
    install_script = specs.get("install", "")

    # Set JAVA_HOME
    java_home = os.path.join(SDKMAN_JAVA_PATH, jdk_version)
    if os.path.exists(java_home):
        env["JAVA_HOME"] = java_home
        env["PATH"] = f"{java_home}/bin:{env.get('PATH', '')}"
        print(f"    JAVA_HOME: {java_home}")

    # Ensure gradlew is executable
    gradlew = os.path.join(project_path, "gradlew")
    if os.path.exists(gradlew):
        subprocess.run(["chmod", "+x", gradlew], check=False)

    # Run install script if provided
    if install_script and install_script.strip():
        print(f"    Running installation script...")
        try:
            result = subprocess.run(
                ["bash", "-c", install_script],
                cwd=project_path,
                env=env,
                capture_output=True,
                text=True,
                timeout=SETUP_TIMEOUT,
            )
            if result.returncode != 0:
                print(f"    Install script warning: {result.stderr[:300]}")
            else:
                print(f"    Install script completed")
        except Exception as e:
            print(f"    Install script error: {e}")

    return env


# =============================================================================
# Result Storage
# =============================================================================

def get_result_paths(instance_id: str, agent_name: str, model: str, rules_tag: str = "no-rules", base_dir: str = None) -> dict:
    """Get paths for storing results. rules_tag is 'rules' or 'no-rules'."""
    if base_dir is None:
        base_dir = EVAL_VOLUME_PATH

    base = os.path.join(base_dir, instance_id, agent_name, model, rules_tag)
    return {
        "base": base,
        "agent_patch": os.path.join(base, "agent_patch.diff"),
        "agent_trace": os.path.join(base, "agent_trace.json"),
        "agent_stdout": os.path.join(base, "agent_stdout.log"),
        "file_comparison": os.path.join(base, "file_comparison.json"),
        "test_result": os.path.join(base, "test_result.json"),
        "test_output": os.path.join(base, "test_output.log"),
    }


def save_results(
    paths: dict,
    agent_patch: str,
    agent_trace: Optional[dict],
    agent_stdout: str,
    file_comparison: dict,
    test_result: Optional[dict] = None,
    test_output: str = "",
):
    """Save all result files."""
    os.makedirs(paths["base"], exist_ok=True)

    # Agent patch
    with open(paths["agent_patch"], "w") as f:
        f.write(agent_patch)

    # Agent trace
    if agent_trace is not None:
        with open(paths["agent_trace"], "w") as f:
            json.dump(agent_trace, f, indent=2)

    # Agent stdout
    with open(paths["agent_stdout"], "w") as f:
        f.write(agent_stdout)

    # File comparison
    with open(paths["file_comparison"], "w") as f:
        json.dump(file_comparison, f, indent=2)

    # Test results
    if test_result is not None:
        test_result["timestamp"] = datetime.now().isoformat()
        with open(paths["test_result"], "w") as f:
            json.dump(test_result, f, indent=2)

    if test_output:
        with open(paths["test_output"], "w") as f:
            f.write(test_output)

    print(f"    Results saved to {paths['base']}")


# =============================================================================
# Main Evaluation Function (runs inside Modal container)
# =============================================================================

@app.function(
    image=cli_agent_image,
    volumes={EVAL_VOLUME_PATH: eval_volume},
    secrets=[github_secret, anthropic_secret, openai_secret],
    timeout=MODAL_TASK_TIMEOUT,
    memory=8192,
    cpu=4,
)
def run_eval_task(
    task_dict: dict,
    agent_name: str,
    model: str,
    use_rules: bool = False,
    run_tests_flag: bool = False,
    force_rerun: bool = False,
    max_turns: int = 200,
) -> dict:
    """
    Run a single evaluation task inside a Modal container.

    Args:
        task_dict: Task instance as a dict
        agent_name: Name of the agent to use
        model: Model identifier
        use_rules: Whether to inject per-repo rules as CLAUDE.md
        run_tests_flag: Whether to run tests (default False - only file comparison)
        force_rerun: Re-run even if cached results exist
        max_turns: Max conversation turns for agent

    Returns:
        Dict with evaluation results
    """
    # Re-import inside container
    import sys
    sys.path.insert(0, "/root/agent-bench")

    from cli_agents import get_agent

    task = TaskInstance.from_dict(task_dict)
    start_time = time.time()
    rules_tag = "rules" if use_rules else "no-rules"

    print("=" * 60)
    print(f"Task: {task.instance_id}")
    print(f"Agent: {agent_name}")
    print(f"Model: {model}")
    print(f"Rules: {rules_tag}")
    print("=" * 60)

    # Check for cached results
    paths = get_result_paths(task.instance_id, agent_name, model, rules_tag)
    if not force_rerun and os.path.exists(paths["file_comparison"]):
        print(f"  Cached results found, skipping (use --force to re-run)")
        try:
            with open(paths["file_comparison"]) as f:
                cached = json.load(f)
            cached["cached"] = True
            cached["instance_id"] = task.instance_id
            return cached
        except Exception:
            pass  # Fall through to re-run

    # Step 1: Clone and checkout
    project_path = f"/tmp/project-{task.instance_id}"
    if os.path.exists(project_path):
        subprocess.run(["rm", "-rf", project_path], check=False)

    if not clone_and_checkout(task.repo, task.base_commit, project_path):
        error_result = {
            "instance_id": task.instance_id,
            "agent": agent_name,
            "model": model,
            "rules": rules_tag,
            "success": False,
            "error": "Failed to clone/checkout repository",
            "duration_seconds": time.time() - start_time,
        }
        return error_result

    # Make project accessible to non-root evaluser and mark as safe git dir
    subprocess.run(["chmod", "-R", "a+rwX", project_path], check=False)
    subprocess.run(["git", "config", "--global", "--add", "safe.directory", project_path], check=False)

    # Step 2: Set up environment
    print("\n  Setting up environment...")
    env = setup_environment(task, project_path)

    # Step 2b: Snapshot git state after setup (so we diff only agent changes)
    print("\n  Snapshotting post-setup state...")
    subprocess.run(["git", "add", "-A"], cwd=project_path, check=False, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "eval: post-setup snapshot", "--allow-empty"],
        cwd=project_path, check=False, capture_output=True,
        env={**os.environ, "GIT_AUTHOR_NAME": "eval", "GIT_AUTHOR_EMAIL": "eval@eval",
             "GIT_COMMITTER_NAME": "eval", "GIT_COMMITTER_EMAIL": "eval@eval"},
    )

    # Step 2c: Write rules as CLAUDE.md in project root (if --rules)
    if use_rules:
        print(f"\n  Loading per-repo rules for '{task.repo}'...")
        rules_content = load_repo_rules(task.repo)
        if rules_content:
            write_project_rules(rules_content, project_path)
        else:
            print(f"  No rules file for this repo, running without rules")
    else:
        print(f"\n  Running without rules (no-rules mode)")

    setup_duration = time.time() - start_time
    print(f"  Setup completed in {setup_duration:.1f}s")

    # Step 3: Run agent
    print(f"\n  Running {agent_name} agent...")
    agent_start = time.time()

    prompt = generate_eval_prompt(task)
    agent = get_agent(agent_name, max_turns=max_turns)
    agent_result = agent.run(prompt, project_path, model=model)

    agent_duration = time.time() - agent_start
    print(f"  Agent completed in {agent_duration:.1f}s (success: {agent_result.success})")

    if not agent_result.success:
        print(f"\n  === AGENT FAILURE DETAILS ===")
        if agent_result.error:
            print(f"  Error: {agent_result.error}")
        if agent_result.stderr:
            print(f"  Stderr (last 2000 chars):")
            print(f"  {agent_result.stderr[-2000:]}")
        if agent_result.stdout:
            # Log tail of stdout for debugging
            print(f"  Stdout (last 1000 chars):")
            print(f"  {agent_result.stdout[-1000:]}")
        print(f"  === END FAILURE DETAILS ===\n")

    # Step 4: Capture git diff
    print("\n  Capturing git diff...")
    agent_patch = capture_git_diff(project_path)
    print(f"    Diff size: {len(agent_patch)} chars")

    if agent_patch:
        files_changed = extract_files_from_patch(agent_patch)
        print(f"    Files changed: {len(files_changed)}")
        for f in files_changed[:10]:
            print(f"      - {f}")
        if len(files_changed) > 10:
            print(f"      ... and {len(files_changed) - 10} more")

    # Step 5: Compare files to gold patch
    print("\n  Comparing to gold patch...")
    file_comparison = compare_file_sets(agent_patch, task.patch or "")
    print(f"    Precision: {file_comparison['precision']:.2%}")
    print(f"    Recall:    {file_comparison['recall']:.2%}")
    print(f"    F1 Score:  {file_comparison['f1_score']:.2%}")
    print(f"    Matched:   {file_comparison['matched_count']}/{file_comparison['gold_file_count']} gold files")

    if file_comparison['extra_files']:
        print(f"    Extra files: {file_comparison['extra_files']}")
    if file_comparison['missing_files']:
        print(f"    Missing files: {file_comparison['missing_files']}")

    # Step 6: Run tests (optional)
    test_result = None
    test_output = ""
    if run_tests_flag and task.test_patch:
        print("\n  Running tests...")
        test_result = run_tests(task, project_path, env)
        test_output = test_result.pop("output", "")
    else:
        print("\n  Skipping tests")

    # Step 7: Save results
    print("\n  Saving results...")
    save_results(
        paths=paths,
        agent_patch=agent_patch,
        agent_trace=agent_result.trace,
        agent_stdout=agent_result.stdout,
        file_comparison=file_comparison,
        test_result=test_result,
        test_output=test_output,
    )

    # Commit volume
    eval_volume.commit()

    total_duration = time.time() - start_time

    # Build result
    result = {
        "instance_id": task.instance_id,
        "agent": agent_name,
        "model": model,
        "rules": rules_tag,
        "success": agent_result.success,
        "error": agent_result.error,
        **file_comparison,
        "test_passed": test_result["passed"] if test_result else None,
        "test_error": test_result.get("error") if test_result else None,
        "duration": {
            "total_seconds": round(total_duration, 1),
            "setup_seconds": round(setup_duration, 1),
            "agent_seconds": round(agent_duration, 1),
            "test_seconds": round(test_result.get("duration_seconds", 0), 1) if test_result else None,
        },
        "timestamp": datetime.now().isoformat(),
    }

    print(f"\n  Task completed in {total_duration:.1f}s")
    print("=" * 60)

    return result


# =============================================================================
# Download Results from Volume
# =============================================================================

@app.function(
    image=util_image,
    volumes={EVAL_VOLUME_PATH: eval_volume},
    timeout=1800,
)
def download_results(agent_name: str, model: str, rules_tag: str = "no-rules") -> Dict[str, bytes]:
    """Download all result files for an agent/model/rules_tag from the Modal volume."""
    results = {}
    base_path = Path(EVAL_VOLUME_PATH)

    for task_dir in sorted(base_path.iterdir()):
        if not task_dir.is_dir():
            continue
        results_dir = task_dir / agent_name / model / rules_tag
        if not results_dir.exists():
            continue

        for result_file in results_dir.iterdir():
            if result_file.is_file():
                rel_path = str(result_file.relative_to(base_path))
                results[rel_path] = result_file.read_bytes()

    print(f"Found {len(results)} result files for {agent_name}/{model}/{rules_tag}")
    return results


# =============================================================================
# Report Generation
# =============================================================================

def merge_results_to_local(agent_name: str, model: str, files_data: Dict[str, bytes]):
    """Merge downloaded results into local cli_agent_data/ directory."""
    CLI_AGENT_DATA_DIR.mkdir(parents=True, exist_ok=True)

    for rel_path, data in files_data.items():
        local_path = CLI_AGENT_DATA_DIR / rel_path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(data)

    print(f"Merged {len(files_data)} files to {CLI_AGENT_DATA_DIR}")


def generate_report() -> dict:
    """
    Generate consolidated report from all local cli_agent_data results.

    Scans outputs/cli_agent_data/ for results and builds a summary
    with file accuracy metrics.
    """
    report = {
        "last_updated": datetime.now().isoformat(),
        "agents": [],
        "models": [],
        "rules_versions": [],
        "tasks": [],
        "results": {},
        "summary": {},
    }

    if not CLI_AGENT_DATA_DIR.exists():
        print("No cli_agent_data directory found")
        return report

    agents_set = set()
    models_set = set()
    rules_set = set()
    tasks_set = set()

    # Scan directory structure: {task_id}/{agent}/{model}/{rules}/
    for task_dir in sorted(CLI_AGENT_DATA_DIR.iterdir()):
        if not task_dir.is_dir():
            continue
        task_id = task_dir.name
        tasks_set.add(task_id)

        if task_id not in report["results"]:
            report["results"][task_id] = {}

        for agent_dir in sorted(task_dir.iterdir()):
            if not agent_dir.is_dir():
                continue
            agent = agent_dir.name
            agents_set.add(agent)

            if agent not in report["results"][task_id]:
                report["results"][task_id][agent] = {}

            for model_dir in sorted(agent_dir.iterdir()):
                if not model_dir.is_dir():
                    continue
                model = model_dir.name
                models_set.add(model)

                if model not in report["results"][task_id][agent]:
                    report["results"][task_id][agent][model] = {}

                # Check if this is the old format (files directly in model_dir)
                # or new format (rules subdirectories)
                has_rules_subdirs = any(
                    d.is_dir() for d in model_dir.iterdir()
                    if not d.name.startswith(".")
                )
                has_result_files = any(
                    f.name == "file_comparison.json" for f in model_dir.iterdir()
                    if f.is_file()
                )

                if has_result_files and not has_rules_subdirs:
                    # Old format: results directly in model dir (treat as "no-rules")
                    rules = "no-rules"
                    rules_set.add(rules)
                    entry = _parse_result_entry(task_id, agent, model, rules, model_dir)
                    report["results"][task_id][agent][model][rules] = entry
                else:
                    # New format: rules subdirectories
                    for rules_dir in sorted(model_dir.iterdir()):
                        if not rules_dir.is_dir():
                            continue
                        rules = rules_dir.name
                        rules_set.add(rules)
                        entry = _parse_result_entry(task_id, agent, model, rules, rules_dir)
                        report["results"][task_id][agent][model][rules] = entry

    report["agents"] = sorted(agents_set)
    report["models"] = sorted(models_set)
    report["rules_versions"] = sorted(rules_set)
    report["tasks"] = sorted(tasks_set)

    # Generate summary stats
    report["summary"] = _generate_summary(report)

    # Save report
    report_path = LOCAL_OUTPUTS_DIR / "cli_agent_report.json"
    LOCAL_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved to: {report_path}")

    return report


def _parse_result_entry(task_id: str, agent: str, model: str, rules: str, result_dir: Path) -> dict:
    """Parse result files for a task/agent/model/rules combination."""
    entry = {
        "has_patch": False,
        "test_passed": None,
        "precision": None,
        "recall": None,
        "f1_score": None,
        "rules": rules,
        "paths": {},
    }

    rel_prefix = f"cli_agent_data/{task_id}/{agent}/{model}/{rules}"

    # File comparison
    comparison_path = result_dir / "file_comparison.json"
    if comparison_path.exists():
        try:
            with open(comparison_path) as f:
                comparison = json.load(f)
            entry.update({
                "precision": comparison.get("precision"),
                "recall": comparison.get("recall"),
                "f1_score": comparison.get("f1_score"),
                "agent_files": comparison.get("agent_files", []),
                "gold_files": comparison.get("gold_files_no_tests", []),
                "matched_files": comparison.get("matched_files", []),
                "agent_file_count": comparison.get("agent_file_count", 0),
                "gold_file_count": comparison.get("gold_file_count", 0),
                "matched_count": comparison.get("matched_count", 0),
            })
        except (json.JSONDecodeError, IOError):
            pass

    # Patch
    patch_path = result_dir / "agent_patch.diff"
    if patch_path.exists():
        entry["has_patch"] = patch_path.stat().st_size > 0
        entry["paths"]["agent_patch"] = f"{rel_prefix}/agent_patch.diff"

    # Trace
    trace_path = result_dir / "agent_trace.json"
    if trace_path.exists():
        entry["paths"]["agent_trace"] = f"{rel_prefix}/agent_trace.json"

    # Test result
    test_result_path = result_dir / "test_result.json"
    if test_result_path.exists():
        try:
            with open(test_result_path) as f:
                test_data = json.load(f)
            entry["test_passed"] = test_data.get("passed")
            entry["test_error"] = test_data.get("error")
        except (json.JSONDecodeError, IOError):
            pass
        entry["paths"]["test_result"] = f"{rel_prefix}/test_result.json"

    return entry


def _generate_summary(report: dict) -> dict:
    """Generate summary statistics from report results.
    
    Summary is keyed by agent -> model -> rules_version.
    """
    summary = {
        "by_agent_model_rules": {},
        "overall": {},
    }

    for agent in report.get("agents", []):
        if agent not in summary["by_agent_model_rules"]:
            summary["by_agent_model_rules"][agent] = {}

        for model in report.get("models", []):
            if model not in summary["by_agent_model_rules"][agent]:
                summary["by_agent_model_rules"][agent][model] = {}

            for rules in report.get("rules_versions", []):
                stats = {
                    "total": 0,
                    "agent_success": 0,
                    "has_patch": 0,
                    "test_passed": 0,
                    "test_failed": 0,
                    "test_not_run": 0,
                    "avg_precision": 0.0,
                    "avg_recall": 0.0,
                    "avg_f1": 0.0,
                    "precisions": [],
                    "recalls": [],
                    "f1s": [],
                }

                for task_id in report.get("tasks", []):
                    entry = (
                        report.get("results", {})
                        .get(task_id, {})
                        .get(agent, {})
                        .get(model, {})
                        .get(rules)
                    )
                    if entry is None:
                        continue

                    stats["total"] += 1
                    if entry.get("has_patch"):
                        stats["has_patch"] += 1

                    if entry.get("test_passed") is True:
                        stats["test_passed"] += 1
                    elif entry.get("test_passed") is False:
                        stats["test_failed"] += 1
                    else:
                        stats["test_not_run"] += 1

                    if entry.get("precision") is not None:
                        stats["precisions"].append(entry["precision"])
                    if entry.get("recall") is not None:
                        stats["recalls"].append(entry["recall"])
                    if entry.get("f1_score") is not None:
                        stats["f1s"].append(entry["f1_score"])

                # Compute averages
                if stats["precisions"]:
                    stats["avg_precision"] = round(sum(stats["precisions"]) / len(stats["precisions"]), 4)
                if stats["recalls"]:
                    stats["avg_recall"] = round(sum(stats["recalls"]) / len(stats["recalls"]), 4)
                if stats["f1s"]:
                    stats["avg_f1"] = round(sum(stats["f1s"]) / len(stats["f1s"]), 4)

                # Remove raw lists from summary
                del stats["precisions"]
                del stats["recalls"]
                del stats["f1s"]

                if stats["total"] > 0:
                    stats["test_pass_rate"] = round(stats["test_passed"] / stats["total"], 4)
                    summary["by_agent_model_rules"][agent][model][rules] = stats

    return summary


# =============================================================================
# CLI Entry Point
# =============================================================================

@app.local_entrypoint()
def main(
    agent: str = "claude-code",
    model: str = None,
    models: str = None,
    rules: bool = False,
    task_id: str = None,
    task_ids: str = None,
    all_tasks: bool = False,
    list_tasks: bool = False,
    list_repos: bool = False,
    list_rules_flag: bool = False,
    repo: str = None,
    repos: str = None,
    run_tests: bool = False,
    force: bool = False,
    parallel: bool = True,
    max_turns: int = 200,
    download: bool = False,
    report_only: bool = False,
):
    """
    Run CLI agent evaluations on Kotlin-bench tasks.

    Args:
        agent: Agent to use (claude-code, codex-cli)
        model: Model identifier
        models: Multiple models, comma-separated
        rules: Inject per-repo rules as CLAUDE.md (default: off)
        task_id: Run a specific task
        task_ids: Run multiple tasks (comma-separated)
        all_tasks: Run all tasks
        list_tasks: List available tasks
        list_repos: List available repos
        list_rules_flag: List repos that have rules files
        repo: Filter by repository
        repos: Multiple repos, comma-separated
        run_tests: Run tests after agent completes (default: off, just file comparison)
        force: Force re-run even if cached
        parallel: Run tasks in parallel
        max_turns: Max conversation turns for agent
        download: Download results from Modal volume
        report_only: Just regenerate the report from local data
    """
    rules_tag = "rules" if rules else "no-rules"
    print("=" * 60)
    print("Kotlin-bench CLI Agent Evaluation")
    print("=" * 60)
    print(f"Agent: {agent}")
    print(f"Rules: {rules_tag}")

    # Report-only mode
    if report_only:
        report = generate_report()
        _print_report_summary(report)
        return

    # List repos that have rules files
    if list_rules_flag:
        available = list_repo_rules()
        print(f"\nRepos with rules files ({len(available)}):")
        for r in available:
            rules_path = RULES_DIR / f"{r}.md"
            size = rules_path.stat().st_size if rules_path.exists() else 0
            print(f"  {r:40} ({size} bytes)")
        return

    # Parse model list
    model_list = []
    if models:
        model_list = [m.strip() for m in models.split(",") if m.strip()]
    elif model:
        model_list = [model]

    # Parse repo list
    repo_list = []
    if repos:
        repo_list = [r.strip() for r in repos.split(",") if r.strip()]
    elif repo:
        repo_list = [repo]

    # List repos
    if list_repos:
        tasks = load_tasks()
        repo_counts = {}
        for t in tasks:
            repo_counts[t.repo] = repo_counts.get(t.repo, 0) + 1
        print(f"\nAvailable repositories ({len(repo_counts)}):")
        for repo_name, count in sorted(repo_counts.items()):
            short = next((k for k, v in REPO_SHORT_NAMES.items() if v == repo_name), "")
            print(f"  {short:12} {repo_name:40} {count:4} tasks")
        return

    # List tasks
    if list_tasks:
        tasks = load_tasks(repo_list or None)
        print(f"\nAvailable tasks ({len(tasks)}):")
        for t in tasks:
            short_repo = next((k for k, v in REPO_SHORT_NAMES.items() if v == t.repo), t.repo)
            gold_files = len(extract_files_from_patch(t.patch or ""))
            print(f"  {t.instance_id:50} [{short_repo:12}] ({gold_files} files in gold patch)")
        return

    # Download mode
    if download:
        if not model_list:
            print("Error: --model is required for --download")
            return
        for m in model_list:
            files = download_results.remote(agent, m, rules_tag)
            if files:
                merge_results_to_local(agent, m, files)
        report = generate_report()
        _print_report_summary(report)
        return

    # Validate model
    if not model_list:
        print("\nError: --model or --models is required")
        print("Example: --model claude-sonnet-4")
        return

    # Collect tasks to run
    tasks_to_run = []
    if task_id:
        task = get_task_by_id(task_id)
        if not task:
            print(f"Task not found: {task_id}")
            return
        tasks_to_run = [task]
    elif task_ids:
        for tid in task_ids.split(","):
            tid = tid.strip()
            task = get_task_by_id(tid)
            if task:
                tasks_to_run.append(task)
            else:
                print(f"Warning: Task not found: {tid}")
    elif all_tasks:
        tasks_to_run = load_tasks(repo_list or None)
    else:
        print("\nError: Specify --task-id, --task-ids, or --all-tasks")
        return

    if not tasks_to_run:
        print("No tasks to run")
        return

    # Build job list: (task, model) pairs
    jobs = []
    for task in tasks_to_run:
        for m in model_list:
            jobs.append((task, m))

    total_jobs = len(jobs)
    print(f"\nRunning {total_jobs} evaluations ({len(tasks_to_run)} tasks x {len(model_list)} models)")
    print(f"Agent: {agent}")
    print(f"Models: {', '.join(model_list)}")
    print(f"Rules: {rules_tag}")
    print(f"Run tests: {run_tests}")
    print(f"Parallel: {parallel}")
    print(f"Max turns: {max_turns}")
    print()

    # Run evaluations
    results = []
    if parallel and total_jobs > 1:
        # Run in parallel using Modal's .map()
        task_dicts = [task.to_dict() for task, _ in jobs]
        agent_names = [agent] * total_jobs
        models_list = [m for _, m in jobs]
        use_rules_list = [rules] * total_jobs
        run_tests_list = [run_tests] * total_jobs
        force_list = [force] * total_jobs
        max_turns_list = [max_turns] * total_jobs

        for i, result in enumerate(
            run_eval_task.map(
                task_dicts,
                agent_names,
                models_list,
                use_rules_list,
                run_tests_list,
                force_list,
                max_turns_list,
            )
        ):
            results.append(result)
            task_name = jobs[i][0].instance_id
            model_name = jobs[i][1]
            f1 = result.get("f1_score", "N/A")
            test = result.get("test_passed", "N/A")
            print(f"  [{i+1}/{total_jobs}] {task_name} ({model_name}): F1={f1}, test={test}")
    else:
        # Run sequentially
        for i, (task, m) in enumerate(jobs):
            print(f"\n--- [{i+1}/{total_jobs}] {task.instance_id} ({m}) ---")
            result = run_eval_task.remote(
                task.to_dict(), agent, m, rules, run_tests, force, max_turns
            )
            results.append(result)
            f1 = result.get("f1_score", "N/A")
            test = result.get("test_passed", "N/A")
            print(f"  Result: F1={f1}, test={test}")

    # Download and generate report
    print("\n" + "=" * 60)
    print("Downloading results and generating report...")
    print("=" * 60)

    for m in model_list:
        files = download_results.remote(agent, m, rules_tag)
        if files:
            merge_results_to_local(agent, m, files)

    report = generate_report()
    _print_report_summary(report)

    # Print per-task results
    print("\n--- Per-Task Results ---")
    for result in results:
        tid = result.get("instance_id", "?")
        f1 = result.get("f1_score", "N/A")
        prec = result.get("precision", "N/A")
        rec = result.get("recall", "N/A")
        test = result.get("test_passed", "N/A")
        dur = result.get("duration", {}).get("total_seconds", "N/A")
        err = result.get("error", "")
        status = "PASS" if test is True else ("FAIL" if test is False else "N/A")
        print(f"  {tid:50} F1={f1:6}  P={prec:6}  R={rec:6}  Test={status:4}  {dur}s  {err[:50] if err else ''}")


def _print_report_summary(report: dict):
    """Print a formatted summary of the report."""
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Agents: {', '.join(report.get('agents', []))}")
    print(f"Models: {', '.join(report.get('models', []))}")
    print(f"Rules:  {', '.join(report.get('rules_versions', []))}")
    print(f"Tasks:  {len(report.get('tasks', []))}")
    print()

    summary = report.get("summary", {}).get("by_agent_model_rules", {})
    for agent_name, agent_models in summary.items():
        for model_name, model_rules in agent_models.items():
            for rules_name, stats in model_rules.items():
                total = stats.get("total", 0)
                if total == 0:
                    continue
                print(f"  [{agent_name}] {model_name} (rules: {rules_name}):")
                print(f"    Tasks evaluated: {total}")
                print(f"    Has patch:       {stats.get('has_patch', 0)}/{total}")
                print(f"    Avg Precision:   {stats.get('avg_precision', 0):.2%}")
                print(f"    Avg Recall:      {stats.get('avg_recall', 0):.2%}")
                print(f"    Avg F1:          {stats.get('avg_f1', 0):.2%}")
                passed = stats.get("test_passed", 0)
                print(f"    Tests passed:    {passed}/{total} ({stats.get('test_pass_rate', 0):.1%})")
                print()

    print(f"Report: {LOCAL_OUTPUTS_DIR / 'cli_agent_report.json'}")
    print(f"Data:   {CLI_AGENT_DATA_DIR}")
