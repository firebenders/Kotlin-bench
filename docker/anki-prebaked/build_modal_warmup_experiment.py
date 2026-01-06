"""
Build Anki-Android Pre-baked Docker Image on Modal (Warmup Experiment)

This version uses Android Studio's native warmup command instead of 
Firebender's warmupProject gradle task. The Firebender plugin is 
bundled at runtime, allowing faster iteration.

The Dockerfile reads config from agent-bench/config/anki.json.

Usage:
    modal run docker/anki-prebaked/build_modal_warmup_experiment.py
    modal run docker/anki-prebaked/build_modal_warmup_experiment.py::verify_build
"""

import modal
import os
import sys
from pathlib import Path

# Add agent-bench to path to import constants
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agent-bench"))
from constants import ANKI_JDK_VERSION, ANKI_BASE_COMMIT, PROJECT_PATH

# =============================================================================
# Configuration
# =============================================================================

app = modal.App("anki-warmup-experiment-builder")

# Build image from experimental Dockerfile (no GITHUB_TOKEN needed!)
anki_image = modal.Image.from_dockerfile(
    path="docker/anki-prebaked/Dockerfile.warmup-experiment",
    context_dir=".",
    add_python="3.11",
)


# =============================================================================
# Build Functions
# =============================================================================

@app.function(image=anki_image, timeout=1800, cpu=4, memory=16384)
def verify_build() -> dict:
    """Verify the built image."""
    import subprocess
    
    print("=" * 60)
    print("Verifying Anki Warmup Experiment Image")
    print("=" * 60)
    
    checks = {}
    
    # Check project exists
    checks["project_exists"] = os.path.exists("/project/gradlew")
    print(f"  /project/gradlew: {checks['project_exists']}")
    
    # Check config exists
    checks["config_exists"] = os.path.exists("/config/anki.json")
    print(f"  /config/anki.json: {checks['config_exists']}")
    
    # Check Android Studio installation
    checks["android_studio_exists"] = os.path.exists("/opt/android-studio/bin/studio.sh")
    print(f"  Android Studio: {checks['android_studio_exists']}")
    
    # Check Java works
    result = subprocess.run(["java", "-version"], capture_output=True, text=True)
    checks["java_works"] = result.returncode == 0
    print(f"  Java works: {checks['java_works']}")
    
    # Check architecture
    result = subprocess.run(["uname", "-m"], capture_output=True, text=True)
    checks["arch"] = result.stdout.strip()
    print(f"  Architecture: {checks['arch']}")
    
    # Check SDKMAN JDK
    jdk_path = f"/root/.sdkman/candidates/java/{ANKI_JDK_VERSION}"
    checks["sdkman_jdk"] = os.path.exists(jdk_path)
    print(f"  SDKMAN JDK ({ANKI_JDK_VERSION}): {checks['sdkman_jdk']}")
    
    # Check Android SDK
    checks["android_sdk"] = os.path.exists("/root/android-sdk/platform-tools")
    print(f"  Android SDK: {checks['android_sdk']}")
    
    # Check Gradle caches were populated
    gradle_cache = "/root/.gradle/caches"
    if os.path.exists(gradle_cache):
        cache_size = sum(
            os.path.getsize(os.path.join(dirpath, filename))
            for dirpath, _, filenames in os.walk(gradle_cache)
            for filename in filenames
        ) / (1024 * 1024)  # MB
        checks["gradle_cache_mb"] = round(cache_size, 1)
        checks["gradle_cache_populated"] = cache_size > 100  # Should be > 100MB
    else:
        checks["gradle_cache_populated"] = False
        checks["gradle_cache_mb"] = 0
    print(f"  Gradle cache: {checks['gradle_cache_mb']} MB")
    
    # Check project .gradle directory
    project_gradle = "/project/.gradle"
    checks["project_gradle_exists"] = os.path.exists(project_gradle)
    print(f"  Project .gradle/: {checks['project_gradle_exists']}")
    
    # Check IDE caches (Linux path)
    ide_cache_base = "/root/.cache/Google"
    if os.path.exists(ide_cache_base):
        ide_cache_dirs = os.listdir(ide_cache_base)
        checks["ide_cache_dirs"] = ide_cache_dirs
        checks["ide_cache_exists"] = len(ide_cache_dirs) > 0
    else:
        checks["ide_cache_exists"] = False
        checks["ide_cache_dirs"] = []
    print(f"  IDE caches: {checks['ide_cache_dirs']}")
    
    all_passed = all([
        checks["project_exists"],
        checks["config_exists"],
        checks["android_studio_exists"],
        checks["java_works"],
        checks["sdkman_jdk"],
        checks["android_sdk"],
        checks["gradle_cache_populated"],
    ])
    
    print("=" * 60)
    print(f"All checks: {'PASSED' if all_passed else 'FAILED'}")
    print("=" * 60)
    
    return {"success": all_passed, "checks": checks}


