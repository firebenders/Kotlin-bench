"""
Firebender Agent Sandbox for Modal

This module provides a sandbox environment for running the Firebender IntelliJ agent
headlessly on Modal. It uses Xvfb to provide a virtual display so IntelliJ can run
without losing any functionality.

Usage:
    modal run swebench/harness/firebender_sandbox_modal.py
"""

import json
import time
from typing import Dict, Any, Optional

import modal

# Modal configuration
AGENT_SERVER_PORT = 8742
DISPLAY_NUM = 99
SCREEN_RESOLUTION = "1920x1080x24"

# Base image with all required dependencies
base_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install([
        # Core utilities
        "git",
        "curl",
        "wget",
        "unzip",
        "ca-certificates",
        # X11 and virtual display
        "xvfb",
        "x11-xserver-utils",
        "libx11-6",
        "libxext6",
        "libxrender1",
        "libxtst6",
        "libxi6",
        "libxrandr2",
        # Fonts (required for IntelliJ UI rendering)
        "fontconfig",
        "fonts-dejavu",
        "fonts-liberation",
        # Additional libs IntelliJ might need
        "libfontconfig1",
        "libfreetype6",
        "libpng16-16",
        "libasound2",
        "libatk1.0-0",
        "libatk-bridge2.0-0",
        "libcairo2",
        "libcups2",
        "libdbus-1-3",
        "libdrm2",
        "libgbm1",
        "libgdk-pixbuf2.0-0",
        "libgtk-3-0",
        "libnspr4",
        "libnss3",
        "libpango-1.0-0",
        "libxcomposite1",
        "libxcursor1",
        "libxdamage1",
        "libxfixes3",
        "libxkbcommon0",
        "libxshmfence1",
        # Java (IntelliJ comes bundled with JBR, but we need JDK for Gradle)
        "openjdk-17-jdk",
        # Process management
        "procps",
        "htop",
    ])
    .pip_install([
        "requests",
        "httpx",
    ])
    .run_commands([
        # Set JAVA_HOME
        "echo 'export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64' >> /etc/profile",
        "echo 'export PATH=$JAVA_HOME/bin:$PATH' >> /etc/profile",
    ])
)

# Create Modal app
app = modal.App("firebender-sandbox", image=base_image)

# Volumes for persistence
firebender_volume = modal.Volume.from_name("firebender-plugin-volume", create_if_missing=True)
logs_volume = modal.Volume.from_name("firebender-logs-volume", create_if_missing=True)


@app.function(
    volumes={
        "/firebender": firebender_volume,
        "/logs": logs_volume,
    },
    timeout=300,
)
def clone_firebender_repo(branch: str = "aman/firebender-harness", force_reclone: bool = False) -> Dict[str, Any]:
    """
    Clone the Firebender plugin repository.
    
    Args:
        branch: Git branch to checkout
        force_reclone: If True, delete existing repo and clone fresh
        
    Returns:
        Dict with status and repo path
    """
    import os
    import subprocess
    
    repo_url = "https://github.com/firebenders/android-studio-copilot.git"
    repo_path = "/firebender/android-studio-copilot"
    
    # Check if repo already exists
    if os.path.exists(os.path.join(repo_path, ".git")):
        if force_reclone:
            print(f"Force reclone requested, removing existing repo at {repo_path}")
            subprocess.run(["rm", "-rf", repo_path], check=True)
        else:
            # Update existing repo
            print(f"Repository already exists at {repo_path}, updating...")
            os.chdir(repo_path)
            subprocess.run(["git", "fetch", "--all"], check=True)
            subprocess.run(["git", "checkout", branch], check=True)
            subprocess.run(["git", "pull", "origin", branch], check=False)
            return {
                "status": "updated",
                "repo_path": repo_path,
                "branch": branch,
            }
    
    # Clone the repository
    print(f"Cloning {repo_url} (branch: {branch})...")
    os.makedirs(os.path.dirname(repo_path), exist_ok=True)
    
    subprocess.run([
        "git", "clone",
        "--branch", branch,
        "--single-branch",
        repo_url,
        repo_path
    ], check=True)
    
    # Make gradlew executable
    gradlew_path = os.path.join(repo_path, "gradlew")
    if os.path.exists(gradlew_path):
        subprocess.run(["chmod", "+x", gradlew_path], check=True)
    
    return {
        "status": "cloned",
        "repo_path": repo_path,
        "branch": branch,
    }


