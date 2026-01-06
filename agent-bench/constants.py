"""
Constants for Kotlin-bench Agentic Evaluations

Single source of truth: config/*.json files
This module loads configs and provides them to Python code.
The same JSON files are used by Dockerfile for consistency.
"""

import json
from pathlib import Path
from typing import Dict

# =============================================================================
# Load Config from JSON
# =============================================================================

CONFIG_DIR = Path(__file__).parent / "config"


def load_repo_config(repo_name: str) -> dict:
    """Load config for a repository from its JSON file."""
    config_file = CONFIG_DIR / f"{repo_name}.json"
    if not config_file.exists():
        return {}
    with open(config_file) as f:
        return json.load(f)


# Load all configs
ANKI_CONFIG = load_repo_config("anki")
WORDPRESS_CONFIG = load_repo_config("wordpress")
KTLINT_CONFIG = load_repo_config("ktlint")
COROUTINES_CONFIG = load_repo_config("coroutines")
THUNDERBIRD_CONFIG = load_repo_config("thunderbird")
DATETIME_CONFIG = load_repo_config("datetime")

# =============================================================================
# Anki Constants (from config/anki.json)
# =============================================================================

ANKI_JDK_VERSION = ANKI_CONFIG.get("jdk_version", "17.0.9-tem")
ANKI_BASE_COMMIT = ANKI_CONFIG.get("base_commit", "bbfd8f4a10c796d4b955d54530c7f11e81ca250d")
ANKI_INSTALL_SCRIPT = ANKI_CONFIG.get("install_script", "")
ANKI_TEST_COMMAND = ANKI_CONFIG.get("test_command", "./gradlew test")
ANDROID_SDK_PACKAGES = ANKI_CONFIG.get("android_sdk_packages", [])

# =============================================================================
# WordPress Constants (from config/wordpress.json)
# =============================================================================

WORDPRESS_JDK_VERSION = WORDPRESS_CONFIG.get("jdk_version", "17.0.9-tem")
WORDPRESS_BASE_COMMIT = WORDPRESS_CONFIG.get("base_commit", "")
WORDPRESS_INSTALL_SCRIPT = WORDPRESS_CONFIG.get("install_script", "if [ -f gradle.properties-example ]; then cp gradle.properties-example gradle.properties; fi")
WORDPRESS_TEST_COMMAND = WORDPRESS_CONFIG.get("test_command", "./gradlew :WordPress:testWordPressVanillaDebugUnitTest")

# =============================================================================
# ktlint Constants (from config/ktlint.json)
# =============================================================================

KTLINT_JDK_VERSION = KTLINT_CONFIG.get("jdk_version", "17.0.9-tem")
KTLINT_BASE_COMMIT = KTLINT_CONFIG.get("base_commit", "")
KTLINT_INSTALL_SCRIPT = KTLINT_CONFIG.get("install_script", "")
KTLINT_TEST_COMMAND = KTLINT_CONFIG.get("test_command", "./gradlew :ktlint-ruleset-standard:test")

# =============================================================================
# kotlinx.coroutines Constants (from config/coroutines.json)
# =============================================================================

COROUTINES_JDK_VERSION = COROUTINES_CONFIG.get("jdk_version", "11.0.20-tem")
COROUTINES_BASE_COMMIT = COROUTINES_CONFIG.get("base_commit", "")
COROUTINES_INSTALL_SCRIPT = COROUTINES_CONFIG.get("install_script", """
if [ -f kotlinx-coroutines-core/jvm/test/TestSecurityManager.kt ]; then
    sed -i '/override fun checkPropertyAccess/,/^    }/d' kotlinx-coroutines-core/jvm/test/TestSecurityManager.kt
fi        
""")
COROUTINES_TEST_COMMAND = COROUTINES_CONFIG.get("test_command", "./gradlew :kotlinx-coroutines-core:jvmTest")

