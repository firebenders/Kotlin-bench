"""
Firebender Agentic Evaluation Runner

This is the main entry point for running agentic evaluations against the
Kotlin-bench dataset. It uses pre-baked Docker images built from a unified
Dockerfile (agent-bench/docker/Dockerfile) with repo-specific configs.

Architecture:
- Unified Dockerfile with build args for each repository
- Configuration stored in agent-bench/config/{repo}.json
- IntelliJ IDEA CE with pre-warmed caches (indexing done at build time)
- Firebender plugin installed at runtime from firebender/Firebender.zip
- IDE started directly with `idea.sh /project` in agent server mode

Supported Repositories:
- ankidroid/Anki-Android
- wordpress-mobile/WordPress-Android
- pinterest/ktlint
- Kotlin/kotlinx.coroutines
- thunderbird/thunderbird-android
- Kotlin/kotlinx-datetime

Pipeline:
1. Load dataset and filter tasks by repo
2. Spin up a container per task instance / model pair
3. In each container:
   
   SETUP PHASE:
   - Reset to base commit
   - Configure JDK and Android SDK
   - Run custom installation scripts
   - Install Firebender plugin
   
   PATCH PHASE (based on --patch flag):
   - gold: Apply gold/correct patch from task instance
   - none: No code changes (baseline)
   - (default): Run agent OR use cached agent results
   
   TEST PHASE:
   - Apply test_patch from task instance
   - Run gradle test command
   - Save results

4. After all evals complete:
   - Download results from Modal volume
   - Merge into canonical outputs/data/ directory
   - Generate consolidated report (outputs/report.json)

Volume Structure (Modal: kotlin-bench-agent volume at /eval):
    /eval/{model}/{instance_id}/{settings_id}/
        ├── agent_result.json      # Agent server response
        ├── agent_patch.diff       # Git diff of code changes
        ├── agent_log.json         # Conversation log (OpenAI chat completions format)
        ├── idea.log               # IntelliJ IDEA IDE log
        ├── test_result.json       # Test pass/fail result
        └── test_output.log        # Full gradle test stdout/stderr

Local Output Structure (agent-bench/outputs/):
    outputs/
    ├── data/                      # Canonical data directory (task-first organization)
    │   └── {instance_id}/
    │       └── {model}/
    │           ├── agent_result.json
    │           ├── agent_patch.diff
    │           ├── agent_log.json
    │           ├── idea.log
    │           ├── test_result.json
    │           └── test_output.log
    ├── report.json                # Consolidated report (task->model->status)
    └── history/                   # Historical report snapshots
        └── report_{timestamp}.json

Report Format (report.json):
    The consolidated report is designed for dashboard rendering with:
    - tasks on X axis (sorted list of all task IDs)
    - models on Y axis (sorted list of all model IDs)
    - results[task_id][model] = {test_passed, has_patch, paths: {...}}
    
    Paths in the report are relative to outputs/ directory.

Usage:
    # List available tasks
    modal run agent-bench/run_eval.py --list-tasks
    
    # Run agent on single task
    modal run agent-bench/run_eval.py --task-id ankidroid__Anki-Android-16395
    
    # Run agent on all tasks
    modal run agent-bench/run_eval.py --all-tasks
    
    # Test with gold patches (validate benchmark - should pass)
    modal run agent-bench/run_eval.py --all-tasks --patch gold
    
    # Baseline test (no changes - tests should fail)
    modal run agent-bench/run_eval.py --all-tasks --patch none
    
    # Force re-run agent/tests
    modal run agent-bench/run_eval.py --task-id xxx --no-agent-cache --no-test-cache
    
    # Download results and create report (without running evals)
    modal run agent-bench/run_eval.py --download --model firebender
"""

import modal
import os
import json
import time
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict

from dotenv import load_dotenv

# =============================================================================
# Fix Python import path for constants module
# =============================================================================
# This file can be run from different locations:
# 1. Local: `modal run agent-bench/run_eval.py` from repo root
# 2. Local: `modal run run_eval.py` from agent-bench directory  
# 3. Modal container: file mounted at /root/run_eval.py, constants at /root/agent-bench/
#
# We need to add the correct directory to sys.path BEFORE importing constants.
_this_file = Path(__file__).resolve()
_this_dir = _this_file.parent

# Load environment variables from .env if present
load_dotenv()

# Fail early if GITHUB_TOKEN is not set
if not os.environ.get("GITHUB_TOKEN"):
    raise EnvironmentError(
        "GITHUB_TOKEN environment variable is not set.\n"
        "Please either:\n"
        "  1. Create a .env file with GITHUB_TOKEN=your_token_here\n"
        "  2. Export it in your shell: export GITHUB_TOKEN=ghp_xxx\n"
        "  3. Add it to ~/.zshrc for persistence across sessions\n"
        "  4. Create a Modal secret: modal secret create github-token GITHUB_TOKEN=ghp_xxx"
    )

# Candidate directories where constants.py might live
_candidate_paths = [
    _this_dir,                      # Same directory as this file (local run from agent-bench/)
    _this_dir / "agent-bench",      # Subdirectory (shouldn't happen but defensive)
    Path("/root/agent-bench"),      # Modal container mount location
]

for _p in _candidate_paths:
    if (_p / "constants.py").exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
        break

# Now import constants
from constants import (
    PROJECT_PATH,
    SDKMAN_JAVA_PATH,
    ANDROID_SDK_PATH,
    AGENT_PORT,
    get_install_specs,
    is_android_project,
)


# =============================================================================
# Test Command Generation (from swebench/harness/utils.py and constants.py)
# =============================================================================

# Map repo to base test command
MAP_REPO_TO_TEST_FRAMEWORK_KT = {
    "wordpress-mobile/WordPress-Android": "./gradlew :WordPress:testWordPressVanillaDebugUnitTest",
    "ankidroid/Anki-Android": "./gradlew :AnkiDroid:testPlayDebugUnitTest",
    "pinterest/ktlint": "./gradlew :ktlint-ruleset-standard:test",
    "Kotlin/kotlinx.coroutines": "./gradlew :kotlinx-coroutines-core:jvmTest",
    "thunderbird/thunderbird-android": "./gradlew test",
    "Kotlin/kotlinx-datetime": "./gradlew :kotlinx-datetime:jvmTest"
}

# File extensions to exclude from test directives
NON_TEST_EXTS = [
    ".json", ".png", "csv", ".txt", ".md", ".jpg", 
    ".jpeg", ".pkl", ".yml", ".yaml", ".toml",
]


def get_test_directives(instance: dict) -> list:
    """
    Get test directives from the test_patch of a task instance.
    
    Extracts test file paths from the test_patch diff and filters them
    to only include actual test files.
    
    Args:
        instance: Task instance dict with 'test_patch' and 'repo' keys
    Returns:
        List of test file paths/directives
    """
    import re
    
    # Get test directives from test patch and remove non-test files
    diff_pat = r"diff --git a/.* b/(.*)"
    test_patch = instance.get("test_patch", "")
    if not test_patch:
        return []
    
    directives = re.findall(diff_pat, test_patch)
    directives = [
        d for d in directives if not any(d.endswith(ext) for ext in NON_TEST_EXTS)
    ]

    # Filter directives to only include those ending with 'Test' (excluding extension)
    directives = [
        d for d in directives 
        if (d.rsplit('.', 1)[0] if '.' in d else d).endswith('Test')
    ]

    # Repo-specific filtering
    repo = instance.get("repo", "")
    
    if repo == "django/django":
        directives_transformed = []
        for d in directives:
            d = d[: -len(".py")] if d.endswith(".py") else d
            d = d[len("tests/") :] if d.startswith("tests/") else d
            d = d.replace("/", ".")
            directives_transformed.append(d)
        directives = directives_transformed

    if repo == "ankidroid/Anki-Android":
        # Only include unit tests (not Android emulator tests)
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


def get_test_cmd_from_instance(instance: dict) -> str:
    """
    Generate the test command for a task instance.
    
    Converts test file paths from get_test_directives() into a proper
    Gradle test command with --tests filters for specific test classes.
    
    Args:
        instance: Task instance dict
    Returns:
        Full test command string (e.g., "./gradlew :AnkiDroid:testPlayDebugUnitTest --tests com.ichi2.anki.SomeTest")
    """
    directives = get_test_directives(instance)
    directives_transformed = []
    repo = instance.get("repo", "")
        
    for d in directives:
        # Only process Kotlin or Java test files
        if d.endswith(".kt") or d.endswith(".java"):
            # Remove file extension
            d = d[:-3] if d.endswith(".kt") else d
            d = d[:-5] if d.endswith(".java") else d
            
            # Convert path to package format (src/test/java or src/test/kotlin prefix removal)
            if "src/test/java/" in d:
                package_path = d.split("src/test/java/")[-1].replace("/", ".")
                directives_transformed.append(package_path)
            elif "src/test/kotlin/" in d:
                package_path = d.split("src/test/kotlin/")[-1].replace("/", ".")
                directives_transformed.append(package_path)
            else:
                # Fall back to simple path conversion
                package_path = d.replace("/", ".")
                directives_transformed.append(package_path)
        else:
            # For non-Java/Kotlin files or already formatted class names
            directives_transformed.append(d)

    # Format directives for Gradle-style test filters
    if directives_transformed:
        test_type = MAP_REPO_TO_TEST_FRAMEWORK_KT.get(repo, "./gradlew test")
        if repo in ("Kotlin/kotlinx.coroutines", "Kotlin/kotlinx-datetime", "thunderbird/thunderbird-android"):
            # Run all tests for these repos
            return test_type
        else:
            # Use --tests flag for each test directive
            formatted_directives = " --tests " + " --tests ".join(directives_transformed)
            return test_type + formatted_directives
    else:
        # If no specific tests found, return None (caller should handle)
        return None


# =============================================================================
# Modal Configuration
# =============================================================================

app = modal.App("kotlin-bench-eval")

# =============================================================================
# Docker Images for Each Repository (Unified Dockerfile)
# =============================================================================
# Each repo has a pre-baked Docker image built from the unified Dockerfile
# (agent-bench/docker/Dockerfile) with repo-specific build args:
# - JDK version (via SDKMAN, from config)
# - Android SDK (conditional, from config)
# - IntelliJ IDEA CE with pre-warmed caches
# - Project cloned and indexed
#
# Firebender plugin is installed at RUNTIME (not baked into image).
# IDE is started with `idea.sh /project` in agent server mode.

# IntelliJ CE 2025.1 plugins directory
IDEA_PLUGINS_DIR = "/root/.local/share/JetBrains/IdeaIC2025.1"

# Path to Firebender plugin zip (will be installed at runtime)
FIREBENDER_PLUGIN_ZIP = "firebender/Firebender.zip"

# =============================================================================
# Docker Images for Each Repository (Pre-generated Dockerfiles)
# =============================================================================
# Each repo uses a pre-generated Dockerfile from agent-bench/docker/generated/
# These are built and cached by: modal run agent-bench/docker/build_modal.py
#
# The images include:
# - Project cloned and at base commit
# - JDK installed via SDKMAN
# - Android SDK (if needed)
# - IntelliJ IDEA CE with pre-warmed caches
#
# Firebender plugin is installed at RUNTIME (not baked into image).


def _create_repo_image(repo_name: str) -> modal.Image:
    """
    Create a Modal image from the pre-generated Dockerfile for a repository.
    
    Uses Dockerfiles from agent-bench/docker/generated/ which are built
    and verified by build_modal.py.
    """
    return (
        modal.Image.from_dockerfile(
            path=f"agent-bench/docker/generated/Dockerfile.{repo_name}",
            context_dir=".",
            add_python="3.11",
        )
        # Add the Firebender plugin zip to the image for runtime installation
        .add_local_file(FIREBENDER_PLUGIN_ZIP, "/tmp/Firebender.zip", copy=True)
        .add_local_dir(
            local_path=Path(__file__).parent,
            remote_path="/root/agent-bench",
        )
    )


# Build images for each repository (Modal will use cached images from build_modal.py)
anki_image = _create_repo_image("anki")
wordpress_image = _create_repo_image("wordpress")
ktlint_image = _create_repo_image("ktlint")
coroutines_image = _create_repo_image("coroutines")
thunderbird_image = _create_repo_image("thunderbird")
datetime_image = _create_repo_image("datetime")

# Mapping from full repo name to image
REPO_TO_IMAGE = {
    "ankidroid/Anki-Android": anki_image,
    "wordpress-mobile/WordPress-Android": wordpress_image,
    "pinterest/ktlint": ktlint_image,
    "Kotlin/kotlinx.coroutines": coroutines_image,
    "thunderbird/thunderbird-android": thunderbird_image,
    "Kotlin/kotlinx-datetime": datetime_image,
}