@app.function(image=anki_image, timeout=300, cpu=4, memory=16384)
def check_caches() -> dict:
    """Detailed check of all warmed-up caches."""
    import subprocess
    
    print("=" * 60)
    print("Cache Analysis")
    print("=" * 60)
    
    caches = {}
    
    # Gradle caches
    print("\n--- Gradle Caches ---")
    result = subprocess.run(
        ["du", "-sh", "/root/.gradle/caches"],
        capture_output=True, text=True
    )
    caches["gradle_caches"] = result.stdout.strip()
    print(f"  ~/.gradle/caches: {result.stdout.strip()}")
    
    # Project .gradle
    print("\n--- Project Cache ---")
    result = subprocess.run(
        ["du", "-sh", "/project/.gradle"],
        capture_output=True, text=True
    )
    caches["project_gradle"] = result.stdout.strip()
    print(f"  /project/.gradle: {result.stdout.strip()}")
    
    # IDE caches
    print("\n--- IDE Caches ---")
    ide_cache = "/root/.cache/Google"
    if os.path.exists(ide_cache):
        result = subprocess.run(
            ["du", "-sh", ide_cache],
            capture_output=True, text=True
        )
        caches["ide_cache"] = result.stdout.strip()
        print(f"  ~/.cache/Google: {result.stdout.strip()}")
        
        # List subdirectories
        for item in os.listdir(ide_cache):
            item_path = os.path.join(ide_cache, item)
            result = subprocess.run(
                ["du", "-sh", item_path],
                capture_output=True, text=True
            )
            print(f"    {item}: {result.stdout.strip().split()[0]}")
    else:
        caches["ide_cache"] = "NOT FOUND"
        print(f"  ~/.cache/Google: NOT FOUND")
    
    # IDE config
    print("\n--- IDE Config ---")
    ide_config = "/root/.config/Google"
    if os.path.exists(ide_config):
        for item in os.listdir(ide_config):
            print(f"    {item}")
    else:
        print("  ~/.config/Google: NOT FOUND")
    
    return caches


@app.local_entrypoint()
def main(verify: bool = True, check_cache: bool = False):
    """Build the Anki warmup experiment image."""
    print("=" * 60)
    print("Building Anki Warmup Experiment Image")
    print("=" * 60)
    print("  This uses Android Studio's native warmup command")
    print("  No Firebender repo clone needed!")
    print(f"  Config: agent-bench/config/anki.json")
    print(f"  JDK: {ANKI_JDK_VERSION}")
    print(f"  Commit: {ANKI_BASE_COMMIT[:8]}")
    print("=" * 60)
    
    if verify:
        print("\nVerifying...")
        result = verify_build.remote()
        print(f"Result: {'PASSED' if result['success'] else 'FAILED'}")
        
        if not result['success']:
            print("\nFailed checks:")
            for k, v in result['checks'].items():
                if v is False:
                    print(f"  - {k}")
            return
    
    if check_cache:
        print("\nChecking caches...")
        caches = check_caches.remote()
        print(f"Caches: {caches}")
    
    print("\nDone! Image cached on Modal.")
