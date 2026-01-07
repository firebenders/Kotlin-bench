"""
Test Agent Server Startup Time on Modal

Measures how long it takes for the IDE agent server to become ready
for each task instance. This includes the full setup process:
- Reset to base commit
- Configure JDK and Android SDK
- Run install scripts
- Install Firebender plugin
- Start IDE and wait for ready

Usage:
    # Test a single task
    modal run agent-bench/docker/test_server_startup.py --task-id pinterest__ktlint-1766
    
    # Test all tasks for a repo
    modal run agent-bench/docker/test_server_startup.py --repo ktlint --all-tasks
    
    # Test all tasks across all repos (in parallel)
    modal run agent-bench/docker/test_server_startup.py --all-tasks --parallel
    
    # List available tasks
    modal run agent-bench/docker/test_server_startup.py --list-tasks --repo ktlint
    
    # Adjust timeout and poll interval
    modal run agent-bench/docker/test_server_startup.py --task-id xxx --timeout 600 --poll-interval 2

Available repos: anki, coroutines, datetime, ktlint, thunderbird, wordpress
"""

import modal
import os
import subprocess
import sys
import time
import json
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass, field, asdict
import statistics

# =============================================================================
# Configuration
# =============================================================================

AVAILABLE_REPOS = ["anki", "coroutines", "datetime", "ktlint", "thunderbird", "wordpress"]
ANDROID_REPOS = {"anki", "thunderbird", "wordpress"}

# Repo short names to full names
REPO_SHORT_NAMES = {
    "anki": "ankidroid/Anki-Android",
    "wordpress": "wordpress-mobile/WordPress-Android",
    "ktlint": "pinterest/ktlint",
    "coroutines": "Kotlin/kotlinx.coroutines",
    "thunderbird": "thunderbird/thunderbird-android",
    "datetime": "Kotlin/kotlinx-datetime",
}

REPO_FULL_TO_SHORT = {v: k for k, v in REPO_SHORT_NAMES.items()}

# Agent server config
AGENT_PORT = 8742
DEFAULT_TIMEOUT = 600  # 10 minutes
DEFAULT_POLL_INTERVAL = 3  # seconds

# Paths
PROJECT_PATH = "/project"
SDKMAN_JAVA_PATH = "/root/.sdkman/candidates/java"
ANDROID_SDK_PATH = "/root/android-sdk"
FIREBENDER_PLUGIN_ZIP = "firebender/Firebender.zip"
IDEA_PLUGINS_DIR = "/root/.local/share/JetBrains/IdeaIC2025.1"

# Setup timeout
SETUP_TIMEOUT = 300  # 5 minutes

# =============================================================================
# Task Instance (from run_eval.py)
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
    patch: Optional[str] = None
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
# Installation Specs (from constants.py)
# =============================================================================

# Load config JSON files
def load_repo_config(repo_name: str) -> dict:
    """Load config for a repository from its JSON file."""
    config_paths = [
        Path("/root/agent-bench/config") / f"{repo_name}.json",
        Path(__file__).parent.parent / "config" / f"{repo_name}.json",
    ]
    for config_file in config_paths:
        if config_file.exists():
            with open(config_file) as f:
                return json.load(f)
    return {}


def get_install_specs(repo: str, version: str) -> dict:
    """Get installation specifications for a repo/version."""
    # Map full repo name to short config name
    config_name = REPO_FULL_TO_SHORT.get(repo, repo)
    config = load_repo_config(config_name)
    
    return {
        "jdk_version": config.get("jdk_version", "17.0.9-tem"),
        "install": config.get("install_script", ""),
    }


def is_android_project(repo: str) -> bool:
    """Check if a repo is an Android project."""
    config_name = REPO_FULL_TO_SHORT.get(repo, repo)
    config = load_repo_config(config_name)
    return bool(config.get("android_sdk_packages", []))


# =============================================================================
# Images - WITH Firebender plugin zip and agent-bench code
# =============================================================================

