"""
Build Pre-baked Docker Images on Modal

Builds and caches pre-baked images for all Kotlin benchmark repositories.
Uses pre-generated Dockerfiles from agent-bench/docker/generated/

Usage:
    # Build and verify all repos
    modal run agent-bench/docker/build_modal.py
    
    # Build specific repo
    modal run agent-bench/docker/build_modal.py::verify_anki
    modal run agent-bench/docker/build_modal.py::verify_coroutines

Available repos: anki, coroutines, datetime, ktlint, thunderbird, wordpress

Before running, generate Dockerfiles:
    python agent-bench/docker/generate_dockerfiles.py
"""

import modal
import os
import subprocess

# =============================================================================
# Configuration
# =============================================================================

AVAILABLE_REPOS = ["anki", "coroutines", "datetime", "ktlint", "thunderbird", "wordpress"]

# Which repos need Android SDK (for verification)
ANDROID_REPOS = {"anki", "thunderbird", "wordpress"}


# =============================================================================
# Static Image Definitions (one per repo for proper Modal caching)
# =============================================================================
# Each uses its pre-generated Dockerfile from agent-bench/docker/generated/

image_anki = modal.Image.from_dockerfile(
    path="agent-bench/docker/generated/Dockerfile.anki",
    context_dir=".",
    add_python="3.11",
)

image_coroutines = modal.Image.from_dockerfile(
    path="agent-bench/docker/generated/Dockerfile.coroutines",
    context_dir=".",
    add_python="3.11",
)

image_datetime = modal.Image.from_dockerfile(
    path="agent-bench/docker/generated/Dockerfile.datetime",
    context_dir=".",
    add_python="3.11",
)

image_ktlint = modal.Image.from_dockerfile(
    path="agent-bench/docker/generated/Dockerfile.ktlint",
    context_dir=".",
    add_python="3.11",
)

image_thunderbird = modal.Image.from_dockerfile(
    path="agent-bench/docker/generated/Dockerfile.thunderbird",
    context_dir=".",
    add_python="3.11",
)

image_wordpress = modal.Image.from_dockerfile(
    path="agent-bench/docker/generated/Dockerfile.wordpress",
    context_dir=".",
    add_python="3.11",
)

IMAGES = {
    "anki": image_anki,
    "coroutines": image_coroutines,
    "datetime": image_datetime,
    "ktlint": image_ktlint,
    "thunderbird": image_thunderbird,
    "wordpress": image_wordpress,
}


# =============================================================================
# App and Verify Functions
# =============================================================================

app = modal.App("kotlin-bench-builder")


def _verify_image(repo_name: str) -> dict:
    """Common verification logic."""
    has_android = repo_name in ANDROID_REPOS
    
    print("=" * 60)
    print(f"Verifying {repo_name} Pre-baked Image")
    print("=" * 60)
    
    checks = {}
    
    # Check project
    has_gradlew = os.path.exists("/project/gradlew")
    has_build_file = os.path.exists("/project/build.gradle") or os.path.exists("/project/build.gradle.kts")
    checks["project_exists"] = has_gradlew or has_build_file
    print(f"  Project exists: {checks['project_exists']}")
    
    # Check config
    checks["config_exists"] = os.path.exists("/config/repo.json")
    print(f"  Config exists: {checks['config_exists']}")
    
    # Check Java
    result = subprocess.run(["java", "-version"], capture_output=True, text=True)
    checks["java_works"] = result.returncode == 0
    print(f"  Java works: {checks['java_works']}")
    if checks["java_works"]:
        java_ver = result.stderr.split('\n')[0] if result.stderr else "unknown"
        print(f"    Version: {java_ver}")
    
    # Check architecture
    result = subprocess.run(["uname", "-m"], capture_output=True, text=True)
    checks["arch"] = result.stdout.strip()
    print(f"  Architecture: {checks['arch']}")
    
    # Check IntelliJ
    checks["idea_exists"] = os.path.exists("/opt/idea/bin/idea.sh")
    print(f"  IntelliJ IDEA: {checks['idea_exists']}")
    
    # Check Android SDK (only if applicable)
    if has_android:
        checks["android_sdk"] = os.path.exists("/root/android-sdk/platform-tools")
        print(f"  Android SDK: {checks['android_sdk']}")
    
    # Check IDE cache (indicates warmup ran)
    cache_dir = "/root/.cache/JetBrains/IdeaIC2025.1"
    checks["ide_cache_exists"] = os.path.exists(cache_dir) and bool(os.listdir(cache_dir))
    print(f"  IDE Cache: {checks['ide_cache_exists']}")
    
    # Check SDKMAN
    checks["sdkman_exists"] = os.path.exists("/root/.sdkman/bin/sdkman-init.sh")
    print(f"  SDKMAN: {checks['sdkman_exists']}")
    
    all_passed = all([
        checks["project_exists"],
        checks["config_exists"],
        checks["java_works"],
        checks["idea_exists"],
        checks.get("android_sdk", True),
        checks["ide_cache_exists"],
    ])
    
    print("=" * 60)
    print(f"All checks: {'PASSED' if all_passed else 'FAILED'}")
    print("=" * 60)
    
    return {"success": all_passed, "checks": checks, "repo": repo_name}


