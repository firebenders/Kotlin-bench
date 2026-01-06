"""
Test Firebender Plugin with Pre-warmed IDE on Modal

This script:
1. Uses Dockerfile.modal (x86_64 optimized) as base with pre-warmed caches
2. Installs the Firebender plugin
3. Starts the IDE and verifies Firebender loads from logs

Usage:
    modal run docker/anki-prebaked/test_firebender_modal.py
"""

import modal
import os
import sys
from pathlib import Path

# =============================================================================
# Configuration
# =============================================================================

app = modal.App("firebender-ide-test")

# Plugin paths
FIREBENDER_ZIP = "firebender/Firebender.zip"
# Using IntelliJIdea (Ultimate) paths since idea-*.tar.gz downloads Ultimate edition
# Plugins go DIRECTLY under DATA_DIR (not in a /plugins subdirectory)
IDEA_PLUGINS_DIR = "/root/.local/share/JetBrains/IntelliJIdea2025.3"

# Build image from Modal-optimized Dockerfile (x86_64)
base_image = modal.Image.from_dockerfile(
    path="docker/anki-prebaked/Dockerfile.modal",
    context_dir=".",
    add_python="3.11",
)

# Add Firebender plugin to the image using ADD in a new layer
# copy=True required because we run commands after adding the file
firebender_image = (
    base_image
    .add_local_file(FIREBENDER_ZIP, "/tmp/Firebender.zip", copy=True)
    .run_commands([
        # Debug: show zip contents first
        "echo '=== ZIP CONTENTS ===' && unzip -l /tmp/Firebender.zip | head -30",
        f"mkdir -p {IDEA_PLUGINS_DIR}",
        f"unzip -o /tmp/Firebender.zip -d {IDEA_PLUGINS_DIR}/",
        "rm /tmp/Firebender.zip",
        # Debug: show what was extracted
        f"echo '=== PLUGINS DIR CONTENTS ===' && ls -la {IDEA_PLUGINS_DIR}/",
        f"echo '=== RECURSIVE LISTING ===' && find {IDEA_PLUGINS_DIR} -type f -name '*.jar' | head -20",
        f"echo '=== PLUGIN.XML FILES ===' && find {IDEA_PLUGINS_DIR} -name 'plugin.xml' -exec cat {{}} \\; | head -50",
    ])
)


# =============================================================================
# Test Functions
# =============================================================================

@app.function(image=firebender_image, timeout=600, cpu=4, memory=16384)
def verify_plugin_installed() -> dict:
    """Verify Firebender plugin is installed correctly."""
    import subprocess
    
    print("=" * 60)
    print("Verifying Firebender Plugin Installation")
    print("=" * 60)
    
    checks = {}
    
    # Check plugins directory
    plugins_dir = IDEA_PLUGINS_DIR
    print(f"  Checking plugins directory: {plugins_dir}")
    
    if os.path.exists(plugins_dir):
        plugins = os.listdir(plugins_dir)
        checks["plugins_found"] = plugins
        print(f"  Plugins found: {plugins}")
        
        # Look deeper - check for the actual package
        # The plugin package is: com.github.firebender.androidstudiocopilot
        result = subprocess.run(
            ["find", plugins_dir, "-name", "*.jar", "-o", "-name", "plugin.xml"],
            capture_output=True, text=True
        )
        print(f"  Plugin files found:\n{result.stdout}")
        
        # Check if any directory contains firebender-related content
        checks["firebender_installed"] = any(
            "firebender" in p.lower() or 
            "Firebender" in p or
            "androidstudiocopilot" in p.lower()
            for p in plugins
        )
        
        # Also grep for the package name in any plugin.xml
        grep_result = subprocess.run(
            ["grep", "-r", "androidstudiocopilot", plugins_dir],
            capture_output=True, text=True
        )
        if grep_result.stdout:
            print(f"  Found androidstudiocopilot references:\n{grep_result.stdout[:500]}")
            checks["firebender_installed"] = True
    else:
        checks["plugins_found"] = []
        checks["firebender_installed"] = False
        print(f"  Plugins directory NOT FOUND: {plugins_dir}")
    
    # Check caches are still there
    gradle_cache = "/root/.gradle/caches"
    checks["gradle_cache_exists"] = os.path.exists(gradle_cache)
    print(f"  Gradle cache exists: {checks['gradle_cache_exists']}")
    
    ide_cache = "/root/.cache/JetBrains"
    checks["ide_cache_exists"] = os.path.exists(ide_cache)
    print(f"  IDE cache exists: {checks['ide_cache_exists']}")
    
    # Check project
    checks["project_exists"] = os.path.exists("/project/gradlew")
    print(f"  Project exists: {checks['project_exists']}")
    
    print("=" * 60)
    print(f"Firebender installed: {checks['firebender_installed']}")
    print("=" * 60)
    
    return checks