def _create_test_image(repo_name: str) -> modal.Image:
    """Create a Modal image with Firebender plugin for a repository."""
    return (
        modal.Image.from_dockerfile(
            path=f"agent-bench/docker/generated/Dockerfile.{repo_name}",
            context_dir=".",
            add_python="3.11",
        )
        # Add the Firebender plugin zip for runtime installation
        .add_local_file(FIREBENDER_PLUGIN_ZIP, "/tmp/Firebender.zip", copy=True)
        # Add agent-bench code for config files
        .add_local_dir(
            local_path=Path(__file__).parent.parent,
            remote_path="/root/agent-bench",
        )
    )


image_anki = _create_test_image("anki")
image_coroutines = _create_test_image("coroutines")
image_datetime = _create_test_image("datetime")
image_ktlint = _create_test_image("ktlint")
image_thunderbird = _create_test_image("thunderbird")
image_wordpress = _create_test_image("wordpress")

IMAGES = {
    "anki": image_anki,
    "coroutines": image_coroutines,
    "datetime": image_datetime,
    "ktlint": image_ktlint,
    "thunderbird": image_thunderbird,
    "wordpress": image_wordpress,
}

# =============================================================================
# App
# =============================================================================

app = modal.App("kotlin-bench-startup-test")


# =============================================================================
# Task Environment Setup (from run_eval.py)
# =============================================================================

def reset_to_base_commit(project_path: str, base_commit: str) -> bool:
    """Reset the repository to the base commit for this task."""
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


def setup_task_environment(task: TaskInstance, project_path: str, env: dict) -> bool:
    """Configure the task environment (JDK, Android SDK, install scripts)."""
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
            else:
                print(f"    Installation script completed successfully")
        except subprocess.TimeoutExpired:
            print(f"    Installation script timed out")
        except Exception as e:
            print(f"    Installation script error: {e}")
    else:
        print(f"    No installation script needed")
    
    return True


def prepare_task_environment(task: TaskInstance, project_path: str, env: dict) -> tuple:
    """Prepare the task environment: reset to base commit and configure."""
    print("[Setup] Preparing task environment...")
    
    if not reset_to_base_commit(project_path, task.base_commit):
        return False, "Failed to reset to base commit"
    
    if not setup_task_environment(task, project_path, env):
        return False, "Failed to setup task environment"
    
    return True, None


# =============================================================================
# Firebender Plugin Installation
# =============================================================================