# -----------------------------------------------------------------------------
# Static verify functions (one per repo)
# -----------------------------------------------------------------------------

@app.function(image=image_anki, timeout=1800, cpu=4, memory=16384)
def verify_anki() -> dict:
    """Verify anki image."""
    return _verify_image("anki")


@app.function(image=image_coroutines, timeout=1800, cpu=4, memory=16384)
def verify_coroutines() -> dict:
    """Verify coroutines image."""
    return _verify_image("coroutines")


@app.function(image=image_datetime, timeout=1800, cpu=4, memory=16384)
def verify_datetime() -> dict:
    """Verify datetime image."""
    return _verify_image("datetime")


@app.function(image=image_ktlint, timeout=1800, cpu=4, memory=16384)
def verify_ktlint() -> dict:
    """Verify ktlint image."""
    return _verify_image("ktlint")


@app.function(image=image_thunderbird, timeout=1800, cpu=4, memory=16384)
def verify_thunderbird() -> dict:
    """Verify thunderbird image."""
    return _verify_image("thunderbird")


@app.function(image=image_wordpress, timeout=1800, cpu=4, memory=16384)
def verify_wordpress() -> dict:
    """Verify wordpress image."""
    return _verify_image("wordpress")


VERIFY_FUNCTIONS = {
    "anki": verify_anki,
    "coroutines": verify_coroutines,
    "datetime": verify_datetime,
    "ktlint": verify_ktlint,
    "thunderbird": verify_thunderbird,
    "wordpress": verify_wordpress,
}


# =============================================================================
# Entry Point
# =============================================================================

@app.local_entrypoint()
def main(
    repo: str = "",
    all: bool = True,
    list_repos: bool = False,
):
    """
    Build and verify pre-baked images for Kotlin projects.
    
    Args:
        repo: Repository config name (e.g., "anki", "coroutines")
        all: Build all repositories (default: True)
        list_repos: List available repositories
    """
    if list_repos:
        print("Available repositories:")
        for r in AVAILABLE_REPOS:
            android = "yes" if r in ANDROID_REPOS else "no"
            print(f"  - {r} (android: {android})")
        return
    
    repos_to_build = AVAILABLE_REPOS if (all and not repo) else [repo] if repo else AVAILABLE_REPOS
    
    results = []
    for repo_name in repos_to_build:
        if repo_name not in AVAILABLE_REPOS:
            print(f"Error: Unknown repo '{repo_name}'")
            print(f"Available: {', '.join(AVAILABLE_REPOS)}")
            continue
        
        print("=" * 60)
        print(f"Building {repo_name} Pre-baked Image")
        print("=" * 60)
        print(f"  Dockerfile: agent-bench/docker/generated/Dockerfile.{repo_name}")
        print(f"  Android: {repo_name in ANDROID_REPOS}")
        print("=" * 60)
        
        verify_fn = VERIFY_FUNCTIONS[repo_name]
        result = verify_fn.remote()
        results.append(result)
        
        status = "PASSED" if result["success"] else "FAILED"
        print(f"\n{repo_name}: {status}\n")
    
    # Summary
    print("\n" + "=" * 60)
    print("BUILD SUMMARY")
    print("=" * 60)
    passed = sum(1 for r in results if r["success"])
    print(f"  Total:  {len(results)}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {len(results) - passed}")
    
    for r in results:
        status = "PASSED" if r["success"] else "FAILED"
        print(f"  - {r['repo']}: {status}")
    
    print("=" * 60)
    print("\nAll images cached on Modal!")
