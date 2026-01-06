"""
Build kotlinx.coroutines Pre-baked Docker Image on Modal

The Dockerfile reads config from agent-bench/config/coroutines.json (single source of truth).
Install script runs AFTER clone, BEFORE warmupProject.

Usage:
    modal run docker/coroutines-prebaked/build_modal.py
    modal run docker/coroutines-prebaked/build_modal.py::benchmark_startup
"""

import modal
import os
import sys
from pathlib import Path

# Add agent-bench to path to import constants
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agent-bench"))
from constants import load_repo_config, FIREBENDER_BRANCH, PROJECT_PATH

# Load coroutines config
COROUTINES_CONFIG = load_repo_config("coroutines")
COROUTINES_JDK_VERSION = COROUTINES_CONFIG.get("jdk_version", "11.0.20-tem")
COROUTINES_BASE_COMMIT = COROUTINES_CONFIG.get("base_commit", "")

# =============================================================================
# Configuration
# =============================================================================

app = modal.App("coroutines-prebaked-builder")

_github_token = os.environ.get("GITHUB_TOKEN", "")
if not _github_token:
    print("WARNING: GITHUB_TOKEN not set. Build will fail.")

# Build image from Dockerfile (which reads from config/coroutines.json)
coroutines_image = modal.Image.from_dockerfile(
    path="docker/coroutines-prebaked/Dockerfile",
    context_dir=".",
    add_python="3.11",
    build_args={
        "GITHUB_TOKEN": _github_token,
        "FIREBENDER_BRANCH": os.environ.get("FIREBENDER_BRANCH", FIREBENDER_BRANCH),
    },
)


# =============================================================================
# Build Functions
# =============================================================================

@app.function(image=coroutines_image, timeout=1800, cpu=4, memory=16384)
def verify_build() -> dict:
    """Verify the built image."""
    import subprocess
    
    print("=" * 60)
    print("Verifying kotlinx.coroutines Pre-baked Image")
    print("=" * 60)
    
    checks = {}
    
    checks["project_exists"] = os.path.exists("/project/gradlew")
    print(f"  /project/gradlew: {checks['project_exists']}")
    
    checks["firebender_exists"] = os.path.exists("/firebender/gradlew")
    print(f"  /firebender/gradlew: {checks['firebender_exists']}")
    
    checks["config_exists"] = os.path.exists("/config/coroutines.json")
    print(f"  /config/coroutines.json: {checks['config_exists']}")
    
    result = subprocess.run(["java", "-version"], capture_output=True, text=True)
    checks["java_works"] = result.returncode == 0
    print(f"  Java works: {checks['java_works']}")
    
    result = subprocess.run(["uname", "-m"], capture_output=True, text=True)
    checks["arch"] = result.stdout.strip()
    print(f"  Architecture: {checks['arch']}")
    
    jdk_path = f"/root/.sdkman/candidates/java/{COROUTINES_JDK_VERSION}"
    checks["sdkman_jdk"] = os.path.exists(jdk_path)
    print(f"  SDKMAN JDK ({COROUTINES_JDK_VERSION}): {checks['sdkman_jdk']}")
    
    all_passed = all([
        checks["project_exists"],
        checks["firebender_exists"],
        checks["config_exists"],
        checks["java_works"],
        checks["sdkman_jdk"],
    ])
    
    print("=" * 60)
    print(f"All checks: {'PASSED' if all_passed else 'FAILED'}")
    print("=" * 60)
    
    return {"success": all_passed, "checks": checks}


@app.function(image=coroutines_image, timeout=900, cpu=8, memory=16384)
def benchmark_startup() -> dict:
    """Benchmark agent server startup time."""
    import subprocess
    import time
    import urllib.request
    import urllib.error
    import json
    
    PORT = 8742
    TIMEOUT = 600
    
    print("=" * 60)
    print("Benchmarking Agent Server Startup")
    print("=" * 60)
    
    start_time = time.time()
    
    env = os.environ.copy()
    env["DISPLAY"] = ":99"
    env["_JAVA_OPTIONS"] = "-Djb.consents.confirmation.enabled=false -Djb.privacy.policy.text=<!--999.999--> -Didea.initially.ask.config=false -Dide.no.splash=true -Dnosplash=true -Dhidpi=false -Dsun.java2d.uiScale.enabled=false -Dsun.java2d.uiScale=1.0 -Dide.ui.scale=1.0 -Dsun.java2d.xrender=false"
    
    cmd = [
        "xvfb-run", "-a", "-s", "-screen 0 1920x1080x24",
        "./gradlew", "runAgentServer",
        f"-PprojectPath={PROJECT_PATH}",
        "-PskipObfuscation=true",
        "--no-daemon",
        "--no-configuration-cache",
    ]
    
    print("Starting agent server...")
    process = subprocess.Popen(
        cmd, cwd="/firebender", env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    
    ready = False
    last_msg = ""
    
    while time.time() - start_time < TIMEOUT:
        elapsed = time.time() - start_time
        try:
            req = urllib.request.Request(f"http://localhost:{PORT}/ready")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                if data.get("ready"):
                    ready = True
                    break
                msg = data.get("message", "")
                if msg != last_msg:
                    print(f"  [{elapsed:.0f}s] {msg}")
                    last_msg = msg
        except urllib.error.HTTPError as e:
            if e.code == 503:
                try:
                    data = json.loads(e.read().decode())
                    msg = data.get("message", "")
                    if msg != last_msg:
                        print(f"  [{elapsed:.0f}s] {msg}")
                        last_msg = msg
                except:
                    pass
        except:
            if int(elapsed) % 30 == 0:
                print(f"  [{elapsed:.0f}s] Waiting...")
        time.sleep(3)
    
    total_time = time.time() - start_time
    
    process.terminate()
    try:
        process.wait(timeout=10)
    except:
        process.kill()
    
    print("=" * 60)
    print(f"Success: {ready}")
    print(f"Time: {total_time:.1f}s")
    print("=" * 60)
    
    return {"success": ready, "startup_time_seconds": round(total_time, 1)}


@app.local_entrypoint()
def main(verify: bool = True, benchmark: bool = False):
    """Build the kotlinx.coroutines pre-baked image."""
    print("=" * 60)
    print("Building kotlinx.coroutines Pre-baked Image")
    print("=" * 60)
    print(f"  Config: agent-bench/config/coroutines.json")
    print(f"  JDK: {COROUTINES_JDK_VERSION}")
    print(f"  Commit: {COROUTINES_BASE_COMMIT[:8] if COROUTINES_BASE_COMMIT else 'N/A'}")
    print("=" * 60)
    
    if verify:
        print("\nVerifying...")
        result = verify_build.remote()
        print(f"Result: {'PASSED' if result['success'] else 'FAILED'}")
        if not result['success']:
            return
    
    if benchmark:
        print("\nBenchmarking...")
        result = benchmark_startup.remote()
        print(f"Startup: {result['startup_time_seconds']}s")
    
    print("\nDone! Image cached on Modal.")