# Short names for CLI convenience (maps to full GitHub repo path)
REPO_SHORT_NAMES = {
    "anki": "ankidroid/Anki-Android",
    "wordpress": "wordpress-mobile/WordPress-Android",
    "ktlint": "pinterest/ktlint",
    "coroutines": "Kotlin/kotlinx.coroutines",
    "thunderbird": "thunderbird/thunderbird-android",
    "datetime": "Kotlin/kotlinx-datetime",
}

# Config name mapping (short name used in config/*.json files)
REPO_TO_CONFIG_NAME = {
    "ankidroid/Anki-Android": "anki",
    "wordpress-mobile/WordPress-Android": "wordpress",
    "pinterest/ktlint": "ktlint",
    "Kotlin/kotlinx.coroutines": "coroutines",
    "thunderbird/thunderbird-android": "thunderbird",
    "Kotlin/kotlinx-datetime": "datetime",
}

ALL_REPOS = list(REPO_TO_IMAGE.keys())

# Persistent volume for all eval data (logs + results)
eval_volume = modal.Volume.from_name("kotlin-bench-agent", create_if_missing=True)

# GitHub token secret
github_secret = modal.Secret.from_name("github-token")

# Lightweight image for utility functions (just needs constants.py)
util_image = (
    modal.Image.debian_slim(python_version="3.11")
    .add_local_dir(
        local_path=Path(__file__).parent,
        remote_path="/root/agent-bench",
    )
)

# =============================================================================
# Path Management
# =============================================================================

# Volume mount point and subdirectories
EVAL_VOLUME_PATH = "/eval"
RESULTS_BASE = EVAL_VOLUME_PATH  # Volume is already named kotlin-bench-agent

# Local output directory
LOCAL_OUTPUTS_DIR = Path(__file__).parent / "outputs"

# =============================================================================
# Timeout Configuration (all values in seconds)
# =============================================================================

# How long to wait for IntelliJ IDE to start and be ready for queries
SERVER_STARTUP_TIMEOUT = 900  # 10 minutes

# How long to wait for the agent to complete its code changes
AGENT_QUERY_TIMEOUT = 1800  # 30 minutes

# How long to wait for gradle tests to complete
TEST_EXECUTION_TIMEOUT = 1800  # 30 minutes

# Maximum time for entire eval task (agent + tests) on Modal
MODAL_TASK_TIMEOUT = 7200  # 2 hours

# Setup phase timeout (gradle wrapper, dependencies)
SETUP_TIMEOUT = 300  # 5 minutes

# Download/utility function timeout
DOWNLOAD_TIMEOUT = 300  # 5 minutes


def get_result_paths(instance_id: str, model: str, settings: "EvalSettings" = None) -> dict:
    """
    Get predictable paths for storing evaluation results.
    
    Structure:
        /eval/{model}/{instance_id}/{settings_id}/
        ├── agent_result.json      # Agent server response
        ├── agent_patch.diff       # Git diff (only if successful)
        ├── agent_log.json         # Conversation log (OpenAI chat completions format)
        ├── idea.log               # IntelliJ IDEA IDE log
        ├── test_result.json       # {passed: bool, error: str|null}
        └── test_output.log        # Full gradle test stdout/stderr
    
    Args:
        instance_id: Task instance ID
        model: Model identifier
        settings: Eval settings (affects path for different configurations)
    """
    if settings is None:
        settings = EvalSettings()
    
    settings_id = settings.to_path_segment()
    base = f"{RESULTS_BASE}/{model}/{instance_id}/{settings_id}"
    return {
        "base": base,
        "agent_result": f"{base}/agent_result.json",
        "agent_patch": f"{base}/agent_patch.diff",
        "agent_log": f"{base}/agent_log.json",
        "idea_log": f"{base}/idea.log",
        "test_result": f"{base}/test_result.json",
        "test_output": f"{base}/test_output.log",
        "settings": settings,  # Include settings for reference
    }


def get_volume_model_path(model: str) -> str:
    """Get the volume path for a model's results."""
    return f"{RESULTS_BASE}/{model}"


def is_agent_cached(paths: dict) -> bool:
    """
    Check if agent results are cached AND successful.
    
    Only returns True if:
    - agent_result.json exists
    - agent_patch.diff exists  
    - agent_result.json has success == True
    
    Errors are stored but don't count as cached (will be re-run).
    """
    if not os.path.exists(paths["agent_result"]):
        return False
    if not os.path.exists(paths["agent_patch"]):
        return False
    
    try:
        with open(paths["agent_result"]) as f:
            result = json.load(f)
        return result.get("success", False)
    except (json.JSONDecodeError, IOError):
        return False


def is_test_cached(paths: dict) -> bool:
    """
    Check if test results are cached AND passed.
    
    Only returns True if:
    - test_result.json exists
    - test_result.json has passed == True
    
    Failed tests don't count as cached (will be re-run).
    """
    if not os.path.exists(paths["test_result"]):
        return False
    
    try:
        with open(paths["test_result"]) as f:
            result = json.load(f)
        return result.get("passed", False)
    except (json.JSONDecodeError, IOError):
        return False


def load_cached_agent_result(paths: dict) -> Optional[dict]:
    """Load cached agent result from disk."""
    try:
        with open(paths["agent_result"]) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def load_cached_test_result(paths: dict) -> Optional[dict]:
    """Load cached test result from disk."""
    try:
        with open(paths["test_result"]) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


# =============================================================================
# Data Classes
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
    patch: Optional[str] = None  # Gold patch for validation
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


