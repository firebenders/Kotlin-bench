"""
Quick test to verify terminal commands work in the agent server.

Usage:
    modal run agent-bench/docker/test_terminal_cmd.py
"""

import modal
import os
import subprocess
import time
import json
import urllib.request
import urllib.error
from pathlib import Path

# Config
AGENT_PORT = 8742
FIREBENDER_PLUGIN_ZIP = "firebender/Firebender.zip"
IDEA_PLUGINS_DIR = "/root/.local/share/JetBrains/IdeaIC2025.1"
PROJECT_PATH = "/project"

# Use ktlint image (smallest/fastest)
image = (
    modal.Image.from_dockerfile(
        path="agent-bench/docker/generated/Dockerfile.ktlint",
        context_dir=".",
        add_python="3.11",
    )
    .add_local_file(FIREBENDER_PLUGIN_ZIP, "/tmp/Firebender.zip", copy=True)
)

app = modal.App("test-terminal-cmd")


def install_plugin() -> bool:
    """Install Firebender plugin."""
    plugin_zip = "/tmp/Firebender.zip"
    os.makedirs(IDEA_PLUGINS_DIR, exist_ok=True)
    
    result = subprocess.run(
        ["unzip", "-o", plugin_zip, "-d", IDEA_PLUGINS_DIR],
        capture_output=True, text=True
    )
    return result.returncode == 0


def start_server(log_file: str) -> subprocess.Popen:
    """Start IDE with agent server."""
    env = os.environ.copy()
    
    # Source SDKMAN for Java
    sdkman_init = "/root/.sdkman/bin/sdkman-init.sh"
    if os.path.exists(sdkman_init):
        result = subprocess.run(
            f"source {sdkman_init} && echo $JAVA_HOME",
            shell=True, capture_output=True, text=True, executable="/bin/bash"
        )
        java_home = result.stdout.strip()
        if java_home:
            env["JAVA_HOME"] = java_home
            env["PATH"] = f"{java_home}/bin:" + env.get("PATH", "")
    
    bypass_key = "firebender-bypass-auth-2025"
    env["FIREBENDER_AGENT_SERVER"] = "true"
    env["FIREBENDER_AGENT_SERVER_PORT"] = str(AGENT_PORT)
    env["FIREBENDER_ANDROID_PROJECT"] = "false"
    env["FIREBENDER_BYPASS_AUTH_KEY"] = bypass_key
    env["DISPLAY"] = ":99"
    
    env["_JAVA_OPTIONS"] = " ".join([
        "-Dfirebender.agentServer=true",
        f"-Dfirebender.agentServerPort={AGENT_PORT}",
        "-Dfirebender.androidProject=false",
        f"-Dfirebender.bypassAuthKey={bypass_key}",
        "-Djb.consents.confirmation.enabled=false",
        '-Djb.privacy.policy.text="<!--999.999-->"',
        "-Didea.initially.ask.config=false",
        "-Dide.no.splash=true",
    ])
    
    cmd = [
        "xvfb-run", "-a", "-s", "-screen 0 1920x1080x24",
        "env",
        f"FIREBENDER_AGENT_SERVER=true",
        f"FIREBENDER_AGENT_SERVER_PORT={AGENT_PORT}",
        f"FIREBENDER_ANDROID_PROJECT=false",
        f"FIREBENDER_BYPASS_AUTH_KEY={bypass_key}",
        "/opt/idea/bin/idea.sh", PROJECT_PATH,
    ]
    
    log_handle = open(log_file, "w")
    return subprocess.Popen(cmd, cwd=PROJECT_PATH, env=env, stdout=log_handle, stderr=subprocess.STDOUT, text=True)


def wait_for_ready(timeout: int = 600) -> bool:
    """Wait for server to be ready."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f"http://localhost:{AGENT_PORT}/ready")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                if data.get("ready"):
                    return True
        except:
            pass
        time.sleep(5)
    return False


def send_agent_request(query: str, model: str = "claude-sonnet-4-20250514") -> dict:
    """Send request to agent."""
    url = f"http://localhost:{AGENT_PORT}/agent/run"
    data = json.dumps({
        "query": query,
        "model": model,
        "includeIntellijGuidance": True,
    }).encode("utf-8")
    
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}


@app.function(image=image, timeout=1800, cpu=4, memory=16384, secrets=[modal.Secret.from_name("github-token")])
def test_terminal_command() -> dict:
    """Test that terminal commands work."""
    print("=" * 60)
    print("TERMINAL COMMAND TEST")
    print("=" * 60)
    
    # Install plugin
    print("\n1. Installing Firebender plugin...")
    if not install_plugin():
        return {"error": "Failed to install plugin"}
    print("   Done!")
    
    # Start server
    print("\n2. Starting IDE...")
    log_file = "/tmp/ide_test.log"
    process = start_server(log_file)
    print(f"   PID: {process.pid}")
    
    # Wait for ready
    print("\n3. Waiting for server to be ready...")
    if not wait_for_ready(timeout=600):
        process.terminate()
        return {"error": "Server didn't become ready"}
    print("   Server is ready!")
    
    # Send test request
    print("\n4. Sending agent request to run terminal command...")
    query = """Please run this terminal command and tell me the output:

```
ls -la /project | head -20
```

Just run this one command and show me what it outputs."""

    print(f"   Query: {query[:100]}...")
    
    response = send_agent_request(query)
    
    # Cleanup
    print("\n5. Cleaning up...")
    process.terminate()
    try:
        process.wait(timeout=10)
    except:
        process.kill()
    
    # Results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    if "error" in response:
        print(f"ERROR: {response['error']}")
    else:
        print(f"Success: {response.get('success', 'unknown')}")
        print(f"\nAgent Response:")
        # Print the response content
        if "response" in response:
            print(response["response"][:2000] if len(str(response.get("response", ""))) > 2000 else response.get("response"))
        else:
            print(json.dumps(response, indent=2, default=str)[:3000])
    
    return response


@app.local_entrypoint()
def main():
    """Run the terminal command test."""
    result = test_terminal_command.remote()
    
    print("\n" + "=" * 60)
    print("FINAL RESULT (returned from Modal)")
    print("=" * 60)
    print(json.dumps(result, indent=2, default=str)[:5000])