def install_firebender_plugin() -> bool:
    """Install the Firebender plugin at runtime."""
    plugin_zip = "/tmp/Firebender.zip"
    plugins_dir = IDEA_PLUGINS_DIR
    
    print(f"  Installing Firebender plugin...")
    print(f"    Source: {plugin_zip}")
    print(f"    Target: {plugins_dir}")
    
    if not os.path.exists(plugin_zip):
        print(f"    ERROR: Plugin zip not found at {plugin_zip}")
        return False
    
    zip_size = os.path.getsize(plugin_zip)
    print(f"    Plugin zip size: {zip_size / 1024 / 1024:.1f} MB")
    
    # Ensure plugins directory exists
    os.makedirs(plugins_dir, exist_ok=True)
    
    # Extract the plugin
    try:
        result = subprocess.run(
            ["unzip", "-o", plugin_zip, "-d", plugins_dir],
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            print(f"    ERROR: unzip failed: {result.stderr}")
            return False
        
        print(f"    Plugin extracted successfully")
        
    except Exception as e:
        print(f"    ERROR: Exception during unzip: {e}")
        return False
    
    # Verify Firebender is there
    plugins = os.listdir(plugins_dir) if os.path.exists(plugins_dir) else []
    firebender_found = any("Firebender" in p or "firebender" in p for p in plugins)
    if firebender_found:
        print(f"    Firebender plugin verified!")
        return True
    else:
        print(f"    WARNING: Firebender not found after extraction")
        return False


# =============================================================================
# Agent Server Management
# =============================================================================

def start_agent_server(project_path: str, env: dict, log_file: str, is_android: bool = False) -> subprocess.Popen:
    """Start the IDE with agent server enabled."""
    
    bypass_auth_key = "firebender-bypass-auth-2025"
    env["FIREBENDER_AGENT_SERVER"] = "true"
    env["FIREBENDER_AGENT_SERVER_PORT"] = str(AGENT_PORT)
    env["FIREBENDER_ANDROID_PROJECT"] = "true" if is_android else "false"
    env["FIREBENDER_BYPASS_AUTH_KEY"] = bypass_auth_key
    env["DISPLAY"] = ":99"
    
    # JVM options
    env["_JAVA_OPTIONS"] = " ".join([
        "-Dfirebender.agentServer=true",
        f"-Dfirebender.agentServerPort={AGENT_PORT}",
        f"-Dfirebender.androidProject={'true' if is_android else 'false'}",
        f"-Dfirebender.bypassAuthKey={bypass_auth_key}",
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
    
    cmd = [
        "xvfb-run", "-a",
        "-s", "-screen 0 1920x1080x24",
        "env",
        f"FIREBENDER_AGENT_SERVER=true",
        f"FIREBENDER_AGENT_SERVER_PORT={AGENT_PORT}",
        f"FIREBENDER_ANDROID_PROJECT={'true' if is_android else 'false'}",
        f"FIREBENDER_BYPASS_AUTH_KEY={bypass_auth_key}",
        "/opt/idea/bin/idea.sh",
        project_path,
    ]
    
    log_handle = open(log_file, "w")
    
    process = subprocess.Popen(
        cmd,
        cwd=project_path,
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    
    return process


def wait_for_server_ready(timeout: int, poll_interval: int) -> dict:
    """Poll the /ready endpoint until server is ready or timeout."""
    start_time = time.time()
    
    first_response_time: Optional[float] = None
    indexing_start_time: Optional[float] = None
    indexing_complete_time: Optional[float] = None
    gradle_sync_start_time: Optional[float] = None
    gradle_sync_complete_time: Optional[float] = None
    server_ready_time: Optional[float] = None
    
    responses = []
    connection_errors = 0
    http_errors = 0
    
    last_message = ""
    last_indexing_state = None
    last_gradle_state = None
    
    print(f"  Polling http://localhost:{AGENT_PORT}/ready (timeout: {timeout}s, interval: {poll_interval}s)")
    print()
    
    while time.time() - start_time < timeout:
        elapsed = time.time() - start_time
        
        try:
            req = urllib.request.Request(f"http://localhost:{AGENT_PORT}/ready")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                
                if first_response_time is None:
                    first_response_time = elapsed
                    print(f"  [{elapsed:6.1f}s] First response from server!")
                
                responses.append({"time": elapsed, "data": data})
                
                # Track indexing
                indexing_data = data.get("indexing", {})
                indexing_complete = indexing_data.get("complete", False)
                
                if indexing_data != last_indexing_state:
                    if indexing_start_time is None and not indexing_complete:
                        indexing_start_time = elapsed
                        print(f"  [{elapsed:6.1f}s] Indexing started")
                    
                    if indexing_complete and indexing_complete_time is None:
                        indexing_complete_time = elapsed
                        print(f"  [{elapsed:6.1f}s] Indexing complete")
                    
                    last_indexing_state = indexing_data
                
                # Track gradle sync
                gradle_data = data.get("gradleSync", {})
                gradle_complete = gradle_data.get("complete", False)
                
                if gradle_data != last_gradle_state:
                    if gradle_sync_start_time is None and not gradle_complete:
                        gradle_sync_start_time = elapsed
                        print(f"  [{elapsed:6.1f}s] Gradle sync started")
                    
                    if gradle_complete and gradle_sync_complete_time is None:
                        gradle_sync_complete_time = elapsed
                        print(f"  [{elapsed:6.1f}s] Gradle sync complete")
                    
                    last_gradle_state = gradle_data
                
                message = data.get("message", "")
                if message != last_message:
                    print(f"  [{elapsed:6.1f}s] Status: {message}")
                    last_message = message
                
                is_ready = data.get("ready", False)
                if is_ready:
                    server_ready_time = elapsed
                    print(f"  [{elapsed:6.1f}s] SERVER READY!")
                    
                    return {
                        "success": True,
                        "total_time": elapsed,
                        "first_response_time": first_response_time,
                        "indexing_start_time": indexing_start_time,
                        "indexing_complete_time": indexing_complete_time,
                        "gradle_sync_start_time": gradle_sync_start_time,
                        "gradle_sync_complete_time": gradle_sync_complete_time,
                        "server_ready_time": server_ready_time,
                        "connection_errors": connection_errors,
                        "http_errors": http_errors,
                        "response_count": len(responses),
                        "final_response": data,
                    }
                    
        except urllib.error.HTTPError as e:
            http_errors += 1
            if http_errors <= 3:
                print(f"  [{elapsed:6.1f}s] HTTP Error: {e.code} {e.reason}")
                
        except (urllib.error.URLError, ConnectionRefusedError) as e:
            connection_errors += 1
            if connection_errors <= 3 or (connection_errors % 20 == 0):
                print(f"  [{elapsed:6.1f}s] Connection error ({connection_errors} total)")
                
        except Exception as e:
            print(f"  [{elapsed:6.1f}s] Unexpected error: {type(e).__name__}: {e}")
        
        time.sleep(poll_interval)
    
    total_time = time.time() - start_time
    print(f"  [{total_time:6.1f}s] TIMEOUT!")
    
    return {
        "success": False,
        "total_time": total_time,
        "first_response_time": first_response_time,
        "indexing_start_time": indexing_start_time,
        "indexing_complete_time": indexing_complete_time,
        "gradle_sync_start_time": gradle_sync_start_time,
        "gradle_sync_complete_time": gradle_sync_complete_time,
        "server_ready_time": None,
        "connection_errors": connection_errors,
        "http_errors": http_errors,
        "response_count": len(responses),
        "final_response": responses[-1]["data"] if responses else None,
        "error": f"Timeout after {timeout}s",
    }


# =============================================================================
# Main Test Function
# =============================================================================

def _test_task_startup(task_dict: dict, timeout: int, poll_interval: int) -> dict:
    """Run server startup test for a specific task instance."""
    task = TaskInstance.from_dict(task_dict)
    is_android = is_android_project(task.repo)
    project_path = PROJECT_PATH
    log_file = f"/tmp/ide_startup_test_{task.instance_id}.log"
    
    print("=" * 70)
    print(f"Server Startup Test: {task.instance_id}")
    print("=" * 70)
    print(f"  Repo: {task.repo}")
    print(f"  Version: {task.version}")
    print(f"  Base Commit: {task.base_commit[:8]}")
    print(f"  Android project: {is_android}")
    print(f"  Timeout: {timeout}s")
    print(f"  Poll interval: {poll_interval}s")
    print()
    
    env = os.environ.copy()
    timestamps = {"start": datetime.now().isoformat()}
    
    # =========================================================================
    # SETUP PHASE - Full task environment preparation
    # =========================================================================
    
    print("=" * 70)
    print("SETUP PHASE")
    print("=" * 70)
    
    setup_start = time.time()
    
    success, error = prepare_task_environment(task, project_path, env)
    if not success:
        print(f"  ERROR: Setup failed: {error}")
        return {
            "success": False,
            "error": f"Setup failed: {error}",
            "instance_id": task.instance_id,
            "repo": task.repo,
            "total_time": time.time() - setup_start,
        }
    
    setup_duration = time.time() - setup_start
    timestamps["setup_complete"] = datetime.now().isoformat()
    print(f"  Setup completed in {setup_duration:.1f}s")
    print()
    
    # =========================================================================
    # PLUGIN INSTALLATION
    # =========================================================================
    
    print("=" * 70)
    print("PLUGIN INSTALLATION")
    print("=" * 70)
    
    plugin_installed = install_firebender_plugin()
    if not plugin_installed:
        print("  WARNING: Firebender plugin installation may have failed!")
    print()
    
    # =========================================================================
    # SERVER STARTUP TEST
    # =========================================================================
    
    print("=" * 70)
    print("SERVER STARTUP TEST")
    print("=" * 70)
    
    print("Starting IntelliJ IDEA with agent server...")
    server_start = time.time()
    
    process = start_agent_server(project_path, env, log_file, is_android)
    print(f"  Process PID: {process.pid}")
    timestamps["server_started"] = datetime.now().isoformat()
    
    # Brief wait to check for immediate crash
    time.sleep(2)
    if process.poll() is not None:
        print(f"  ERROR: Process exited immediately with code {process.poll()}")
        try:
            with open(log_file, 'r') as f:
                log_content = f.read()
            print(f"  Log (first 1000 chars):\n{log_content[:1000]}")
        except Exception as e:
            print(f"  Could not read log: {e}")
        
        return {
            "success": False,
            "error": "Process crashed immediately",
            "instance_id": task.instance_id,
            "repo": task.repo,
            "total_time": time.time() - setup_start,
            "setup_duration": setup_duration,
            "plugin_installed": plugin_installed,
        }
    
    print()
    print("Waiting for server ready...")
    print()
    
    # Wait for ready
    result = wait_for_server_ready(timeout, poll_interval)
    
    server_startup_duration = time.time() - server_start
    timestamps["server_ready"] = datetime.now().isoformat()
    
    # Cleanup
    print()
    print("Cleaning up...")
    process.terminate()
    try:
        process.wait(timeout=10)
    except:
        process.kill()
    
    # Log analysis
    print()
    print("IDE Log Analysis:")
    try:
        with open(log_file, 'r') as f:
            log_content = f.read()
        
        patterns = [
            ("AgentServer", "Agent server mentions"),
            ("Firebender", "Firebender mentions"),
            ("GradleSync", "Gradle sync mentions"),
            ("ERROR", "Errors"),
        ]
        for pattern, desc in patterns:
            count = log_content.count(pattern)
            print(f"  {desc}: {count}")
                
    except Exception as e:
        print(f"  Could not read log: {e}")
    
    # Build final result
    total_duration = time.time() - setup_start
    
    return {
        "success": result["success"],
        "instance_id": task.instance_id,
        "repo": task.repo,
        "version": task.version,
        "base_commit": task.base_commit,
        "is_android": is_android,
        "total_time": total_duration,
        "setup_duration": setup_duration,
        "server_startup_duration": server_startup_duration,
        "plugin_installed": plugin_installed,
        "first_response_time": result.get("first_response_time"),
        "indexing_complete_time": result.get("indexing_complete_time"),
        "gradle_sync_complete_time": result.get("gradle_sync_complete_time"),
        "server_ready_time": result.get("server_ready_time"),
        "connection_errors": result.get("connection_errors", 0),
        "http_errors": result.get("http_errors", 0),
        "error": result.get("error"),
        "timestamps": timestamps,
    }


# =============================================================================
# Modal Functions (one per repo)
# =============================================================================

@app.function(image=image_ktlint, timeout=3600, cpu=4, memory=16384)
def test_task_startup_ktlint(task_dict: dict, timeout: int = DEFAULT_TIMEOUT, poll_interval: int = DEFAULT_POLL_INTERVAL) -> dict:
    return _test_task_startup(task_dict, timeout, poll_interval)


@app.function(image=image_datetime, timeout=3600, cpu=4, memory=16384)
def test_task_startup_datetime(task_dict: dict, timeout: int = DEFAULT_TIMEOUT, poll_interval: int = DEFAULT_POLL_INTERVAL) -> dict:
    return _test_task_startup(task_dict, timeout, poll_interval)


@app.function(image=image_coroutines, timeout=3600, cpu=4, memory=16384)
def test_task_startup_coroutines(task_dict: dict, timeout: int = DEFAULT_TIMEOUT, poll_interval: int = DEFAULT_POLL_INTERVAL) -> dict:
    return _test_task_startup(task_dict, timeout, poll_interval)


@app.function(image=image_anki, timeout=3600, cpu=4, memory=16384)
def test_task_startup_anki(task_dict: dict, timeout: int = DEFAULT_TIMEOUT, poll_interval: int = DEFAULT_POLL_INTERVAL) -> dict:
    return _test_task_startup(task_dict, timeout, poll_interval)


@app.function(image=image_thunderbird, timeout=3600, cpu=4, memory=16384)
def test_task_startup_thunderbird(task_dict: dict, timeout: int = DEFAULT_TIMEOUT, poll_interval: int = DEFAULT_POLL_INTERVAL) -> dict:
    return _test_task_startup(task_dict, timeout, poll_interval)


@app.function(image=image_wordpress, timeout=3600, cpu=4, memory=16384)
def test_task_startup_wordpress(task_dict: dict, timeout: int = DEFAULT_TIMEOUT, poll_interval: int = DEFAULT_POLL_INTERVAL) -> dict:
    return _test_task_startup(task_dict, timeout, poll_interval)


REPO_TO_TEST_FUNC = {
    "ankidroid/Anki-Android": test_task_startup_anki,
    "wordpress-mobile/WordPress-Android": test_task_startup_wordpress,
    "pinterest/ktlint": test_task_startup_ktlint,
    "Kotlin/kotlinx.coroutines": test_task_startup_coroutines,
    "thunderbird/thunderbird-android": test_task_startup_thunderbird,
    "Kotlin/kotlinx-datetime": test_task_startup_datetime,
}


def get_test_func_for_repo(repo: str):
    """Get the appropriate test function for a repository."""
    # Handle short names
    if repo in REPO_SHORT_NAMES:
        repo = REPO_SHORT_NAMES[repo]
    return REPO_TO_TEST_FUNC.get(repo)


# =============================================================================
# Dataset Loading (local)
# =============================================================================

def load_tasks(repos: List[str] = None) -> List[TaskInstance]:
    """Load tasks from the Kotlin-bench dataset."""
    dataset_paths = [
        Path(__file__).parent.parent / "data" / "kotlin_bench.json",
        Path("agent-bench/data/kotlin_bench.json"),
    ]
    
    dataset_path = None
    for p in dataset_paths:
        if p.exists():
            dataset_path = p
            break
    
    if not dataset_path:
        print("Dataset not found!")
        return []
    
    with open(dataset_path) as f:
        all_tasks = json.load(f)
    
    # Resolve short names
    resolved_repos = None
    if repos:
        resolved_repos = [REPO_SHORT_NAMES.get(r, r) for r in repos]
    
    # Filter tasks
    if resolved_repos:
        tasks = [
            TaskInstance.from_dict(t)
            for t in all_tasks
            if t.get("repo") in resolved_repos
        ]
    else:
        tasks = [TaskInstance.from_dict(t) for t in all_tasks]
    
    return tasks


# =============================================================================
# Helpers
# =============================================================================

def print_result_summary(result: dict):
    """Print a summary of a single test result."""
    print("-" * 50)
    print(f"Task: {result.get('instance_id', 'unknown')}")
    print(f"  Repo: {result.get('repo', 'unknown')}")
    print(f"  Success: {result.get('success', False)}")
    print(f"  Total time: {result.get('total_time', 0):.1f}s")
    print(f"  Setup: {result.get('setup_duration', 0):.1f}s")
    if result.get('first_response_time'):
        print(f"  First response: {result['first_response_time']:.1f}s")
    if result.get('indexing_complete_time'):
        print(f"  Indexing complete: {result['indexing_complete_time']:.1f}s")
    if result.get('gradle_sync_complete_time'):
        print(f"  Gradle sync complete: {result['gradle_sync_complete_time']:.1f}s")
    if result.get('server_ready_time'):
        print(f"  Server ready: {result['server_ready_time']:.1f}s")
    if result.get('error'):
        print(f"  Error: {result['error']}")
    print("-" * 50)


def print_summary(all_results: List[dict]):
    """Print summary statistics."""
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    successful = [r for r in all_results if r.get('success')]
    failed = [r for r in all_results if not r.get('success')]
    
    print(f"Total tasks: {len(all_results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    
    if successful:
        times = [r['total_time'] for r in successful]
        ready_times = [r['server_ready_time'] for r in successful if r.get('server_ready_time')]
        
        print(f"\nTiming (successful runs):")
        print(f"  Total time: mean {statistics.mean(times):.1f}s, min {min(times):.1f}s, max {max(times):.1f}s")
        if ready_times:
            print(f"  Server ready: mean {statistics.mean(ready_times):.1f}s, min {min(ready_times):.1f}s, max {max(ready_times):.1f}s")
    
    if failed:
        print(f"\nFailed tasks:")
        for r in failed:
            print(f"  - {r.get('instance_id')}: {r.get('error', 'Unknown error')}")
    
    # Per-repo breakdown
    repos_seen = set(r.get('repo') for r in all_results)
    if len(repos_seen) > 1:
        print(f"\nPer-repo breakdown:")
        for repo in sorted(repos_seen):
            repo_results = [r for r in all_results if r.get('repo') == repo]
            repo_success = [r for r in repo_results if r.get('success')]
            if repo_success:
                times = [r['server_ready_time'] for r in repo_success if r.get('server_ready_time')]
                if times:
                    print(f"  {repo}: {len(repo_success)}/{len(repo_results)} success, mean ready time {statistics.mean(times):.1f}s")
                else:
                    print(f"  {repo}: {len(repo_success)}/{len(repo_results)} success")
            else:
                print(f"  {repo}: 0/{len(repo_results)} success")


# =============================================================================
# Entry Point
# =============================================================================

@app.local_entrypoint()
def main(
    task_id: str = None,
    task_ids: str = None,
    repo: str = None,
    repos: str = None,
    all_tasks: bool = False,
    list_tasks: bool = False,
    timeout: int = DEFAULT_TIMEOUT,
    poll_interval: int = DEFAULT_POLL_INTERVAL,
    parallel: bool = False,
    output: str = None,
):
    """
    Test agent server startup time for task instances.
    
    Args:
        task_id: Test a specific task by instance_id
        task_ids: Test multiple tasks (comma-separated)
        repo: Filter by repository (anki, ktlint, coroutines, etc.)
        repos: Filter by multiple repos (comma-separated)
        all_tasks: Test all tasks (for specified repos, or all if not specified)
        list_tasks: List available tasks
        timeout: Timeout in seconds for server ready (default: 600)
        poll_interval: Polling interval in seconds (default: 3)
        parallel: Run tests in parallel
        output: Output file for results JSON
    """
    print("=" * 70)
    print("AGENT SERVER STARTUP TIME TEST")
    print("=" * 70)
    
    # Parse repo list
    repo_list = []
    if repos:
        repo_list = [r.strip() for r in repos.split(",") if r.strip()]
    elif repo:
        repo_list = [repo]
    
    if repo_list:
        print(f"Repos: {', '.join(repo_list)}")
    
    # Load tasks
    tasks = load_tasks(repo_list if repo_list else None)
    
    if not tasks:
        print("No tasks found!")
        return
    
    print(f"Loaded {len(tasks)} tasks")
    
    # List tasks
    if list_tasks:
        print(f"\nAvailable Tasks ({len(tasks)} total):\n")
        
        tasks_by_repo: Dict[str, List] = {}
        for t in tasks:
            if t.repo not in tasks_by_repo:
                tasks_by_repo[t.repo] = []
            tasks_by_repo[t.repo].append(t)
        
        for repo_name, repo_tasks in sorted(tasks_by_repo.items()):
            print(f"  {repo_name} ({len(repo_tasks)} tasks):")
            for t in repo_tasks[:5]:
                print(f"    - {t.instance_id}")
            if len(repo_tasks) > 5:
                print(f"    ... and {len(repo_tasks) - 5} more")
            print()
        return
    
    # Select tasks to test
    selected_tasks = []
    
    if task_id:
        task = next((t for t in tasks if t.instance_id == task_id), None)
        if not task:
            # Try loading all tasks
            all_tasks_list = load_tasks(None)
            task = next((t for t in all_tasks_list if t.instance_id == task_id), None)
        if not task:
            print(f"Task not found: {task_id}")
            return
        selected_tasks = [task]
        
    elif task_ids:
        ids = [tid.strip() for tid in task_ids.split(",")]
        all_tasks_list = load_tasks(None)
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
        print("  modal run agent-bench/docker/test_server_startup.py --list-tasks [--repo <name>]")
        print("  modal run agent-bench/docker/test_server_startup.py --task-id <id>")
        print("  modal run agent-bench/docker/test_server_startup.py --task-ids <id1,id2,id3>")
        print("  modal run agent-bench/docker/test_server_startup.py --all-tasks [--repo <name>]")
        print("  modal run agent-bench/docker/test_server_startup.py --all-tasks --parallel")
        print("\nOptions:")
        print("  --repo <name>        Filter by repo (anki, ktlint, coroutines, datetime, thunderbird, wordpress)")
        print("  --repos <n1,n2>      Filter by multiple repos (comma-separated)")
        print("  --timeout <sec>      Timeout for server ready (default: 600)")
        print("  --poll-interval <s>  Poll interval (default: 3)")
        print("  --parallel           Run tests in parallel")
        print("  --output <file>      Save results to JSON file")
        return
    
    # Run tests
    print(f"\nTesting {len(selected_tasks)} task(s)")
    print(f"  Timeout: {timeout}s")
    print(f"  Poll interval: {poll_interval}s")
    print(f"  Parallel: {parallel}")
    print()
    
    results = []
    
    if parallel and len(selected_tasks) > 1:
        # Parallel execution
        print(f"Launching {len(selected_tasks)} tests in parallel...")
        
        futures = []
        for task in selected_tasks:
            test_func = get_test_func_for_repo(task.repo)
            if not test_func:
                print(f"  WARNING: No test function for repo {task.repo}")
                continue
            future = test_func.spawn(task.to_dict(), timeout=timeout, poll_interval=poll_interval)
            futures.append((task.instance_id, future))
        
        print(f"Waiting for {len(futures)} tests to complete...")
        for task_id, future in futures:
            try:
                result = future.get()
                results.append(result)
                print()
                print_result_summary(result)
            except Exception as e:
                print(f"ERROR: Test failed for {task_id}: {e}")
                results.append({
                    "success": False,
                    "instance_id": task_id,
                    "error": str(e),
                    "total_time": 0,
                })
    else:
        # Sequential execution
        for i, task in enumerate(selected_tasks):
            print(f"\n[{i+1}/{len(selected_tasks)}] {task.instance_id}")
            
            test_func = get_test_func_for_repo(task.repo)
            if not test_func:
                print(f"  WARNING: No test function for repo {task.repo}")
                continue
            
            result = test_func.remote(task.to_dict(), timeout=timeout, poll_interval=poll_interval)
            results.append(result)
            print()
            print_result_summary(result)
    
    # Print summary
    print_summary(results)
    
    # Save results
    if output:
        output_file = output
    else:
        output_file = f"startup_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {output_file}")