@app.function(image=firebender_image, timeout=600, cpu=4, memory=16384)
def start_ide_and_check_logs() -> dict:
    """Start the IDE and check logs for Firebender initialization."""
    import subprocess
    import time
    
    print("=" * 60)
    print("Starting IDE and Checking for Firebender in Logs")
    print("=" * 60)
    
    # Set up environment
    env = os.environ.copy()
    env["DISPLAY"] = ":99"
    env["_JAVA_OPTIONS"] = (
        "-Djb.consents.confirmation.enabled=false "
        "-Djb.privacy.policy.text=<!--999.999--> "
        "-Didea.initially.ask.config=false "
        "-Dide.no.splash=true "
        "-Dnosplash=true "
        "-Dhidpi=false "
        "-Dsun.java2d.uiScale.enabled=false "
        "-Dsun.java2d.uiScale=1.0 "
        "-Dide.ui.scale=1.0 "
        "-Dawt.useSystemAAFontSettings=lcd "
        "-Dsun.java2d.xrender=false"
    )
    
    # Start Xvfb
    print("Starting Xvfb...")
    xvfb_proc = subprocess.Popen(
        ["Xvfb", ":99", "-screen", "0", "1920x1080x24"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(2)
    
    # Start IDE with project - use warmup command which exits cleanly
    print("Starting IDE warmup (this will exit when done)...")
    print("Command: /opt/idea/bin/idea.sh warmup --project-dir=/project")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            ["/opt/idea/bin/idea.sh", "warmup", "--project-dir=/project"],
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout for warmup
        )
        elapsed = time.time() - start_time
        
        stdout = result.stdout
        stderr = result.stderr
        
    except subprocess.TimeoutExpired as e:
        elapsed = time.time() - start_time
        stdout = e.stdout.decode() if e.stdout else ""
        stderr = e.stderr.decode() if e.stderr else ""
        print(f"IDE warmup timed out after {elapsed:.1f}s")
    
    finally:
        # Clean up Xvfb
        xvfb_proc.terminate()
    
    # Analyze logs
    all_output = stdout + stderr
    
    print("\n" + "=" * 60)
    print("LOG ANALYSIS")
    print("=" * 60)
    
    # Look for Firebender-related strings in output
    # Package: com.github.firebender.androidstudiocopilot
    firebender_mentions = []
    for line in all_output.split('\n'):
        line_lower = line.lower()
        if 'firebender' in line_lower or 'androidstudiocopilot' in line_lower:
            firebender_mentions.append(line.strip())
    
    if firebender_mentions:
        print(f"\nFirebender mentions found ({len(firebender_mentions)}):")
        for mention in firebender_mentions[:20]:  # First 20
            print(f"  {mention}")
    else:
        print("\nNo Firebender mentions found in output")
    
    # Look for plugin loading messages
    plugin_mentions = []
    for line in all_output.split('\n'):
        if 'plugin' in line.lower() and ('load' in line.lower() or 'init' in line.lower()):
            plugin_mentions.append(line.strip())
    
    if plugin_mentions:
        print(f"\nPlugin loading mentions ({len(plugin_mentions)}):")
        for mention in plugin_mentions[:10]:
            print(f"  {mention}")
    
    # Print last 100 lines of output for context
    print("\n" + "=" * 60)
    print("LAST 100 LINES OF OUTPUT")
    print("=" * 60)
    lines = all_output.strip().split('\n')
    for line in lines[-100:]:
        print(line)
    
    return {
        "elapsed_seconds": round(elapsed, 1),
        "firebender_mentions": len(firebender_mentions),
        "plugin_mentions": len(plugin_mentions),
        "output_lines": len(lines),
    }


@app.function(image=firebender_image, timeout=600, cpu=4, memory=16384)
def run_warmup_with_firebender() -> dict:
    """Run warmup command with Firebender installed and check timing."""
    import subprocess
    import time
    
    print("=" * 60)
    print("Running Warmup with Firebender Plugin")
    print("=" * 60)
    
    # Set up environment
    env = os.environ.copy()
    env["DISPLAY"] = ":99"
    env["_JAVA_OPTIONS"] = (
        "-Djb.consents.confirmation.enabled=false "
        "-Djb.privacy.policy.text=<!--999.999--> "
        "-Didea.initially.ask.config=false "
        "-Dide.no.splash=true "
        "-Dnosplash=true"
    )
    
    # Start Xvfb
    print("Starting Xvfb...")
    xvfb_proc = subprocess.Popen(
        ["Xvfb", ":99", "-screen", "0", "1920x1080x24"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(2)
    
    # Run warmup
    print("Running warmup command...")
    start_time = time.time()
    
    result = subprocess.run(
        ["/opt/idea/bin/idea.sh", "warmup", "--project-dir=/project"],
        env=env,
        capture_output=True,
        text=True,
        timeout=300  # 5 minute timeout
    )
    
    elapsed = time.time() - start_time
    xvfb_proc.terminate()
    
    all_output = result.stdout + result.stderr
    
    # Check for Firebender in output - look for both names
    firebender_lines = [
        l for l in all_output.split('\n') 
        if 'firebender' in l.lower() or 'androidstudiocopilot' in l.lower()
    ]
    
    print(f"\nWarmup completed in {elapsed:.1f}s")
    print(f"Firebender mentions: {len(firebender_lines)}")
    
    if firebender_lines:
        print("\nFirebender log lines:")
        for line in firebender_lines[:20]:
            print(f"  {line}")
    
    # Print warmup summary
    for line in all_output.split('\n'):
        if 'Warm-up' in line or 'indexed' in line.lower():
            print(line)
    
    return {
        "elapsed_seconds": round(elapsed, 1),
        "firebender_mentions": len(firebender_lines),
        "success": result.returncode == 0
    }


@app.local_entrypoint()
def main():
    """Run all tests."""
    print("=" * 60)
    print("Firebender IDE Test Suite")
    print("=" * 60)
    
    # Test 1: Verify plugin is installed
    print("\n[1/3] Verifying plugin installation...")
    install_result = verify_plugin_installed.remote()
    print(f"Plugin installed: {install_result.get('firebender_installed', False)}")
    
    if not install_result.get('firebender_installed'):
        print("ERROR: Firebender not installed! Stopping.")
        return
    
    # Test 2: Run warmup with Firebender
    print("\n[2/3] Running warmup with Firebender...")
    warmup_result = run_warmup_with_firebender.remote()
    print(f"Warmup time: {warmup_result['elapsed_seconds']}s")
    print(f"Firebender log mentions: {warmup_result['firebender_mentions']}")
    
    # Test 3: Start IDE and check logs
    print("\n[3/3] Starting IDE and checking logs...")
    ide_result = start_ide_and_check_logs.remote()
    print(f"IDE ran for: {ide_result['elapsed_seconds']}s")
    print(f"Firebender log mentions: {ide_result['firebender_mentions']}")
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"  Plugin installed: {install_result.get('firebender_installed', False)}")
    print(f"  Warmup time: {warmup_result['elapsed_seconds']}s")
    print(f"  Firebender in warmup logs: {warmup_result['firebender_mentions']} mentions")
    print(f"  Firebender in IDE logs: {ide_result['firebender_mentions']} mentions")
    print("=" * 60)