@dataclass
class EvalSettings:
    """
    Configuration flags that affect how the agent runs.
    
    These settings allow empirical comparison of different evaluation modes.
    """
    intellij_guidance: bool = True   # Include IntelliJ tool guidance in system prompt
    oracle_files: bool = False       # Provide relevant file hints from gold patch
    
    def to_dict(self) -> dict:
        return {
            "intellij_guidance": self.intellij_guidance,
            "oracle_files": self.oracle_files
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "EvalSettings":
        return cls(
            intellij_guidance=data.get("intellij_guidance", True),
            oracle_files=data.get("oracle_files", False)
        )
    
    def to_path_segment(self) -> str:
        """Generate a deterministic path segment for these settings."""
        return f"ij{int(self.intellij_guidance)}_oracle{int(self.oracle_files)}"


def generate_eval_prompt(task: "TaskInstance", settings: "EvalSettings" = None) -> str:
    """
    Generate the prompt for an evaluation task.
    
    This creates a well-structured prompt that includes the problem statement
    and any relevant context, but excludes information the agent shouldn't have
    (like the gold patch or test patch).
    
    Args:
        task: The task instance containing problem details
        settings: Eval settings (affects oracle file hints)
        
    Returns:
        Formatted prompt string for the agent
    """
    if settings is None:
        settings = EvalSettings()
    
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
    
    # Include hints if available (these are often valuable context from issue discussions)
    if task.hints_text and task.hints_text.strip():
        lines.append("## Additional Context from Issue Discussion")
        lines.append("")
        lines.append(task.hints_text.strip())
        lines.append("")
    
    # Oracle mode: provide file hints from gold patch
    if settings.oracle_files and task.patch:
        oracle_files = extract_files_from_patch(task.patch)
        if oracle_files:
            lines.append("## Relevant Files")
            lines.append("")
            lines.append("The following files are likely relevant to solving this issue:")
            for f in oracle_files:
                lines.append(f"- `{f}`")
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
    
    return "\n".join(lines)


@dataclass
class EvalResult:
    """Result of running an agentic evaluation."""
    instance_id: str
    model: str
    success: bool
    agent_response: Optional[dict] = None
    error: Optional[str] = None
    
    # Timing
    total_duration_seconds: float = 0.0
    setup_duration_seconds: float = 0.0
    server_startup_seconds: float = 0.0
    agent_query_seconds: float = 0.0
    
    # Metadata
    timestamps: Dict[str, str] = field(default_factory=dict)
    logs: str = ""
    log_file: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


# =============================================================================
# Dataset Loading
# =============================================================================

def load_tasks(repos: List[str] = None) -> List[TaskInstance]:
    """
    Load tasks from the Kotlin-bench dataset.
    
    Args:
        repos: List of repositories to filter for (e.g., ["ankidroid/Anki-Android"]).
               Can also be short names like ["anki", "ktlint"].
               If None or empty, loads ALL tasks.
    
    Returns:
        List of TaskInstance objects
    """
    dataset_path = Path(__file__).parent / "data" / "kotlin_bench.json"
    
    if not dataset_path.exists():
        print(f"Dataset not found at {dataset_path}")
        return []
    
    with open(dataset_path) as f:
        all_tasks = json.load(f)
    
    # Resolve short names to full repo names
    resolved_repos = None
    if repos:
        resolved_repos = [
            REPO_SHORT_NAMES.get(r, r) for r in repos
        ]
    
    # Filter tasks
    if resolved_repos:
        tasks = [
            TaskInstance.from_dict(t)
            for t in all_tasks
            if t.get("repo") in resolved_repos
        ]
        if len(resolved_repos) == 1:
            print(f"Loaded {len(tasks)} {resolved_repos[0]} tasks from dataset")
        else:
            print(f"Loaded {len(tasks)} tasks from {len(resolved_repos)} repos: {', '.join(resolved_repos)}")
    else:
        tasks = [TaskInstance.from_dict(t) for t in all_tasks]
        print(f"Loaded {len(tasks)} tasks from dataset (all repos)")
    
    return tasks


def get_task_by_id(task_id: str, repos: List[str] = None) -> Optional[TaskInstance]:
    """
    Get a specific task by instance_id.
    
    Args:
        task_id: The instance_id to find
        repos: Optional repo filter list (speeds up search)
    """
    tasks = load_tasks(repos)
    for task in tasks:
        if task.instance_id == task_id:
            return task
    return None


def get_repos_with_tasks() -> Dict[str, int]:
    """Get a dict of repo -> task count for all repos in the dataset."""
    dataset_path = Path(__file__).parent / "data" / "kotlin_bench.json"
    
    if not dataset_path.exists():
        return {}
    
    with open(dataset_path) as f:
        all_tasks = json.load(f)
    
    repo_counts = {}
    for t in all_tasks:
        repo = t.get("repo", "unknown")
        repo_counts[repo] = repo_counts.get(repo, 0) + 1
    
    return repo_counts


# =============================================================================
# Task Environment Setup
# =============================================================================

def reset_to_base_commit(project_path: str, base_commit: str) -> bool:
    """
    Reset the repository to the base commit for this task.
    
    The pre-baked image has Anki at a specific commit, but each task
    may need a different base commit.
    """
    print(f"  Resetting to base commit: {base_commit[:8]}...")
    
    try:
        # Clean any existing changes
        subprocess.run(
            ["git", "restore", "."],
            cwd=project_path,
            capture_output=True,
            check=False,
        )
        subprocess.run(
            ["git", "clean", "-fdx"],
            cwd=project_path,
            capture_output=True,
            check=False,
        )
        
        # Fetch the commit (in case it's not in shallow history)
        subprocess.run(
            ["git", "fetch", "--depth=1", "origin", base_commit],
            cwd=project_path,
            capture_output=True,
            check=False,
        )
        
        # Checkout the base commit
        result = subprocess.run(
            ["git", "-c", "advice.detachedHead=false", "checkout", base_commit],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            # Try force checkout
            result = subprocess.run(
                ["git", "-c", "advice.detachedHead=false", "checkout", "-f", base_commit],
                cwd=project_path,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(f"  Failed to checkout: {result.stderr}")
                return False
        
        print(f"  Successfully reset to {base_commit[:8]}")
        return True
        
    except Exception as e:
        print(f"  Error resetting to commit: {e}")
        return False


def setup_task_environment(
    task: "TaskInstance",
    project_path: str,
    env: dict,
) -> bool:
    """
    Configure the task environment.
    
    This sets up:
    - JDK version from MAP_VERSION_TO_INSTALL (uses SDKMAN path)
    - Android SDK environment variables
    - local.properties for Android builds
    - Runs repo-specific installation scripts (patches build files, etc.)
    """
    print("  Setting up task environment...")
    
    # Get installation specs for this repo/version
    specs = get_install_specs(task.repo, task.version)
    jdk_version = specs.get("jdk_version", "17.0.9-tem")
    install_script = specs.get("install", "")
    
    print(f"    JDK version: {jdk_version}")
    
    # Set JAVA_HOME from SDKMAN
    java_home = os.path.join(SDKMAN_JAVA_PATH, jdk_version)
    if os.path.exists(java_home):
        env["JAVA_HOME"] = java_home
        env["PATH"] = f"{java_home}/bin:{env.get('PATH', '')}"
        print(f"    JAVA_HOME: {java_home}")
    else:
        # Fallback to system Java 21
        fallback = "/usr/lib/jvm/java-21"
        if os.path.exists(fallback):
            env["JAVA_HOME"] = fallback
            env["PATH"] = f"{fallback}/bin:{env.get('PATH', '')}"
            print(f"    JAVA_HOME (fallback): {fallback}")
        else:
            print(f"    WARNING: JDK {jdk_version} not found at {java_home}")
    
    # Android SDK
    env["ANDROID_HOME"] = ANDROID_SDK_PATH
    env["PATH"] = f"{ANDROID_SDK_PATH}/platform-tools:{ANDROID_SDK_PATH}/cmdline-tools/latest/bin:{env.get('PATH', '')}"
    print(f"    ANDROID_HOME: {ANDROID_SDK_PATH}")
    
    # Create/update local.properties
    local_props = os.path.join(project_path, "local.properties")
    with open(local_props, "w") as f:
        f.write(f"sdk.dir={ANDROID_SDK_PATH}\n")
    print(f"    Created local.properties")
    
    # Ensure gradlew is executable
    gradlew = os.path.join(project_path, "gradlew")
    if os.path.exists(gradlew):
        subprocess.run(["chmod", "+x", gradlew], check=False)
    
    # Run installation script if provided
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
                print(f"    Installation script failed: {result.stderr[:500]}")
                # Don't fail - some scripts may have non-fatal errors
            else:
                print(f"    Installation script completed successfully")
        except subprocess.TimeoutExpired:
            print(f"    Installation script timed out")
        except Exception as e:
            print(f"    Installation script error: {e}")
    else:
        print(f"    No installation script needed")
    
    return True


def prepare_task_environment(
    task: "TaskInstance",
    project_path: str,
    env: dict,
) -> tuple[bool, str]:
    """
    Prepare the task environment: reset to base commit and configure.
    
    This combines reset_to_base_commit() and setup_task_environment() into
    a single call that should be done at the start of every evaluation.
    
    Args:
        task: Task instance
        project_path: Path to the project repository
        env: Environment variables dict (modified in place)
        
    Returns:
        (success: bool, error_message: str or None)
    """
    print("[Setup] Preparing task environment...")
    
    if not reset_to_base_commit(project_path, task.base_commit):
        return False, "Failed to reset to base commit"
    
    if not setup_task_environment(task, project_path, env):
        return False, "Failed to setup task environment"
    
    return True, None


def apply_patch_file(
    patch_content: str,
    project_path: str,
    patch_name: str = "patch",
) -> tuple[bool, str]:
    """
    Apply a patch to the repository.
    
    Generic function for applying any patch (agent, gold, test).
    
    Args:
        patch_content: The patch content as a string
        project_path: Path to the project repository
        patch_name: Name for logging purposes
        
    Returns:
        (success: bool, error_message: str or None)
    """
    if not patch_content:
        print(f"    No {patch_name} patch to apply, skipping")
        return True, None
    
    print(f"    Applying {patch_name} patch...")
    
    # Write patch to temporary file
    patch_path = f"/tmp/{patch_name}_{os.getpid()}.patch"
    with open(patch_path, "w") as f:
        f.write(patch_content)
    
    # Apply the patch
    result = subprocess.run(
        ["git", "apply", "--verbose", patch_path],
        cwd=project_path,
        capture_output=True,
        text=True,
    )
    
    # Clean up temp file
    try:
        os.remove(patch_path)
    except:
        pass
    
    if result.returncode != 0:
        error_msg = f"{patch_name} patch apply failed: {result.stderr or result.stdout}"
        print(f"    {error_msg}")
        return False, error_msg
    
    print(f"    {patch_name} patch applied successfully")
    return True, None


# =============================================================================
# Agent Server Management
# =============================================================================

def start_agent_server(
    project_path: str,
    env: dict,
    log_file: str,
    is_android: bool = False,
) -> subprocess.Popen:
    """
    Start the Firebender agent server using IntelliJ IDEA directly.
    
    Uses xvfb-run for headless operation and runs:
    idea.sh /project
    
    The Firebender plugin is pre-installed and configured via environment
    variables to start in agent server mode.
    
    Args:
        project_path: Path to the project directory
        env: Environment variables dict
        log_file: Path to write IDE logs
        is_android: If True, use Android's GradleSyncState for sync detection
    """
    print("  Starting IDE with Firebender plugin...")
    
    # Set agent server environment (both as env vars and JVM properties for reliability)
    env["FIREBENDER_AGENT_SERVER"] = "true"
    env["FIREBENDER_AGENT_SERVER_PORT"] = str(AGENT_PORT)
    env["FIREBENDER_ANDROID_PROJECT"] = "true" if is_android else "false"
    env["DISPLAY"] = ":99"
    
    # JVM options for headless IntelliJ
    # IMPORTANT: Include firebender.agentServer as JVM property because env vars
    # may not propagate correctly through idea.sh to the JVM process.
    # The AgentServer.isEnabled() checks System.getProperty() as fallback.
    env["_JAVA_OPTIONS"] = " ".join([
        "-Dfirebender.agentServer=true",
        f"-Dfirebender.agentServerPort={AGENT_PORT}",
        f"-Dfirebender.androidProject={'true' if is_android else 'false'}",
        "-Djb.consents.confirmation.enabled=false",
        '-Djb.privacy.policy.text="<!--999.999-->"',
        "-Didea.initially.ask.config=false",
        "-Dide.no.splash=true",
        "-Dnosplash=true",
        "-Dhidpi=false",
        "-Dsun.java2d.uiScale.enabled=false",
        "-Dsun.java2d.uiScale=1.0",
        "-Dide.ui.scale=1.0",
        "-Dsun.java2d.xrender=false",
    ])
    
    # Command to start IDE with project
    # Use 'env' to explicitly pass the environment variables to ensure they reach the JVM
    cmd = [
        "xvfb-run", "-a",
        "-s", "-screen 0 1920x1080x24",
        "env",
        f"FIREBENDER_AGENT_SERVER=true",
        f"FIREBENDER_AGENT_SERVER_PORT={AGENT_PORT}",
        f"FIREBENDER_ANDROID_PROJECT={'true' if is_android else 'false'}",
        "/opt/idea/bin/idea.sh",
        project_path,
    ]
    
    print(f"    Command: {' '.join(cmd)}")
    print(f"    Log file: {log_file}")
    print(f"    FIREBENDER_AGENT_SERVER={env['FIREBENDER_AGENT_SERVER']}")
    print(f"    FIREBENDER_AGENT_SERVER_PORT={env['FIREBENDER_AGENT_SERVER_PORT']}")
    print(f"    FIREBENDER_ANDROID_PROJECT={env['FIREBENDER_ANDROID_PROJECT']}")
    
    # Open log file
    log_handle = open(log_file, "w")
    
    # Start process
    process = subprocess.Popen(
        cmd,
        cwd=project_path,
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    
    return process


def wait_for_server_ready(
    port: int = AGENT_PORT,
    poll_interval: int = 5,
) -> dict:
    """
    Poll the /ready endpoint until server is ready or timeout.
    
    Uses SERVER_STARTUP_TIMEOUT constant for timeout.
    
    Returns:
        dict with success, timing info, and final response
    """
    import urllib.request
    import urllib.error
    
    print(f"  Waiting for server to be ready (timeout: {SERVER_STARTUP_TIMEOUT}s, poll_interval: {poll_interval}s)...")
    print(f"    Polling http://localhost:{port}/ready")
    
    start_time = time.time()
    last_message = ""
    indexing_complete_time = None
    gradle_sync_complete_time = None
    last_response = None
    poll_count = 0
    last_log_time = 0
    
    while time.time() - start_time < SERVER_STARTUP_TIMEOUT:
        elapsed = time.time() - start_time
        poll_count += 1
        
        try:
            req = urllib.request.Request(f"http://localhost:{port}/ready")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                last_response = data
                
                print(f"    [+{elapsed:.0f}s] /ready response: {data}", flush=True)
                
                # Track completion times
                if data.get("indexing", {}).get("complete") and indexing_complete_time is None:
                    indexing_complete_time = elapsed
                    print(f"    [+{elapsed:.0f}s] Indexing complete", flush=True)
                
                if data.get("gradleSync", {}).get("complete") and gradle_sync_complete_time is None:
                    gradle_sync_complete_time = elapsed
                    print(f"    [+{elapsed:.0f}s] Gradle sync complete", flush=True)
                
                # Check the server's ready flag (combines indexing AND Gradle sync status)
                is_ready = data.get("ready", False)
                if is_ready:
                    print(f"    [+{elapsed:.0f}s] Server reports ready (indexing + Gradle sync complete)!", flush=True)
                    return {
                        "success": True,
                        "total_time": elapsed,
                        "indexing_time": indexing_complete_time,
                        "gradle_sync_time": gradle_sync_complete_time,
                        "response": data,
                    }
                
                # Log status changes
                message = data.get("message", "")
                if message != last_message:
                    print(f"    [+{elapsed:.0f}s] Status: {message}", flush=True)
                    last_message = message
                    
        except urllib.error.HTTPError as e:
            print(f"    [+{elapsed:.0f}s] HTTP Error: {e.code} {e.reason}", flush=True)
                    
        except (urllib.error.URLError, ConnectionRefusedError) as conn_err:
            if elapsed - last_log_time >= 10 or poll_count <= 2:
                print(f"    [+{elapsed:.0f}s] Connection refused/error: {conn_err}", flush=True)
                
        except Exception as e:
            print(f"    [+{elapsed:.0f}s] Unexpected error: {type(e).__name__}: {e}", flush=True)
        
        time.sleep(poll_interval)
    
    return {
        "success": False,
        "total_time": time.time() - start_time,
        "indexing_time": indexing_complete_time,
        "gradle_sync_time": gradle_sync_complete_time,
        "response": last_response,
        "error": f"Timeout after {SERVER_STARTUP_TIMEOUT}s",
    }


def send_agent_request(
    query: str,
    model: str,
    port: int = AGENT_PORT,
    include_intellij_guidance: bool = True,
) -> dict:
    """
    Send a query to the agent server.
    
    Uses AGENT_QUERY_TIMEOUT constant for timeout.
    
    Args:
        query: The problem statement / task description
        model: The model to use for the agent (e.g., claude-sonnet-4-20250514)
        port: Agent server port
        include_intellij_guidance: Whether to include IntelliJ tool guidance (default True)
        
    Returns:
        Agent response dict or error dict
    """
    import urllib.request
    import urllib.error
    
    url = f"http://localhost:{port}/agent/run"
    data = json.dumps({
        "query": query,
        "model": model,
        "includeIntellijGuidance": include_intellij_guidance,
    }).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    
    try:
        with urllib.request.urlopen(req, timeout=AGENT_QUERY_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"error": f"Connection error: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# Firebender Plugin Installation (Runtime)
# =============================================================================

def install_firebender_plugin(log_func=print) -> bool:
    """
    Install the Firebender plugin at runtime before starting the IDE.
    
    The plugin zip is expected at /tmp/Firebender.zip (added to image via Modal).
    It will be extracted to the IntelliJ plugins directory.
    
    Args:
        log_func: Function to use for logging (default: print)
        
    Returns:
        True if installation succeeded, False otherwise
    """
    plugin_zip = "/tmp/Firebender.zip"
    plugins_dir = IDEA_PLUGINS_DIR
    
    log_func(f"  Installing Firebender plugin...")
    log_func(f"    Source: {plugin_zip}")
    log_func(f"    Target: {plugins_dir}")
    
    # Check if plugin zip exists
    if not os.path.exists(plugin_zip):
        log_func(f"    ERROR: Plugin zip not found at {plugin_zip}")
        return False
    
    # Check plugin zip size
    zip_size = os.path.getsize(plugin_zip)
    log_func(f"    Plugin zip size: {zip_size / 1024 / 1024:.1f} MB")
    
    # List contents of the zip to see what we're extracting
    try:
        list_result = subprocess.run(
            ["unzip", "-l", plugin_zip],
            capture_output=True,
            text=True,
        )
        log_func(f"    Zip contents preview:")
        for line in list_result.stdout.split('\n')[:10]:
            log_func(f"      {line}")
    except Exception as e:
        log_func(f"    Could not list zip contents: {e}")
    
    # Ensure plugins directory exists
    os.makedirs(plugins_dir, exist_ok=True)
    
    # Show existing plugins BEFORE installation
    log_func(f"    Plugins dir BEFORE install:")
    try:
        for item in os.listdir(plugins_dir):
            item_path = os.path.join(plugins_dir, item)
            if os.path.isdir(item_path):
                log_func(f"      [DIR]  {item}")
            else:
                log_func(f"      [FILE] {item}")
    except Exception as e:
        log_func(f"      Error listing: {e}")
    
    # Extract the plugin
    try:
        result = subprocess.run(
            ["unzip", "-o", plugin_zip, "-d", plugins_dir],
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            log_func(f"    ERROR: unzip failed: {result.stderr}")
            return False
        
        log_func(f"    Plugin extracted successfully")
        log_func(f"    unzip output: {result.stdout[:500] if result.stdout else '(none)'}")
        
    except Exception as e:
        log_func(f"    ERROR: Exception during unzip: {e}")
        return False
    
    # Show plugins AFTER installation
    log_func(f"    Plugins dir AFTER install:")
    plugins = []
    try:
        for item in os.listdir(plugins_dir):
            item_path = os.path.join(plugins_dir, item)
            if os.path.isdir(item_path):
                log_func(f"      [DIR]  {item}")
                plugins.append(item)
                # Check for lib/ subfolder (typical plugin structure)
                lib_path = os.path.join(item_path, "lib")
                if os.path.isdir(lib_path):
                    jars = os.listdir(lib_path)[:5]
                    log_func(f"              lib/ contains: {jars}...")
            else:
                log_func(f"      [FILE] {item}")
    except Exception as e:
        log_func(f"      Error listing: {e}")
    
    # Verify Firebender is there
    firebender_found = any("Firebender" in p or "firebender" in p for p in plugins)
    if firebender_found:
        log_func(f"    Firebender plugin verified in plugins directory!")
        return True
    else:
        log_func(f"    WARNING: Firebender not found in plugins directory after extraction")
        log_func(f"    Available plugins: {plugins}")
        return False


# =============================================================================
# Agent Result Capture
# =============================================================================

# Agent output files (written by agent in IDE)
AGENT_CONVERSATION_LOG = "/tmp/agent_log.json"  # OpenAI chat completions format
AGENT_IDE_LOG = "/tmp/idea.log"  # IntelliJ IDEA log


def capture_agent_patch(project_path: str, paths: dict) -> bool:
    """
    Capture the git diff of changes made by the agent.
    
    After the agent completes, this generates a diff of all modifications
    and saves it to the results volume along with the eval log.
    
    Also captures:
    - agent_log.json: Agent conversation log (OpenAI chat completions format)
    - idea.log: IntelliJ IDEA IDE log for the session
    
    Args:
        project_path: Path to the project repository
        paths: Result paths from get_result_paths()
        
    Returns:
        True if capture succeeded, False otherwise
    """
    try:
        import shutil
        
        # Create results directory
        os.makedirs(paths["base"], exist_ok=True)
        
        # Generate git diff of all changes (staged and unstaged)
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        
        patch_content = result.stdout
        
        # Also check for untracked files and add them to the patch
        untracked_result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        
        untracked_files = untracked_result.stdout.strip().split("\n") if untracked_result.stdout.strip() else []
        
        # For untracked files, generate a diff showing them as new files
        for filepath in untracked_files:
            if not filepath:
                continue
            try:
                file_path = os.path.join(project_path, filepath)
                if os.path.isfile(file_path):
                    with open(file_path, "r") as f:
                        content = f.read()
                    lines = content.split("\n")
                    patch_content += f"\ndiff --git a/{filepath} b/{filepath}\n"
                    patch_content += "new file mode 100644\n"
                    patch_content += f"--- /dev/null\n"
                    patch_content += f"+++ b/{filepath}\n"
                    patch_content += f"@@ -0,0 +1,{len(lines)} @@\n"
                    for line in lines:
                        patch_content += f"+{line}\n"
            except Exception as e:
                print(f"    Warning: Could not add untracked file {filepath}: {e}")
        
        # Write patch to results volume
        with open(paths["agent_patch"], "w") as f:
            f.write(patch_content)
        
        print(f"    Captured agent patch ({len(patch_content)} bytes)")
        
        # Copy agent conversation log (OpenAI chat completions format)
        if os.path.exists(AGENT_CONVERSATION_LOG):
            dest_path = f"{paths['base']}/agent_log.json"
            shutil.copy(AGENT_CONVERSATION_LOG, dest_path)
            file_size = os.path.getsize(AGENT_CONVERSATION_LOG)
            print(f"    Copied agent conversation log ({file_size} bytes) to {dest_path}")
        else:
            print(f"    Warning: Agent conversation log not found at {AGENT_CONVERSATION_LOG}")
        
        # Copy IDE log (idea.log)
        if os.path.exists(AGENT_IDE_LOG):
            dest_path = f"{paths['base']}/idea.log"
            shutil.copy(AGENT_IDE_LOG, dest_path)
            file_size = os.path.getsize(AGENT_IDE_LOG)
            print(f"    Copied IDE log ({file_size} bytes) to {dest_path}")
        else:
            print(f"    Warning: IDE log not found at {AGENT_IDE_LOG}")
        
        return True
        
    except Exception as e:
        print(f"    Error capturing agent patch: {e}")
        return False


def find_and_save_idea_log(paths: dict):
    """
    Find and save IntelliJ's idea.log to the results directory.
    
    Searches common locations for the idea.log file and copies it
    to the results directory for debugging.
    """
    import shutil
    import glob
    
    # Possible locations for idea.log
    idea_log_locations = [
        "/tmp/idea.log",  # Copied by AgentServer
        "/root/.cache/JetBrains/IdeaIC2025.1/log/idea.log",
        "/root/.cache/JetBrains/IdeaIC*/log/idea.log",  # Glob pattern
        f"{IDEA_PLUGINS_DIR}/../log/idea.log",  # Relative to plugins
    ]
    
    for pattern in idea_log_locations:
        # Handle glob patterns
        if '*' in pattern:
            matches = glob.glob(pattern)
            if matches:
                pattern = matches[0]
            else:
                continue
        
        if os.path.exists(pattern):
            try:
                dest_path = f"{paths['base']}/idea.log"
                shutil.copy(pattern, dest_path)
                file_size = os.path.getsize(pattern)
                print(f"    Saved idea.log ({file_size} bytes) from {pattern}")
                return True
            except Exception as e:
                print(f"    Failed to copy idea.log from {pattern}: {e}")
    
    print(f"    Warning: Could not find idea.log in any known location")
    return False


def save_agent_error(paths: dict, error: str, agent_response: Optional[dict] = None):
    """
    Save an error result for the agent phase.
    
    This stores the error but does NOT create agent_patch.diff,
    so is_agent_cached() will return False and the task will be re-run.
    Also attempts to save idea.log for debugging.
    """
    try:
        os.makedirs(paths["base"], exist_ok=True)
        
        error_result = {
            "success": False,
            "error": error,
            "agent_response": agent_response,
            "timestamp": datetime.now().isoformat(),
        }
        
        with open(paths["agent_result"], "w") as f:
            json.dump(error_result, f, indent=2)
            
        print(f"    Saved agent error to {paths['agent_result']}")
        
        # Also try to save idea.log for debugging
        find_and_save_idea_log(paths)
        
        # Try to save agent conversation log if it exists
        if os.path.exists(AGENT_CONVERSATION_LOG):
            import shutil
            dest_path = f"{paths['base']}/agent_log.json"
            shutil.copy(AGENT_CONVERSATION_LOG, dest_path)
            print(f"    Saved agent_log.json for debugging")
        
    except Exception as e:
        print(f"    Failed to save agent error: {e}")


# =============================================================================
# Test Phase
# =============================================================================

def extract_files_from_patch(patch_content: str) -> list:
    """
    Extract all file paths from a git diff patch.
    
    Args:
        patch_content: Git diff patch content
        
    Returns:
        List of file paths modified by the patch
    """
    import re
    
    if not patch_content:
        return []
    
    # Match "diff --git a/path b/path" format
    diff_pat = r"diff --git a/.* b/(.*)"
    files = re.findall(diff_pat, patch_content)
    
    return files


def reset_files_to_base_commit(files: list, base_commit: str, project_path: str) -> tuple:
    """
    Reset specific files to their state at the base commit.
    
    This is used to reset test files that may have been modified by the agent
    before applying the gold test patch.
    
    Args:
        files: List of file paths to reset
        base_commit: Git commit hash to reset files to
        project_path: Path to the git repository
        
    Returns:
        Tuple of (success: bool, error_message: str or None)
    """
    if not files:
        return True, None
    
    reset_count = 0
    errors = []
    
    for filepath in files:
        try:
            result = subprocess.run(
                ["git", "checkout", base_commit, "--", filepath],
                cwd=project_path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                reset_count += 1
            else:
                # File might not exist at base commit (new file in test patch)
                # This is okay - the patch will create it
                pass
        except Exception as e:
            errors.append(f"{filepath}: {e}")
    
    if reset_count > 0:
        print(f"    Reset {reset_count} test file(s) to base commit for clean patch application")
    
    if errors:
        return False, f"Failed to reset some files: {'; '.join(errors)}"
    
    return True, None


def run_test_phase(
    task: "TaskInstance",
    paths: dict,
    env: dict,
) -> dict:
    """
    Run the test phase: apply test patch and execute tests.
    
    Uses TEST_EXECUTION_TIMEOUT constant for timeout.
    
    Assumes the environment is already prepared (reset + setup done)
    and any code patches (gold/agent/cached) have been applied.
    
    Steps:
    1. Reset test files to base commit (in case agent modified them)
    2. Apply test_patch from task instance
    3. Run tests
    
    Args:
        task: Task instance with repo info and test_patch
        paths: Result paths from get_result_paths()
        env: Environment variables
        
    Returns:
        {passed: bool, error: str|null, duration_seconds: float}
    """
    start_time = time.time()
    
    # Step 1: Reset test files that may have been modified by the agent
    # This ensures we can cleanly apply the gold test patch
    print("  Resetting test files to base commit...")
    test_files = extract_files_from_patch(task.test_patch)
    if test_files:
        print(f"    Test patch modifies: {test_files}")
        success, error = reset_files_to_base_commit(test_files, task.base_commit, PROJECT_PATH)
        if not success:
            print(f"    Warning: {error}")
            # Continue anyway - the patch apply will fail if there's a real problem
    
    # Step 2: Apply test patch
    print("  Applying test patch...")
    success, error = apply_patch_file(task.test_patch, PROJECT_PATH, "test")
    if not success:
        return {
            "passed": False,
            "error": f"test patch apply failed: {error}",
            "duration_seconds": time.time() - start_time,
        }
    
    # Step 2: Run tests
    print("  Running tests...")
    
    # Generate test command dynamically based on test_patch (like legacy implementation)
    # This extracts test class names from test_patch and creates --tests filters
    task_dict = task.to_dict()
    test_directives = get_test_directives(task_dict)
    test_cmd = get_test_cmd_from_instance(task_dict)
    
    print(f"    Test directives: {test_directives}")
    print(f"    Command: {test_cmd}")
    
    # =========================================================================
    # Test Environment Setup (mirrors context_manager_modal.py run_tests_task)
    # =========================================================================
    
    # Set additional JVM arguments to fix ByteBuddy/Mockito issues
    mockito_fix = "-Dmockito.mock.maker=org.mockito.internal.creation.bytebuddy.SubclassByteBuddyMockMaker -Djdk.attach.allowAttachSelf=true -Dnet.bytebuddy.experimental=true"
    current_java_opts = env.get("JAVA_TOOL_OPTIONS", "")
    if "mockito.mock.maker" not in current_java_opts:
        env["JAVA_TOOL_OPTIONS"] = f"{current_java_opts} {mockito_fix}".strip()
        print(f"    Added Mockito fix to JAVA_TOOL_OPTIONS")
    
    # Set Android SDK environment variables
    print(f"    Setting Android environment variables: ANDROID_HOME={ANDROID_SDK_PATH}")
    env["ANDROID_HOME"] = ANDROID_SDK_PATH
    
    # Update PATH to include Android tools
    env["PATH"] = (
        f"{ANDROID_SDK_PATH}/platform-tools:{ANDROID_SDK_PATH}/cmdline-tools/latest/bin:"
        f"{env.get('PATH', '')}"
    )
    
    # Double-check local.properties exists before running tests
    local_properties_path = os.path.join(PROJECT_PATH, "local.properties")
    if not os.path.exists(local_properties_path):
        print(f"    Creating local.properties with sdk.dir={ANDROID_SDK_PATH}")
        with open(local_properties_path, "w") as f:
            f.write(f"sdk.dir={ANDROID_SDK_PATH}\n")
    
    # Add Mockito fix to gradle.properties
    gradle_properties_path = os.path.join(PROJECT_PATH, "gradle.properties")
    mockito_gradle_fix = "org.gradle.jvmargs=-Dmockito.mock.maker=org.mockito.internal.creation.bytebuddy.SubclassByteBuddyMockMaker -Djdk.attach.allowAttachSelf=true -Dnet.bytebuddy.experimental=true"
    
    if os.path.exists(gradle_properties_path):
        print("    Updating gradle.properties with Mockito fix...")
        with open(gradle_properties_path, "r") as f:
            lines = f.readlines()
        
        # Check if org.gradle.jvmargs is already defined
        jvmargs_found = False
        for i, line in enumerate(lines):
            if line.startswith("org.gradle.jvmargs="):
                if "mockito.mock.maker" not in line:
                    # Append Mockito fix to existing jvmargs
                    lines[i] = line.strip() + " -Dmockito.mock.maker=org.mockito.internal.creation.bytebuddy.SubclassByteBuddyMockMaker -Djdk.attach.allowAttachSelf=true -Dnet.bytebuddy.experimental=true\n"
                jvmargs_found = True
                break
        
        # Add jvmargs if not found
        if not jvmargs_found:
            lines.append(f"{mockito_gradle_fix}\n")
        
        # Write updated content
        with open(gradle_properties_path, "w") as f:
            f.writelines(lines)
    else:
        # Create new gradle.properties file
        print("    Creating gradle.properties with Mockito fix...")
        with open(gradle_properties_path, "w") as f:
            f.write(f"{mockito_gradle_fix}\n")
    
    # Ensure output directory exists
    os.makedirs(paths["base"], exist_ok=True)
    
    try:
        with open(paths["test_output"], "w") as log_file:
            # Write header
            log_file.write(f"Test Command: {test_cmd}\n")
            log_file.write(f"Task: {task.instance_id}\n")
            log_file.write(f"Base Commit: {task.base_commit}\n")
            log_file.write(f"Timestamp: {datetime.now().isoformat()}\n")
            log_file.write("=" * 60 + "\n\n")
            log_file.flush()
            
            # Run test command
            result = subprocess.run(
                test_cmd,
                shell=True,
                cwd=PROJECT_PATH,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=TEST_EXECUTION_TIMEOUT,
            )
            
            # Write output
            log_file.write(result.stdout or "")
            log_file.write("\n" + "=" * 60 + "\n")
            
            # Write pass/fail marker (like context_manager.py)
            if result.returncode == 0:
                log_file.write(">>>>> All Tests Passed\n")
                print("    Tests PASSED")
            else:
                log_file.write(">>>>> Some Tests Failed\n")
                print("    Tests FAILED")
        
        duration = time.time() - start_time
        
        return {
            "passed": result.returncode == 0,
            "error": None if result.returncode == 0 else "Tests failed (see test_output.log)",
            "duration_seconds": duration,
            "return_code": result.returncode,
        }
        
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        
        with open(paths["test_output"], "a") as log_file:
            log_file.write(f"\n>>>>> Tests Timed Out after {TEST_EXECUTION_TIMEOUT} seconds\n")
        
        print(f"    Tests TIMED OUT after {TEST_EXECUTION_TIMEOUT}s")
        
        return {
            "passed": False,
            "error": f"Tests timed out after {TEST_EXECUTION_TIMEOUT} seconds",
            "duration_seconds": duration,
        }
        
    except Exception as e:
        duration = time.time() - start_time
        
        with open(paths["test_output"], "a") as log_file:
            log_file.write(f"\n>>>>> Tests Error: {e}\n")
        
        print(f"    Tests ERROR: {e}")
        
        return {
            "passed": False,
            "error": str(e),
            "duration_seconds": duration,
        }


def save_test_result(paths: dict, result: dict):
    """Save test result to the results volume."""
    try:
        os.makedirs(paths["base"], exist_ok=True)
        
        result["timestamp"] = datetime.now().isoformat()
        
        with open(paths["test_result"], "w") as f:
            json.dump(result, f, indent=2)
            
        print(f"    Saved test result to {paths['test_result']}")
        
    except Exception as e:
        print(f"    Failed to save test result: {e}")

# =============================================================================
# Main Evaluation Function
# =============================================================================

def _run_eval_task_impl(
    task_dict: dict,
    model: str,
    patch_source: str = None,
    use_agent_cache: bool = True,
    use_test_cache: bool = True,
    include_intellij_guidance: bool = True,
    oracle_files: bool = False,
) -> dict:
    """
    Shared implementation for running an agentic evaluation.
    
    This is the core logic that all repo-specific eval functions use.
    It's defined as a regular function so it can be called from Modal functions
    with different images.
    
    Timeouts are controlled by module-level constants:
    - SERVER_STARTUP_TIMEOUT: Max seconds to wait for server ready
    - AGENT_QUERY_TIMEOUT: Max seconds for agent query
    - TEST_EXECUTION_TIMEOUT: Max seconds for test execution
    
    Pipeline:
    1. Prepare environment (reset to base commit + setup)
    2. Apply code changes based on patch_source
    3. Apply test patch and run tests
    
    Args:
        task_dict: Task instance as dictionary
        model: Model identifier
        patch_source: Where to get the code patch from:
            - None (default): Run agent (or use cache if available)
            - "gold": Use the gold/correct patch from task instance
            - "none": No code changes (baseline - tests should fail)
        use_agent_cache: If True and patch_source=None, use cached agent results
        use_test_cache: If True, use cached test results if available
        include_intellij_guidance: Whether to include IntelliJ tool guidance (default True)
        oracle_files: Whether to provide file hints from gold patch (default False)
        
    Returns:
        Evaluation result dict
    """
    task = TaskInstance.from_dict(task_dict)
    start_time = time.time()
    
    # Build settings from parameters
    settings = EvalSettings(
        intellij_guidance=include_intellij_guidance,
        oracle_files=oracle_files
    )
    
    timestamps = {"start": datetime.now().isoformat()}
    
    def log(msg: str):
        print(msg, flush=True)
    
    log("=" * 60)
    log(f"Running Eval: {task.instance_id}")
    log("=" * 60)
    log(f"  Repo: {task.repo}")
    log(f"  Version: {task.version}")
    log(f"  Base Commit: {task.base_commit[:8]}")
    log(f"  Model: {model}")
    log(f"  Patch Source: {patch_source or 'agent'}")
    log(f"  Use Agent Cache: {use_agent_cache}")
    log(f"  Use Test Cache: {use_test_cache}")
    log(f"  Settings: {settings.to_dict()}")
    
    # Get result paths for caching (includes settings in path)
    paths = get_result_paths(task.instance_id, model, settings)
    os.makedirs(paths["base"], exist_ok=True)
    log(f"  Results path: {paths['base']}")
    
    # Environment setup
    env = os.environ.copy()
    
    # Initialize result tracking
    agent_success = False
    agent_cached = False
    agent_response = None
    agent_duration = 0.0
    server_startup_duration = 0.0
    server_was_ready = True  # Default to True (cached/oracle paths don't need server)
    setup_duration = 0.0
    
    # =========================================================================
    # SETUP PHASE - Always prepare environment first
    # =========================================================================
    
    log("\n[Setup] Preparing task environment...")
    setup_start = time.time()
    
    success, error = prepare_task_environment(task, PROJECT_PATH, env)
    if not success:
        eval_volume.commit()
        return {
            "instance_id": task.instance_id,
            "model": model,
            "patch_source": patch_source,
            "agent_success": False,
            "error": error,
            "test_passed": None,
        }
    
    setup_duration = time.time() - setup_start
    timestamps["setup_complete"] = datetime.now().isoformat()
    log(f"  Setup completed in {setup_duration:.1f}s")
    
    # =========================================================================
    # PATCH PHASE - Get code changes from the appropriate source
    # =========================================================================
    
    if patch_source == "gold":
        # Use gold patch from task instance
        log("\n[Patch] Applying gold patch...")
        
        if not task.patch:
            eval_volume.commit()
            return {
                "instance_id": task.instance_id,
                "model": model,
                "patch_source": patch_source,
                "agent_success": False,
                "error": "No gold patch available in task instance",
                "test_passed": None,
            }
        
        success, error = apply_patch_file(task.patch, PROJECT_PATH, "gold")
        if not success:
            eval_volume.commit()
            return {
                "instance_id": task.instance_id,
                "model": model,
                "patch_source": patch_source,
                "agent_success": False,
                "error": error,
                "test_passed": None,
            }
        
        agent_success = True  # Gold patch counts as "agent success" for reporting
        log("  Gold patch applied successfully")
        
    elif patch_source == "none":
        # No code changes - baseline test (should fail)
        log("\n[Patch] No code changes (baseline mode)")
        agent_success = True  # No patch needed counts as success
        
    elif use_agent_cache and is_agent_cached(paths):
        # Use cached agent results
        log("\n[Patch] Using cached agent patch...")
        agent_cached = True
        
        cached_result = load_cached_agent_result(paths)
        if cached_result:
            agent_response = cached_result.get("agent_response")
        
        # Read and apply cached patch
        if os.path.exists(paths["agent_patch"]):
            with open(paths["agent_patch"], "r") as f:
                cached_patch = f.read()
            
            if cached_patch.strip():  # Only apply if not empty
                success, error = apply_patch_file(cached_patch, PROJECT_PATH, "cached agent")
                if not success:
                    eval_volume.commit()
                    return {
                        "instance_id": task.instance_id,
                        "model": model,
                        "patch_source": "cache",
                        "agent_success": False,
                        "agent_cached": True,
                        "error": error,
                        "test_passed": None,
                    }
        
        agent_success = True
        log("  Cached agent patch applied")
        
    else:
        # Run actual agent
        log("\n[Agent] Installing Firebender plugin and starting IDE...")
        
        # Invalidate test cache when re-running agent - tests must be re-run
        # with fresh agent output to get accurate results
        for test_file in ["test_result", "test_output"]:
            test_path = paths.get(test_file)
            if test_path and os.path.exists(test_path):
                try:
                    os.remove(test_path)
                    log(f"  Invalidated test cache: {test_file}")
                except Exception as e:
                    log(f"  Warning: Could not delete {test_file}: {e}")
        
        # Install Firebender plugin at runtime (not baked into image)
        if not install_firebender_plugin(log_func=log):
            error_msg = "Failed to install Firebender plugin"
            log(f"    ERROR: {error_msg}")
            save_agent_error(paths, error_msg)
            eval_volume.commit()
            return {
                "instance_id": task.instance_id,
                "model": model,
                "patch_source": "agent",
                "agent_success": False,
                "error": error_msg,
                "test_passed": None,
            }
        
        agent_log_file = f"/tmp/agent_server_{task.instance_id}.log"
        
        # Start agent server (IDE with Firebender plugin)
        log("  Starting IntelliJ IDEA with Firebender plugin...")
        server_start = time.time()
        
        # Determine if this is an Android project (uses different sync detection)
        is_android = is_android_project(task.repo)
        log(f"    Android project: {is_android}")
        
        agent_process = start_agent_server(PROJECT_PATH, env, agent_log_file, is_android=is_android)
        timestamps["server_started"] = datetime.now().isoformat()
        log(f"    IDE process PID: {agent_process.pid}")
        
        # Give the process a moment to start and check if it crashed immediately
        time.sleep(2)
        if agent_process.poll() is not None:
            log(f"    WARNING: IDE process exited immediately with code: {agent_process.poll()}")
            # Try to read the log file for errors
            try:
                with open(agent_log_file, 'r') as f:
                    log_content = f.read()
                log(f"    IDE log (first 2000 chars):\n{log_content[:2000]}")
            except Exception as e:
                log(f"    Could not read IDE log: {e}")
        
        # Wait for server ready
        log("  Waiting for server to be ready...")
        ready_result = wait_for_server_ready(
            port=AGENT_PORT,
        )
        
        server_startup_duration = time.time() - server_start
        timestamps["server_ready"] = datetime.now().isoformat()
        
        # Track if server was ready (but continue either way)
        server_was_ready = ready_result["success"]
        
        if not server_was_ready:
            log(f"    WARNING: Server did not report ready within timeout. Proceeding with agent request anyway...")
            log(f"    Last server state: {ready_result.get('response', {})}")
            
            # Log some analysis but don't abort
            try:
                with open(agent_log_file, 'r') as f:
                    log_content = f.read()
                log(f"    === IDE Log Analysis (server not ready) ===")
                patterns = [
                    ("AgentServer", "Agent server mentions"),
                    ("GradleSync", "Gradle sync mentions"),
                    ("ERROR", "Errors"),
                ]
                for pattern, desc in patterns:
                    matches = [line for line in log_content.split('\n') if pattern in line]
                    if matches:
                        log(f"    {desc} ({len(matches)} matches, showing last 3):")
                        for m in matches[-3:]:
                            log(f"      {m[:200]}")
            except Exception as e:
                log(f"    Could not read IDE log: {e}")
        else:
            log(f"  Server ready in {server_startup_duration:.1f}s")
        
        # Send agent request
        log("  Sending agent request...")
        eval_prompt = generate_eval_prompt(task, settings)
        log(f"    Prompt preview: {eval_prompt[:300]}...")

        query_start = time.time()
        agent_response = send_agent_request(
            query=eval_prompt,
            model=model,
            port=AGENT_PORT,
            include_intellij_guidance=include_intellij_guidance,
        )
        agent_duration = time.time() - query_start
        timestamps["query_complete"] = datetime.now().isoformat()
        
        log(f"  Agent responded in {agent_duration:.1f}s")
        
        # Cleanup agent process
        agent_process.terminate()
        try:
            agent_process.wait(timeout=10)
        except:
            agent_process.kill()
        
        # Check if agent request succeeded
        if "error" in agent_response:
            error_msg = agent_response.get("error", "Agent request failed")
            log(f"  Agent ERROR: {error_msg}")
            save_agent_error(paths, error_msg, agent_response)
            eval_volume.commit()
            
            return {
                "instance_id": task.instance_id,
                "model": model,
                "patch_source": "agent",
                "agent_success": False,
                "error": error_msg,
                "agent_response": agent_response,
                "test_passed": None,
                "agent_query_seconds": agent_duration,
            }
        
        # Capture the patch
        log("  Capturing agent changes...")
        if not capture_agent_patch(PROJECT_PATH, paths):
            save_agent_error(paths, "Failed to capture agent patch", agent_response)
            eval_volume.commit()
            
            return {
                "instance_id": task.instance_id,
                "model": model,
                "patch_source": "agent",
                "agent_success": False,
                "error": "Failed to capture agent patch",
                "agent_response": agent_response,
                "test_passed": None,
            }
        
        agent_success = True
        log("  Agent phase complete!")
    
    # =========================================================================
    # TEST PHASE - Apply test patch and run tests
    # =========================================================================
    
    test_result = None
    test_cached = False
    
    if use_test_cache and is_test_cached(paths):
        log("\n[Test] Using cached test results (passed=True)")
        test_cached = True
        test_result = load_cached_test_result(paths)
    else:
        log("\n[Test] Running tests...")
        
        test_result = run_test_phase(
            task=task,
            paths=paths,
            env=env,
        )
        
        # Save test result
        save_test_result(paths, test_result)
        
        if test_result["passed"]:
            log("  Tests PASSED")
        else:
            log(f"  Tests FAILED: {test_result.get('error', 'unknown')}")
    
    # =========================================================================
    # FINALIZE
    # =========================================================================
    
    eval_volume.commit()
    
    total_duration = time.time() - start_time
    
    log("\n" + "=" * 60)
    log(f"Eval Complete: {task.instance_id}")
    log(f"  Patch Source: {patch_source or ('cache' if agent_cached else 'agent')}")
    log(f"  Agent Success: {agent_success}")
    log(f"  Test Passed: {test_result.get('passed') if test_result else None} (cached={test_cached})")
    log(f"  Total Duration: {total_duration:.1f}s")
    log("=" * 60)
    
    return {
        "instance_id": task.instance_id,
        "model": model,
        "patch_source": patch_source or ("cache" if agent_cached else "agent"),
        "agent_success": agent_success,
        "agent_cached": agent_cached,
        "agent_response": agent_response,
        "test_passed": test_result.get("passed") if test_result else None,
        "test_cached": test_cached,
        "test_error": test_result.get("error") if test_result else None,
        "total_duration_seconds": total_duration,
        "setup_duration_seconds": setup_duration,
        "server_startup_seconds": server_startup_duration,
        "server_was_ready": server_was_ready,  # Whether server reported ready before timeout
        "agent_query_seconds": agent_duration,
        "test_duration_seconds": test_result.get("duration_seconds") if test_result else None,
        "timestamps": timestamps,
        "result_paths": paths,
        "include_intellij_guidance": include_intellij_guidance,
    }


# Anki-Android eval function (uses anki_image)
@app.function(
    image=anki_image,
    volumes={EVAL_VOLUME_PATH: eval_volume},
    secrets=[github_secret],
    timeout=MODAL_TASK_TIMEOUT,
    cpu=8,
    memory=16384,  # 16GB RAM
)
def run_eval_task(
    task_dict: dict,
    model: str,
    patch_source: str = None,
    use_agent_cache: bool = True,
    use_test_cache: bool = True,
    include_intellij_guidance: bool = True,
    oracle_files: bool = False,
) -> dict:
    """Run eval for Anki-Android tasks (default/legacy)."""
    return _run_eval_task_impl(
        task_dict, model, patch_source, use_agent_cache, use_test_cache,
        include_intellij_guidance, oracle_files
    )


# =============================================================================
# Repo-Specific Eval Functions
# =============================================================================
# Modal requires images to be bound at function definition time, so we need
# separate functions for each repository's Docker image.

# The actual implementation is shared via run_eval_task (Anki image)
# These wrapper functions use the same logic but with different images.

# Note: run_eval_task above uses anki_image and handles Anki-Android tasks


@app.function(
    image=wordpress_image,
    volumes={EVAL_VOLUME_PATH: eval_volume},
    secrets=[github_secret],
    timeout=MODAL_TASK_TIMEOUT,
    cpu=8,
    memory=16384,
)
def run_eval_task_wordpress(
    task_dict: dict,
    model: str,
    patch_source: str = None,
    use_agent_cache: bool = True,
    use_test_cache: bool = True,
    include_intellij_guidance: bool = True,
    oracle_files: bool = False,
) -> dict:
    """Run eval for WordPress-Android tasks."""
    return _run_eval_task_impl(
        task_dict, model, patch_source, use_agent_cache, use_test_cache,
        include_intellij_guidance, oracle_files
    )


@app.function(
    image=ktlint_image,
    volumes={EVAL_VOLUME_PATH: eval_volume},
    secrets=[github_secret],
    timeout=MODAL_TASK_TIMEOUT,
    cpu=8,
    memory=16384,
)
def run_eval_task_ktlint(
    task_dict: dict,
    model: str,
    patch_source: str = None,
    use_agent_cache: bool = True,
    use_test_cache: bool = True,
    include_intellij_guidance: bool = True,
    oracle_files: bool = False,
) -> dict:
    """Run eval for ktlint tasks."""
    return _run_eval_task_impl(
        task_dict, model, patch_source, use_agent_cache, use_test_cache,
        include_intellij_guidance, oracle_files
    )


@app.function(
    image=coroutines_image,
    volumes={EVAL_VOLUME_PATH: eval_volume},
    secrets=[github_secret],
    timeout=MODAL_TASK_TIMEOUT,
    cpu=8,
    memory=16384,
)
def run_eval_task_coroutines(
    task_dict: dict,
    model: str,
    patch_source: str = None,
    use_agent_cache: bool = True,
    use_test_cache: bool = True,
    include_intellij_guidance: bool = True,
    oracle_files: bool = False,
) -> dict:
    """Run eval for kotlinx.coroutines tasks."""
    return _run_eval_task_impl(
        task_dict, model, patch_source, use_agent_cache, use_test_cache,
        include_intellij_guidance, oracle_files
    )


@app.function(
    image=thunderbird_image,
    volumes={EVAL_VOLUME_PATH: eval_volume},
    secrets=[github_secret],
    timeout=MODAL_TASK_TIMEOUT,
    cpu=8,
    memory=16384,
)
def run_eval_task_thunderbird(
    task_dict: dict,
    model: str,
    patch_source: str = None,
    use_agent_cache: bool = True,
    use_test_cache: bool = True,
    include_intellij_guidance: bool = True,
    oracle_files: bool = False,
) -> dict:
    """Run eval for Thunderbird-Android tasks."""
    return _run_eval_task_impl(
        task_dict, model, patch_source, use_agent_cache, use_test_cache,
        include_intellij_guidance, oracle_files
    )


@app.function(
    image=datetime_image,
    volumes={EVAL_VOLUME_PATH: eval_volume},
    secrets=[github_secret],
    timeout=MODAL_TASK_TIMEOUT,
    cpu=8,
    memory=16384,
)
def run_eval_task_datetime(
    task_dict: dict,
    model: str,
    patch_source: str = None,
    use_agent_cache: bool = True,
    use_test_cache: bool = True,
    include_intellij_guidance: bool = True,
    oracle_files: bool = False,
) -> dict:
    """Run eval for kotlinx-datetime tasks."""
    return _run_eval_task_impl(
        task_dict, model, patch_source, use_agent_cache, use_test_cache,
        include_intellij_guidance, oracle_files
    )


# Mapping from repo to eval function
REPO_TO_EVAL_FUNC = {
    "ankidroid/Anki-Android": run_eval_task,
    "wordpress-mobile/WordPress-Android": run_eval_task_wordpress,
    "pinterest/ktlint": run_eval_task_ktlint,
    "Kotlin/kotlinx.coroutines": run_eval_task_coroutines,
    "thunderbird/thunderbird-android": run_eval_task_thunderbird,
    "Kotlin/kotlinx-datetime": run_eval_task_datetime,
}


def get_eval_func_for_repo(repo: str):
    """Get the appropriate eval function for a repository."""
    if repo in REPO_SHORT_NAMES:
        repo = REPO_SHORT_NAMES[repo]
    return REPO_TO_EVAL_FUNC.get(repo, run_eval_task)


# =============================================================================
# Batch Evaluation
# =============================================================================

@app.function(
    image=anki_image,
    timeout=60,
)
def get_task_list() -> List[dict]:
    """Get list of all Anki tasks (runs in container to access dataset)."""
    # This would need the dataset in the image, so we'll handle locally
    return []


def run_batch_eval(
    tasks: List[TaskInstance],
    model: str,
    patch_source: str = None,
    use_agent_cache: bool = True,
    use_test_cache: bool = True,
    parallel: bool = True,
    include_intellij_guidance: bool = True,
    oracle_files: bool = False,
) -> List[dict]:
    """
    Run evaluations on multiple tasks.
    
    Automatically dispatches to the correct repo-specific eval function
    based on each task's repository.
    
    Args:
        tasks: List of TaskInstance objects
        model: Model identifier
        patch_source: "gold", "none", or None (run agent)
        use_agent_cache: Whether to use cached agent results
        use_test_cache: Whether to use cached test results
        parallel: Whether to run in parallel
        include_intellij_guidance: Whether to include IntelliJ tool guidance (default True)
        
    Returns:
        List of EvalResult dicts
    """
    print(f"\nRunning batch eval on {len(tasks)} tasks...")
    print(f"  Model: {model}")
    print(f"  Patch Source: {patch_source or 'agent'}")
    print(f"  Use Agent Cache: {use_agent_cache}")
    print(f"  Use Test Cache: {use_test_cache}")
    print(f"  IntelliJ Guidance: {include_intellij_guidance}")
    print(f"  Oracle Files: {oracle_files}")
    print(f"  Mode: {'parallel' if parallel else 'sequential'}")
    
    # Group tasks by repo
    tasks_by_repo: Dict[str, List[TaskInstance]] = {}
    for task in tasks:
        repo = task.repo
        if repo not in tasks_by_repo:
            tasks_by_repo[repo] = []
        tasks_by_repo[repo].append(task)
    
    print(f"  Repos: {list(tasks_by_repo.keys())}")
    
    kwargs = {
        "model": model,
        "patch_source": patch_source,
        "use_agent_cache": use_agent_cache,
        "use_test_cache": use_test_cache,
        "include_intellij_guidance": include_intellij_guidance,
        "oracle_files": oracle_files,
    }
    
    results = []
    
    def get_eval_func(repo: str):
        """Get eval function for the given repo."""
        return get_eval_func_for_repo(repo)
    
    if parallel:
        # Run ALL tasks across ALL repos in parallel using spawn
        # This avoids blocking on one repo before starting the next
        all_futures = []
        for repo, repo_tasks in tasks_by_repo.items():
            eval_func = get_eval_func(repo)
            task_dicts = [t.to_dict() for t in repo_tasks]
            print(f"  Launching {len(task_dicts)} {repo} tasks...")
            # Use spawn to launch without blocking
            for task_dict in task_dicts:
                future = eval_func.spawn(task_dict, **kwargs)
                all_futures.append(future)
        
        # Now collect all results
        print(f"  Waiting for {len(all_futures)} total tasks...")
        for future in all_futures:
            results.append(future.get())
    else:
        # Run sequentially
        for i, task in enumerate(tasks):
            print(f"\n[{i+1}/{len(tasks)}] {task.instance_id}")
            eval_func = get_eval_func(task.repo)
            result = eval_func.remote(task.to_dict(), **kwargs)
            results.append(result)
    
    return results


# =============================================================================
# Results Download and Consolidation
# =============================================================================

@app.function(
    image=util_image,
    volumes={EVAL_VOLUME_PATH: eval_volume},
    timeout=DOWNLOAD_TIMEOUT,
)
def download_model_results(model: str) -> Dict[str, bytes]:
    """
    Download all result files for a model from the Modal volume.
    
    Returns:
        Dict mapping relative paths to file contents
    """
    import glob
    
    model_path = get_volume_model_path(model)
    files_data = {}
    
    if not os.path.exists(model_path):
        print(f"No results found for model: {model}")
        return {}
    
    # Recursively get all files
    for filepath in glob.glob(f"{model_path}/**/*", recursive=True):
        if os.path.isfile(filepath):
            rel_path = os.path.relpath(filepath, model_path)
            try:
                with open(filepath, 'rb') as f:
                    files_data[rel_path] = f.read()
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
    
    print(f"Found {len(files_data)} files for model {model}")
    return files_data


def merge_results_to_canonical_dir(model: str, files_data: Dict[str, bytes]) -> Path:
    """
    Merge downloaded results into the canonical outputs/data/ directory structure.
    
    This reorganizes from volume structure (model/task/settings/) to local structure 
    (task/model/settings/) and merges with existing data.
    
    Volume path:  {model}/{instance_id}/{settings_id}/file.json
    Local path:   data/{instance_id}/{model}/{settings_id}/file.json
    
    Args:
        model: Model identifier
        files_data: Dict mapping relative paths to file contents
        
    Returns:
        Path to the data directory (outputs/data/)
    """
    data_dir = LOCAL_OUTPUTS_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    files_saved = 0
    tasks_updated = set()
    
    for rel_path, content in files_data.items():
        # rel_path is like: "task_id/settings_id/agent_result.json"
        # or for legacy: "task_id/agent_result.json"
        parts = Path(rel_path).parts
        if len(parts) < 2:
            print(f"Skipping unexpected path format: {rel_path}")
            continue
        
        task_id = parts[0]
        
        # Check if path includes settings_id (new format) or not (legacy)
        if len(parts) >= 3 and parts[1].startswith("ij"):
            # New format with settings: task_id/settings_id/filename
            settings_id = parts[1]
            filename = "/".join(parts[2:])
            # Local structure: data/{task_id}/{model}/{settings_id}/{filename}
            file_path = data_dir / task_id / model / settings_id / filename
        else:
            # Legacy format without settings: task_id/filename
            filename = "/".join(parts[1:])
            # Put in default settings folder
            file_path = data_dir / task_id / model / "ij1_oracle0" / filename
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'wb') as f:
            f.write(content)
        files_saved += 1
        tasks_updated.add(task_id)
    
    print(f"Merged {files_saved} files for {len(tasks_updated)} tasks into {data_dir}")
    return data_dir


def generate_consolidated_report() -> dict:
    """
    Generate a consolidated report from all results in outputs/data/.
    
    New structure with settings support:
    - results[task_id][model] = array of results with different settings
    - Each result has { settings: {...}, test_passed, paths, ... }
    
    This allows comparing the same model with different settings (e.g., oracle on/off).
    
    Also saves a copy to outputs/history/ for historical tracking.
    
    Returns:
        Consolidated report dict
    """
    data_dir = LOCAL_OUTPUTS_DIR / "data"
    history_dir = LOCAL_OUTPUTS_DIR / "history"
    report_path = LOCAL_OUTPUTS_DIR / "report.json"
    
    # Initialize report structure
    report = {
        "last_updated": datetime.now().isoformat(),
        "models": [],
        "tasks": [],
        "settings_variants": [],  # List of unique settings combinations seen
        "results": {},  # task_id -> model -> [array of results with different settings]
        "summary": {
            "by_model": {},  # model -> {passed, failed, total}
            "by_model_settings": {},  # model -> settings_id -> {passed, failed, total}
        }
    }
    
    if not data_dir.exists():
        print(f"No data directory found: {data_dir}")
        return report
    
    # Collect all models, tasks, and settings
    all_models = set()
    all_tasks = set()
    all_settings = set()
    
    # Scan data directory: data/{task_id}/{model}/{settings_id}/
    for task_dir in sorted(data_dir.iterdir()):
        if not task_dir.is_dir():
            continue
        
        task_id = task_dir.name
        all_tasks.add(task_id)
        report["results"][task_id] = {}
        
        for model_dir in sorted(task_dir.iterdir()):
            if not model_dir.is_dir():
                continue
            
            model = model_dir.name
            all_models.add(model)
            
            # Array to hold results for different settings
            model_results = []
            
            # Check for settings subdirectories
            for settings_dir in sorted(model_dir.iterdir()):
                if not settings_dir.is_dir():
                    continue
                
                settings_id = settings_dir.name
                all_settings.add(settings_id)
                
                # Parse settings from directory name (e.g., "ij1_oracle0")
                settings_dict = _parse_settings_from_id(settings_id)
                
                # Parse result files for this task+model+settings
                result_entry = _parse_task_model_settings_result(
                    task_id, model, settings_id, settings_dir
                )
                result_entry["settings"] = settings_dict
                model_results.append(result_entry)
            
            report["results"][task_id][model] = model_results
    
    # Set sorted lists
    report["models"] = sorted(all_models)
    report["tasks"] = sorted(all_tasks)
    report["settings_variants"] = sorted(all_settings)
    
    # Calculate per-model summary (aggregated across all settings)
    for model in report["models"]:
        passed = 0
        failed = 0
        total = 0
        for task_id in report["tasks"]:
            results_list = report["results"].get(task_id, {}).get(model, [])
            for result in results_list:
                total += 1
                if result.get("test_passed") is True:
                    passed += 1
                elif result.get("test_passed") is False:
                    failed += 1
        report["summary"]["by_model"][model] = {
            "passed": passed,
            "failed": failed,
            "total": total,
        }
    
    # Calculate per-model-settings summary
    for model in report["models"]:
        report["summary"]["by_model_settings"][model] = {}
        for settings_id in report["settings_variants"]:
            passed = 0
            failed = 0
            total = 0
            for task_id in report["tasks"]:
                results_list = report["results"].get(task_id, {}).get(model, [])
                for result in results_list:
                    if result.get("settings", {}) == _parse_settings_from_id(settings_id):
                        total += 1
                        if result.get("test_passed") is True:
                            passed += 1
                        elif result.get("test_passed") is False:
                            failed += 1
            if total > 0:
                report["summary"]["by_model_settings"][model][settings_id] = {
                    "passed": passed,
                    "failed": failed,
                    "total": total,
                }
    
    # Archive previous report if exists
    if report_path.exists():
        history_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(report_path) as f:
                old_report = json.load(f)
            old_timestamp = old_report.get("last_updated", "unknown").replace(":", "-")
            history_path = history_dir / f"report_{old_timestamp}.json"
            with open(history_path, 'w') as f:
                json.dump(old_report, f, indent=2)
            print(f"Archived previous report to: {history_path}")
        except Exception as e:
            print(f"Warning: Could not archive old report: {e}")
    
    # Save new report
    LOCAL_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"Report saved to: {report_path}")
    
    return report


def _parse_settings_from_id(settings_id: str) -> dict:
    """Parse a settings ID string (e.g., 'ij1_oracle0') into a dict."""
    settings = {
        "intellij_guidance": True,
        "oracle_files": False,
    }
    
    if "ij0" in settings_id:
        settings["intellij_guidance"] = False
    if "oracle1" in settings_id:
        settings["oracle_files"] = True
    
    return settings


def _parse_task_model_settings_result(task_id: str, model: str, settings_id: str, settings_dir: Path) -> dict:
    """
    Parse result files for a specific task+model+settings combination.
    
    Returns a result entry with status and paths to raw files.
    """
    result = {
        "test_passed": None,
        "test_error": None,
        "has_patch": False,
        "updated_at": None,
        "paths": {}
    }
    
    # Define expected files and their relative paths
    file_mappings = {
        "agent_result": "agent_result.json",
        "agent_patch": "agent_patch.diff",
        "agent_log": "agent_log.json",
        "idea_log": "idea.log",
        "test_result": "test_result.json",
        "test_output": "test_output.log",
    }
    
    # Check which files exist and build paths
    for key, filename in file_mappings.items():
        file_path = settings_dir / filename
        if file_path.exists():
            # Store relative path from outputs/ directory
            result["paths"][key] = f"data/{task_id}/{model}/{settings_id}/{filename}"
    
    # Parse agent_result.json for agent status
    agent_result_path = settings_dir / "agent_result.json"
    if agent_result_path.exists():
        try:
            with open(agent_result_path) as f:
                agent_data = json.load(f)
            result["agent_success"] = agent_data.get("success", False)
            # Track when this was updated
            if "timestamp" in agent_data:
                result["updated_at"] = agent_data["timestamp"]
        except (json.JSONDecodeError, IOError):
            pass
    
    # Check patch
    patch_path = settings_dir / "agent_patch.diff"
    if patch_path.exists():
        result["has_patch"] = patch_path.stat().st_size > 0
    
    # Parse test_result.json
    test_result_path = settings_dir / "test_result.json"
    if test_result_path.exists():
        try:
            with open(test_result_path) as f:
                test_data = json.load(f)
            result["test_passed"] = test_data.get("passed")
            result["test_error"] = test_data.get("error")
            result["test_duration"] = test_data.get("duration_seconds")
            # Use test timestamp if agent timestamp not available
            if result["updated_at"] is None and "timestamp" in test_data:
                result["updated_at"] = test_data["timestamp"]
        except (json.JSONDecodeError, IOError):
            pass
    
    return result


def download_and_report(model: str) -> dict:
    """
    Download results from Modal volume and merge into consolidated report.
    
    This downloads results for a specific model and merges them into the
    canonical outputs/data/ directory structure. Then regenerates the
    consolidated report (outputs/report.json) with all models/tasks.
    
    Args:
        model: Model identifier
        
    Returns:
        Consolidated report dict (includes all models, not just downloaded one)
    """
    print(f"\nDownloading results for model: {model}")
    
    # Download from Modal volume
    files_data = download_model_results.remote(model)
    
    if not files_data:
        print("No results found to download")
        return {}
    
    # Merge into canonical directory structure (task/model organization)
    merge_results_to_canonical_dir(model, files_data)
    
    # Generate consolidated report (scans all tasks/models in data/)
    report = generate_consolidated_report()
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"CONSOLIDATED REPORT")
    print("=" * 60)
    print(f"Models: {', '.join(report.get('models', []))}")
    print(f"Tasks:  {len(report.get('tasks', []))}")
    print()
    
    # Per-model summary
    for model_name, stats in report.get("summary", {}).get("by_model", {}).items():
        passed = stats.get("passed", 0)
        failed = stats.get("failed", 0)
        total = stats.get("total", 0)
        print(f"  {model_name}:")
        print(f"    Tests Passed: {passed}/{total}")
        print(f"    Tests Failed: {failed}/{total}")
    
    print(f"\nResults saved to: {LOCAL_OUTPUTS_DIR / 'data'}")
    print(f"Report saved to:  {LOCAL_OUTPUTS_DIR / 'report.json'}")
    
    return report


# =============================================================================
# CLI Entry Point
# =============================================================================

@app.local_entrypoint()
def main(
    model: str = None,  # Single model (use --model or --models, not both)
    models: str = None,  # Multiple models, comma-separated (e.g., "claude-opus-4-5,gpt-4o")
    task_id: str = None,
    task_ids: str = None,
    all_tasks: bool = False,
    list_tasks: bool = False,
    list_repos: bool = False,
    repo: str = None,  # Single repo (use --repo or --repos, not both)
    repos: str = None,  # Multiple repos, comma-separated (e.g., "anki,ktlint")
    patch: str = None,
    no_agent_cache: bool = False,
    no_test_cache: bool = False,
    parallel: bool = True,
    output: str = None,
    download: bool = False,
    no_intellij_guidance: bool = False,
    oracle: bool = False,
):
    """
    Run agentic evaluations on Kotlin-bench tasks.
    
    Supported Repositories:
        - anki (ankidroid/Anki-Android)
        - wordpress (wordpress-mobile/WordPress-Android)
        - ktlint (pinterest/ktlint)
        - coroutines (Kotlin/kotlinx.coroutines)
        - thunderbird (thunderbird/thunderbird-android)
        - datetime (Kotlin/kotlinx-datetime)
    
    Examples:
        # List available repos
        modal run agent-bench/run_eval.py --list-repos
        
        # List tasks for a specific repo
        modal run agent-bench/run_eval.py --list-tasks --repo anki
        modal run agent-bench/run_eval.py --list-tasks --repo ktlint
        
        # Run agent on single task
        modal run agent-bench/run_eval.py --task-id ankidroid__Anki-Android-16395
        
        # Run all tasks for a specific repo
        modal run agent-bench/run_eval.py --all-tasks --repo anki
        modal run agent-bench/run_eval.py --all-tasks --repo ktlint

        # Run all tasks for multiple repos
        modal run agent-bench/run_eval.py --all-tasks --repos anki,ktlint

        # Run all tasks across all repos
        modal run agent-bench/run_eval.py --all-tasks

        # Test with gold patches (should pass)
        modal run agent-bench/run_eval.py --all-tasks --repo anki --patch gold
        
        # Download results and create report
        modal run agent-bench/run_eval.py --download --model firebender
    
    Args:
        task_id: Run a specific task by instance_id
        task_ids: Run multiple tasks (comma-separated)
        all_tasks: Run all tasks (for specified repo, or all repos if not specified)
        list_tasks: List available tasks
        list_repos: List available repos with task counts
        repo: Repository to filter (e.g., "anki", "ktlint", "coroutines")
        model: Model identifier
        patch: Patch source - "gold" (correct solution), "none" (baseline), omit for agent
        no_agent_cache: Force re-run agent even if cached
        no_test_cache: Force re-run tests even if cached
        parallel: Run tasks in parallel (default True)
        output: Output file for results JSON
        download: Download results from Modal volume and create consolidated report
        no_intellij_guidance: Disable IntelliJ tool guidance (default: guidance enabled)
    """
    print("=" * 60)
    print("Kotlin-bench Agentic Evaluation")
    print("=" * 60)

    # Parse model list from either --model or --models
    model_list = []
    if models:
        model_list = [m.strip() for m in models.split(",") if m.strip()]
    elif model:
        model_list = [model]
    
    # Validate model is provided for operations that need it
    needs_model = download or task_id or task_ids or all_tasks
    if needs_model and not model_list:
        print("\nError: --model or --models is required")
        print("Examples:")
        print("  modal run agent-bench/run_eval.py --all-tasks --model claude-sonnet-4-20250514")
        print("  modal run agent-bench/run_eval.py --all-tasks --models claude-opus-4-5,gpt-4o")
        return

    # Handle download-only mode
    if download:
        for m in model_list:
            print(f"\nDownloading results for model: {m}")
            download_and_report(m)
        return
    
    # List available repos
    if list_repos:
        print("\nAvailable Repositories:")
        print("-" * 60)
        repo_counts = get_repos_with_tasks()
        for repo_name, count in sorted(repo_counts.items()):
            short_name = next((k for k, v in REPO_SHORT_NAMES.items() if v == repo_name), "")
            has_image = repo_name in REPO_TO_IMAGE
            status = "✓" if has_image else "✗ (no image)"
            print(f"  {short_name:12} {repo_name:40} {count:4} tasks  {status}")
        print("-" * 60)
        print("\nUse --repo <name> or --repos <n1,n2> to filter tasks by repository")
        print("Short names: anki, wordpress, ktlint, coroutines, thunderbird, datetime")
        return
    
    # Validate patch option
    if patch and patch not in ("gold", "none"):
        print(f"Invalid --patch value: {patch}")
        print("Valid options: gold, none")
        return
    
    # Print mode
    if patch == "gold":
        print("Mode: GOLD PATCH (testing with correct solution)")
    elif patch == "none":
        print("Mode: BASELINE (no code changes, tests should fail)")
    else:
        print("Mode: AGENT")
    
    # Parse repo list from either --repo or --repos
    repo_list = []
    if repos:
        repo_list = [r.strip() for r in repos.split(",") if r.strip()]
    elif repo:
        repo_list = [repo]
    
    if repo_list:
        # Resolve short names for display
        resolved_repos = [REPO_SHORT_NAMES.get(r, r) for r in repo_list]
        if len(resolved_repos) == 1:
            print(f"Repo: {resolved_repos[0]}")
        else:
            print(f"Repos: {', '.join(resolved_repos)}")
    
    # Resolve intellij guidance (use negative flag for CLI convenience)
    include_intellij_guidance = not no_intellij_guidance
    oracle_files = oracle

    if no_agent_cache:
        print("  Agent cache: DISABLED (will re-run agent)")
    if no_test_cache:
        print("  Test cache: DISABLED (will re-run tests)")
    if no_intellij_guidance:
        print("  IntelliJ Guidance: DISABLED")
    else:
        print("  IntelliJ Guidance: ENABLED")
    if oracle:
        print("  Oracle Files: ENABLED (providing file hints from gold patch)")
    
    # Load tasks (filtered by repos if specified)
    tasks = load_tasks(repo_list if repo_list else None)
    
    if not tasks:
        if repo_list:
            print(f"No tasks found for repos: {', '.join(repo_list)}")
        else:
            print("No tasks found in dataset!")
        print("Make sure agent-bench/data/kotlin_bench.json exists")
        print("Use --list-repos to see available repositories")
        return
    
    if list_tasks:
        if repo_list:
            repo_display = ', '.join(repo_list) if len(repo_list) > 1 else repo_list[0]
        else:
            repo_display = "all repos"
        print(f"\nAvailable Tasks for {repo_display} ({len(tasks)} total):\n")
        
        # Group by repo if showing multiple repos or all
        if not repo_list or len(repo_list) > 1:
            tasks_by_repo: Dict[str, List] = {}
            for t in tasks:
                if t.repo not in tasks_by_repo:
                    tasks_by_repo[t.repo] = []
                tasks_by_repo[t.repo].append(t)
            
            for repo_name, repo_tasks in sorted(tasks_by_repo.items()):
                print(f"  {repo_name} ({len(repo_tasks)} tasks):")
                for t in repo_tasks[:3]:  # Show first 3
                    print(f"    - {t.instance_id}")
                if len(repo_tasks) > 3:
                    print(f"    ... and {len(repo_tasks) - 3} more")
                print()
        else:
            # Single repo - show detailed view
            for t in tasks:
                print(f"  {t.instance_id}")
                print(f"    Version: {t.version}")
                print(f"    Commit: {t.base_commit[:8]}")
                print()
        return
    
    # Determine which tasks to run
    selected_tasks = []
    
    if task_id:
        # Find task across all repos (or filtered repo)
        task = next((t for t in tasks if t.instance_id == task_id), None)
        if not task:
            # Try loading all tasks if repo was specified
            if repo:
                all_tasks_list = load_tasks(None)
                task = next((t for t in all_tasks_list if t.instance_id == task_id), None)
                if task:
                    print(f"Note: Task {task_id} is from {task.repo}, not {repo}")
            if not task:
                print(f"Task not found: {task_id}")
                print("\nUse --list-tasks to see available tasks")
                return
        selected_tasks = [task]
        
    elif task_ids:
        # Parse comma-separated task IDs
        ids = [tid.strip() for tid in task_ids.split(",")]
        all_tasks_list = load_tasks(None)  # Load all to find any task
        for tid in ids:
            task = next((t for t in all_tasks_list if t.instance_id == tid), None)
            if not task:
                print(f"Task not found: {tid}")
                return
            selected_tasks.append(task)
            
    elif all_tasks:
        selected_tasks = tasks
        
    else:
        print("\nUsage:")
        print("  modal run agent-bench/run_eval.py --list-repos")
        print("  modal run agent-bench/run_eval.py --list-tasks [--repo <name>]")
        print("  modal run agent-bench/run_eval.py --task-id <id>")
        print("  modal run agent-bench/run_eval.py --task-ids <id1,id2,id3>")
        print("  modal run agent-bench/run_eval.py --all-tasks [--repo <name>]")
        print("  modal run agent-bench/run_eval.py --download --model <name>")
        print("\nRepository Filter:")
        print("  --repo <name>        Single repo (anki, wordpress, ktlint, coroutines, thunderbird, datetime)")
        print("  --repos <n1,n2>      Multiple repos, comma-separated (e.g., anki,ktlint)")
        print("\nPatch Source:")
        print("  (default)            Run agent (or use cache)")
        print("  --patch gold         Use gold/correct patch")
        print("  --patch none         No changes (baseline)")
        print("\nCache Options:")
        print("  --no-agent-cache     Force re-run agent, ignore agent cache")
        print("  --no-test-cache      Force re-run tests, ignore test cache")
        print("\nEval Settings:")
        print("  (default)                IntelliJ tool guidance enabled, oracle disabled")
        print("  --no-intellij-guidance   Disable IntelliJ tool guidance in system prompt")
        print("  --oracle                 Enable oracle mode (provide relevant files from gold patch)")
        print("\nModel Selection (REQUIRED):")
        print("  --model <name>       Single model to use")
        print("  --models <n1,n2>     Multiple models (comma-separated, parallel execution)")
        print("  --parallel           Run tasks in parallel (default)")
        print("  --no-parallel        Run tasks sequentially")
        print("  --output <file>      Save results to file")
        print("  --download           Download results and create report (no eval)")
        return
    
    # Run evaluation
    total_jobs = len(selected_tasks) * len(model_list)
    print(f"\nRunning {len(selected_tasks)} task(s) x {len(model_list)} model(s) = {total_jobs} total jobs")
    print(f"  Models: {', '.join(model_list)}")
    
    # Show repo breakdown
    repos_in_batch = set(t.repo for t in selected_tasks)
    if len(repos_in_batch) > 1:
        print(f"  Repos: {', '.join(repos_in_batch)}")
    
    start_time = time.time()
    
    # Common kwargs for all jobs
    common_kwargs = {
        "patch_source": patch,
        "use_agent_cache": not no_agent_cache,
        "use_test_cache": not no_test_cache,
        "include_intellij_guidance": include_intellij_guidance,
        "oracle_files": oracle_files,
    }
    
    results = []
    
    if parallel and total_jobs > 1:
        # Run ALL (task, model) combinations in parallel
        print(f"\nLaunching {total_jobs} jobs in parallel...")
        all_futures = []
        
        for m in model_list:
            for task in selected_tasks:
                eval_func = get_eval_func_for_repo(task.repo)
                future = eval_func.spawn(task.to_dict(), model=m, **common_kwargs)
                all_futures.append((m, task.instance_id, future))
        
        # Collect results
        print(f"Waiting for {len(all_futures)} jobs to complete...")
        for m, task_id, future in all_futures:
            result = future.get()
            result["model"] = m  # Ensure model is in result
            results.append(result)
    else:
        # Sequential execution
        for m in model_list:
            print(f"\n--- Model: {m} ---")
            for i, task in enumerate(selected_tasks):
                print(f"[{i+1}/{len(selected_tasks)}] {task.instance_id}")
                eval_func = get_eval_func_for_repo(task.repo)
                result = eval_func.remote(task.to_dict(), model=m, **common_kwargs)
                result["model"] = m
                results.append(result)
    
    wall_time = time.time() - start_time
    
    # Print summary
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    
    print(f"Models: {', '.join(model_list)}")
    print(f"Tasks: {len(selected_tasks)}")
    print(f"Total Jobs: {len(results)}")
    print(f"IntelliJ Guidance: {'ENABLED' if include_intellij_guidance else 'DISABLED'}")
    print(f"Oracle Files: {'ENABLED' if oracle_files else 'DISABLED'}")
    print(f"Wall clock time: {wall_time:.1f}s")
    
    # Per-model summary
    print("\n" + "-" * 60)
    for m in model_list:
        model_results = [r for r in results if r.get("model") == m]
        agent_success = sum(1 for r in model_results if r.get("agent_success"))
        test_passed = sum(1 for r in model_results if r.get("test_passed"))
        print(f"{m}:")
        print(f"  Patch Applied: {agent_success}/{len(model_results)}")
        print(f"  Tests Passed:  {test_passed}/{len(model_results)}")
    
    # Per-task summary (grouped by model)
    print("\n" + "-" * 100)
    print(f"{'Model':<25} {'Task ID':<40} {'Patch':<10} {'Tests':<12} {'Time (s)':<10}")
    print("-" * 100)
    for r in results:
        model_name = r.get("model", "unknown")[:24]
        task_id = r.get("instance_id", "unknown")[:39]
        patch_str = r.get("patch_source", "agent")
        if r.get("agent_cached"):
            patch_str = "cache"
        test_str = "PASS" if r.get("test_passed") else ("FAIL" if r.get("test_passed") is False else "-")
        if r.get("test_cached"):
            test_str += " (cached)"
        duration = r.get("total_duration_seconds", 0)
        print(f"{model_name:<25} {task_id:<40} {patch_str:<10} {test_str:<12} {duration:<10.1f}")
    
    # Save immediate results (for quick reference)
    output_file = output or f"eval_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {output_file}")
    
    # Download all results and create consolidated report
    print("\n" + "=" * 60)
    print("Downloading and consolidating results...")
    print("=" * 60)
    for m in model_list:
        download_and_report(m)