# =============================================================================
# Thunderbird Constants (from config/thunderbird.json)
# =============================================================================

THUNDERBIRD_JDK_VERSION = THUNDERBIRD_CONFIG.get("jdk_version", "17.0.9-tem")
THUNDERBIRD_BASE_COMMIT = THUNDERBIRD_CONFIG.get("base_commit", "")
THUNDERBIRD_INSTALL_SCRIPT = THUNDERBIRD_CONFIG.get("install_script", "")
THUNDERBIRD_TEST_COMMAND = THUNDERBIRD_CONFIG.get("test_command", "./gradlew test")

# =============================================================================
# kotlinx-datetime Constants (from config/datetime.json)
# =============================================================================

DATETIME_JDK_VERSION = DATETIME_CONFIG.get("jdk_version", "8.0.392-zulu")
DATETIME_BASE_COMMIT = DATETIME_CONFIG.get("base_commit", "")
DATETIME_INSTALL_SCRIPT = DATETIME_CONFIG.get("install_script", "")
DATETIME_TEST_COMMAND = DATETIME_CONFIG.get("test_command", "./gradlew :kotlinx-datetime:jvmTest")

# =============================================================================
# Version to Installation Mappings
# =============================================================================

# Anki versions all use the same config
MAP_VERSION_TO_INSTALL_ANKI = {
    k: {"jdk_version": ANKI_JDK_VERSION, "install": ANKI_INSTALL_SCRIPT}
    for k in [
        "2.16", "2.171", "2.1710", "2.1713", "2.1714", "2.1715", "2.1716", "2.1717",
        "2.172", "2.173", "2.174", "2.175", "2.176", "2.178", "2.179",
        "2.182", "2.183", "2.184", "2.185", "2.186", "2.187", "2.188", "2.189",
        "2.190", "2.191", "2.1910", "2.1911", "2.1912", "2.192", "2.193", "2.194", "2.196", "2.197", "2.199",
        "2.20", "2.201", "2.202", "2.203",
        "2.211", "2.2111", "2.2112", "2.2113", "2.214", "2.215", "2.217", "2.218", "2.219"
    ]
}

MAP_VERSION_TO_INSTALL_WORDPRESS = {
    k: {"jdk_version": WORDPRESS_JDK_VERSION, "install": WORDPRESS_INSTALL_SCRIPT}
    for k in [
        "25.72", "25.71", "25.62", "25.4", "25.41", "25.31", "25.01",
        "24.92", "24.72", "24.83", "24.82", "24.73", "24.5", "24.71",
        "24.61", "24.51", "24.42", "24.41", "24.31", "24.2", "24.22",
        "24.21", "24.1", "24.12", "24.13", "24.01", "23.93", "23.92",
        "23.71", "23.91", "23.85", "23.83", "23.84", "23.82", "23.7",
        "23.61", "23.5", "23.52", "23.51", "23.4", "23.43", "23.32",
        "23.31", "23.2", "23.21", "23.12", "23.11", "23.02", "23.01", "22.91"
    ]
}

MAP_VERSION_TO_INSTALL_KTLINT = {
    k: {"jdk_version": KTLINT_JDK_VERSION, "install": KTLINT_INSTALL_SCRIPT}
    for k in ["0.49", "0.50", "1.0", "1.1", "1.2", "1.3", "1.4", "1.5"]
}

MAP_VERSION_TO_INSTALL_THUNDERBIRD = {
    k: {"jdk_version": THUNDERBIRD_JDK_VERSION, "install": THUNDERBIRD_INSTALL_SCRIPT}
    for k in ["0.1", "8.0", "10.0", "11.0"]
}

MAP_VERSION_TO_INSTALL_COROUTINES = {
    k: {"jdk_version": COROUTINES_JDK_VERSION, "install": COROUTINES_INSTALL_SCRIPT}
    for k in ["1.10", "1.9", "1.8", "1.6", "1.7"]
}