@app.function(
    volumes={
        "/firebender": firebender_volume,
        "/logs": logs_volume,
    },
    timeout=3600,  # 1 hour for long-running IDE
    cpu=4.0,
    memory=16384,  # 16GB RAM for IDE
)
def start_ide_with_agent_server(
    project_path: Optional[str] = None,
    timeout_seconds: int = 300,
) -> Dict[str, Any]:
    """
    Start IntelliJ IDE with the Firebender agent server enabled.
    
    This function:
    1. Starts Xvfb for virtual display
    2. Runs `./gradlew runIde` with agent server env vars
    3. Waits for the agent server to be ready
    4. Returns connection info
    
    Args:
        project_path: Optional path to a project to open in the IDE
        timeout_seconds: How long to wait for IDE to start
        
    Returns:
        Dict with status and connection info
    """
    import os
    import subprocess
    import socket
    import requests
    
    repo_path = "/firebender/android-studio-copilot"
    log_file = f"/logs/ide_startup_{int(time.time())}.log"
    
    # Verify repo exists
    if not os.path.exists(repo_path):
        return {
            "status": "error",
            "error": f"Repository not found at {repo_path}. Run clone_firebender_repo first.",
        }
    
    os.chdir(repo_path)
    
    # Start Xvfb (X Virtual Framebuffer)
    print(f"Starting Xvfb on display :{DISPLAY_NUM}...")
    xvfb_cmd = [
        "Xvfb",
        f":{DISPLAY_NUM}",
        "-screen", "0", SCREEN_RESOLUTION,
        "-ac",  # Disable access control
        "-nolisten", "tcp",  # Security: no TCP connections
    ]
    
    xvfb_process = subprocess.Popen(
        xvfb_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # Give Xvfb a moment to start
    time.sleep(2)
    
    # Check if Xvfb is running
    if xvfb_process.poll() is not None:
        stdout, stderr = xvfb_process.communicate()
        return {
            "status": "error",
            "error": f"Xvfb failed to start: {stderr.decode()}",
        }
    
    print(f"Xvfb started (PID: {xvfb_process.pid})")
    
    # Set environment for IDE
    env = os.environ.copy()
    env["DISPLAY"] = f":{DISPLAY_NUM}"
    env["FIREBENDER_AGENT_SERVER"] = "true"
    env["FIREBENDER_AGENT_SERVER_PORT"] = str(AGENT_SERVER_PORT)
    env["JAVA_HOME"] = "/usr/lib/jvm/java-17-openjdk-amd64"
    env["PATH"] = f"{env['JAVA_HOME']}/bin:{env.get('PATH', '')}"
    
    # Optional: Set project path if provided
    if project_path:
        env["FIREBENDER_PROJECT_PATH"] = project_path
    
    # Start the IDE with agent server
    print(f"Starting IDE with agent server on port {AGENT_SERVER_PORT}...")
    
    with open(log_file, "w") as log_f:
        ide_process = subprocess.Popen(
            ["./gradlew", "runIde", "--no-daemon"],
            env=env,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            cwd=repo_path,
        )
    
    print(f"IDE process started (PID: {ide_process.pid})")
    
    # Wait for agent server to be ready
    start_time = time.time()
    server_ready = False
    
    print(f"Waiting for agent server to be ready (timeout: {timeout_seconds}s)...")
    
    while time.time() - start_time < timeout_seconds:
        # Check if IDE process is still running
        if ide_process.poll() is not None:
            with open(log_file, "r") as f:
                log_content = f.read()
            return {
                "status": "error",
                "error": f"IDE process exited unexpectedly with code {ide_process.returncode}",
                "log": log_content[-5000:] if len(log_content) > 5000 else log_content,
            }
        
        # Try to connect to agent server
        try:
            response = requests.get(
                f"http://localhost:{AGENT_SERVER_PORT}/health",
                timeout=2,
            )
            if response.status_code == 200:
                server_ready = True
                break
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(5)
        elapsed = int(time.time() - start_time)
        print(f"Waiting... ({elapsed}s elapsed)")
    
    if not server_ready:
        # Read log file for debugging
        with open(log_file, "r") as f:
            log_content = f.read()
        
        return {
            "status": "timeout",
            "error": f"Agent server did not become ready within {timeout_seconds}s",
            "log": log_content[-5000:] if len(log_content) > 5000 else log_content,
            "ide_pid": ide_process.pid,
            "xvfb_pid": xvfb_process.pid,
        }
    
    return {
        "status": "ready",
        "agent_server_port": AGENT_SERVER_PORT,
        "ide_pid": ide_process.pid,
        "xvfb_pid": xvfb_process.pid,
        "log_file": log_file,
    }


@app.function(
    volumes={
        "/firebender": firebender_volume,
        "/logs": logs_volume,
    },
    timeout=600,
)
def run_agent_query(
    query: str,
    timeout_seconds: int = 300,
) -> Dict[str, Any]:
    """
    Run a query through the Firebender agent.
    
    Args:
        query: The query/task to send to the agent
        timeout_seconds: Timeout for the agent to complete
        
    Returns:
        Dict with agent response
    """
    import requests
    
    url = f"http://localhost:{AGENT_SERVER_PORT}/agent/run"
    
    try:
        response = requests.post(
            url,
            json={"query": query},
            headers={"Content-Type": "application/json"},
            timeout=timeout_seconds,
        )
        
        return {
            "status": "success",
            "response": response.json(),
            "status_code": response.status_code,
        }
    except requests.exceptions.Timeout:
        return {
            "status": "timeout",
            "error": f"Agent query timed out after {timeout_seconds}s",
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "error": str(e),
        }


@app.function(
    volumes={
        "/firebender": firebender_volume,
        "/logs": logs_volume,
    },
    timeout=3600,
    cpu=4.0,
    memory=16384,
)
def sandbox_test(
    query: str = "What files are in this project?",
    ide_startup_timeout: int = 300,
    query_timeout: int = 120,
) -> Dict[str, Any]:
    """
    Complete sandbox test: clone repo, start IDE, run a test query.
    
    This is the main entry point for iterating on the sandbox.
    
    Args:
        query: Test query to send to the agent
        ide_startup_timeout: Timeout waiting for IDE to start
        query_timeout: Timeout for the agent query
        
    Returns:
        Dict with full test results
    """
    import os
    import subprocess
    import requests
    
    results = {
        "steps": [],
        "success": False,
    }
    
    repo_path = "/firebender/android-studio-copilot"
    
    # Step 1: Clone/update repo
    print("=" * 50)
    print("Step 1: Clone/update Firebender repository")
    print("=" * 50)
    
    try:
        clone_result = clone_firebender_repo.local(branch="aman/firebender-harness")
        results["steps"].append({
            "step": "clone_repo",
            "status": "success",
            "result": clone_result,
        })
        print(f"Repository ready: {clone_result}")
    except Exception as e:
        results["steps"].append({
            "step": "clone_repo",
            "status": "error",
            "error": str(e),
        })
        return results
    
    # Step 2: Start Xvfb
    print("\n" + "=" * 50)
    print("Step 2: Start Xvfb virtual display")
    print("=" * 50)
    
    xvfb_cmd = [
        "Xvfb",
        f":{DISPLAY_NUM}",
        "-screen", "0", SCREEN_RESOLUTION,
        "-ac",
        "-nolisten", "tcp",
    ]
    
    xvfb_process = subprocess.Popen(
        xvfb_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2)
    
    if xvfb_process.poll() is not None:
        stdout, stderr = xvfb_process.communicate()
        results["steps"].append({
            "step": "start_xvfb",
            "status": "error",
            "error": stderr.decode(),
        })
        return results
    
    results["steps"].append({
        "step": "start_xvfb",
        "status": "success",
        "pid": xvfb_process.pid,
        "display": f":{DISPLAY_NUM}",
    })
    print(f"Xvfb started on display :{DISPLAY_NUM} (PID: {xvfb_process.pid})")
    
    # Step 3: Start IDE with agent server
    print("\n" + "=" * 50)
    print("Step 3: Start IntelliJ IDE with agent server")
    print("=" * 50)
    
    os.chdir(repo_path)
    
    env = os.environ.copy()
    env["DISPLAY"] = f":{DISPLAY_NUM}"
    env["FIREBENDER_AGENT_SERVER"] = "true"
    env["FIREBENDER_AGENT_SERVER_PORT"] = str(AGENT_SERVER_PORT)
    env["JAVA_HOME"] = "/usr/lib/jvm/java-17-openjdk-amd64"
    env["PATH"] = f"{env['JAVA_HOME']}/bin:{env.get('PATH', '')}"
    
    log_file = f"/logs/sandbox_test_{int(time.time())}.log"
    
    with open(log_file, "w") as log_f:
        ide_process = subprocess.Popen(
            ["./gradlew", "runIde", "--no-daemon"],
            env=env,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            cwd=repo_path,
        )
    
    print(f"IDE process started (PID: {ide_process.pid})")
    print(f"Logs at: {log_file}")
    
    # Wait for agent server
    start_time = time.time()
    server_ready = False
    
    print(f"Waiting for agent server on port {AGENT_SERVER_PORT}...")
    
    while time.time() - start_time < ide_startup_timeout:
        if ide_process.poll() is not None:
            with open(log_file, "r") as f:
                log_content = f.read()
            results["steps"].append({
                "step": "start_ide",
                "status": "error",
                "error": f"IDE exited with code {ide_process.returncode}",
                "log_tail": log_content[-3000:],
            })
            xvfb_process.terminate()
            return results
        
        try:
            # Try health endpoint first, then root
            for endpoint in ["/health", "/"]:
                try:
                    response = requests.get(
                        f"http://localhost:{AGENT_SERVER_PORT}{endpoint}",
                        timeout=2,
                    )
                    if response.status_code in [200, 404]:  # 404 means server is up but endpoint doesn't exist
                        server_ready = True
                        break
                except:
                    pass
            if server_ready:
                break
        except:
            pass
        
        elapsed = int(time.time() - start_time)
        if elapsed % 30 == 0:
            print(f"Still waiting... ({elapsed}s elapsed)")
        time.sleep(5)
    
    if not server_ready:
        with open(log_file, "r") as f:
            log_content = f.read()
        results["steps"].append({
            "step": "start_ide",
            "status": "timeout",
            "error": f"Agent server not ready after {ide_startup_timeout}s",
            "log_tail": log_content[-3000:],
        })
        ide_process.terminate()
        xvfb_process.terminate()
        return results
    
    results["steps"].append({
        "step": "start_ide",
        "status": "success",
        "ide_pid": ide_process.pid,
        "agent_port": AGENT_SERVER_PORT,
    })
    print(f"Agent server is ready on port {AGENT_SERVER_PORT}")
    
    # Step 4: Run test query
    print("\n" + "=" * 50)
    print(f"Step 4: Run agent query: '{query}'")
    print("=" * 50)
    
    try:
        response = requests.post(
            f"http://localhost:{AGENT_SERVER_PORT}/agent/run",
            json={"query": query},
            headers={"Content-Type": "application/json"},
            timeout=query_timeout,
        )
        
        results["steps"].append({
            "step": "run_query",
            "status": "success",
            "query": query,
            "response": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
            "status_code": response.status_code,
        })
        results["success"] = True
        print(f"Query completed successfully!")
        print(f"Response: {response.text[:500]}...")
        
    except requests.exceptions.Timeout:
        results["steps"].append({
            "step": "run_query",
            "status": "timeout",
            "query": query,
            "error": f"Query timed out after {query_timeout}s",
        })
    except Exception as e:
        results["steps"].append({
            "step": "run_query",
            "status": "error",
            "query": query,
            "error": str(e),
        })
    
    # Cleanup
    print("\n" + "=" * 50)
    print("Cleanup")
    print("=" * 50)
    
    ide_process.terminate()
    xvfb_process.terminate()
    print("Processes terminated")
    
    # Save results
    results_file = f"/logs/sandbox_results_{int(time.time())}.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    results["results_file"] = results_file
    
    return results


@app.local_entrypoint()
def main(
    query: str = "List the files in the src directory",
    ide_timeout: int = 300,
    query_timeout: int = 120,
):
    """
    Main entrypoint for the Firebender sandbox.
    
    Usage:
        modal run swebench/harness/firebender_sandbox_modal.py
        modal run swebench/harness/firebender_sandbox_modal.py --query "Add logs to AutocompleteCache.kt"
    """
    print("=" * 60)
    print("Firebender Agent Sandbox")
    print("=" * 60)
    print(f"Query: {query}")
    print(f"IDE Timeout: {ide_timeout}s")
    print(f"Query Timeout: {query_timeout}s")
    print("=" * 60)
    
    result = sandbox_test.remote(
        query=query,
        ide_startup_timeout=ide_timeout,
        query_timeout=query_timeout,
    )
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(json.dumps(result, indent=2))
    
    return result