MAP_VERSION_TO_INSTALL_KOTLINX_DATETIME = {
    k: {"jdk_version": DATETIME_JDK_VERSION, "install": DATETIME_INSTALL_SCRIPT}
    for k in ["0.4", "0.5", "0.6"]
}

# Master mapping: repo -> version -> install specs
MAP_VERSION_TO_INSTALL: Dict[str, Dict[str, dict]] = {
    "wordpress-mobile/WordPress-Android": MAP_VERSION_TO_INSTALL_WORDPRESS,
    "ankidroid/Anki-Android": MAP_VERSION_TO_INSTALL_ANKI,
    "pinterest/ktlint": MAP_VERSION_TO_INSTALL_KTLINT,
    "Kotlin/kotlinx.coroutines": MAP_VERSION_TO_INSTALL_COROUTINES,
    "thunderbird/thunderbird-android": MAP_VERSION_TO_INSTALL_THUNDERBIRD,
    "Kotlin/kotlinx-datetime": MAP_VERSION_TO_INSTALL_KOTLINX_DATETIME,
}

# =============================================================================
# Test Framework Commands
# =============================================================================

MAP_REPO_TO_TEST_FRAMEWORK: Dict[str, str] = {
    "wordpress-mobile/WordPress-Android": WORDPRESS_TEST_COMMAND,
    "ankidroid/Anki-Android": ANKI_TEST_COMMAND,
    "pinterest/ktlint": KTLINT_TEST_COMMAND,
    "Kotlin/kotlinx.coroutines": COROUTINES_TEST_COMMAND,
    "thunderbird/thunderbird-android": THUNDERBIRD_TEST_COMMAND,
    "Kotlin/kotlinx-datetime": DATETIME_TEST_COMMAND,
}

# =============================================================================
# Repo to Config Name Mapping
# =============================================================================

REPO_TO_CONFIG_NAME: Dict[str, str] = {
    "wordpress-mobile/WordPress-Android": "wordpress",
    "ankidroid/Anki-Android": "anki",
    "pinterest/ktlint": "ktlint",
    "Kotlin/kotlinx.coroutines": "coroutines",
    "thunderbird/thunderbird-android": "thunderbird",
    "Kotlin/kotlinx-datetime": "datetime",
}

# =============================================================================
# Path Constants
# =============================================================================

PROJECT_PATH = "/project"
FIREBENDER_PATH = "/firebender"
FIREBENDER_BRANCH = "aman/firebender-harness"
SDKMAN_JAVA_PATH = "/root/.sdkman/candidates/java"
ANDROID_SDK_PATH = "/root/android-sdk"
AGENT_PORT = 8742

# =============================================================================
# Helper Functions
# =============================================================================

def get_install_specs(repo: str, version: str) -> dict:
    """
    Get installation specifications for a repo/version.
    
    Returns dict with:
    - jdk_version: JDK version to use (e.g., "17.0.9-tem")
    - install: Installation script to run
    """
    if repo not in MAP_VERSION_TO_INSTALL:
        return {"jdk_version": "17.0.9-tem", "install": ""}
    
    repo_versions = MAP_VERSION_TO_INSTALL[repo]
    if version not in repo_versions:
        return {"jdk_version": "17.0.9-tem", "install": ""}
    
    return repo_versions[version]


def get_test_command(repo: str) -> str:
    """Get the test command for a repository."""
    return MAP_REPO_TO_TEST_FRAMEWORK.get(repo, "./gradlew test")


def get_repo_config(repo: str) -> dict:
    """Get the full config for a repository."""
    config_name = REPO_TO_CONFIG_NAME.get(repo)
    if config_name:
        return load_repo_config(config_name)
    return {}


def is_android_project(repo: str) -> bool:
    """Check if a repo is an Android project (requires Android SDK)."""
    config = get_repo_config(repo)
    return bool(config.get("android_sdk_packages", []))
