#!/usr/bin/env python3
"""
Generate unique Dockerfiles for each repository based on config files.

This reads from agent-bench/config/{repo}.json and generates
agent-bench/docker/generated/Dockerfile.{repo} for each repository.

Usage:
    python agent-bench/docker/generate_dockerfiles.py
    python agent-bench/docker/generate_dockerfiles.py --repo anki
    python agent-bench/docker/generate_dockerfiles.py --list
"""

import json
import os
import argparse
from pathlib import Path

# =============================================================================
# Paths
# =============================================================================

SCRIPT_DIR = Path(__file__).parent
CONFIG_DIR = SCRIPT_DIR.parent / "config"
OUTPUT_DIR = SCRIPT_DIR / "generated"

AVAILABLE_REPOS = ["anki", "coroutines", "datetime", "ktlint", "thunderbird", "wordpress"]


def load_config(repo_name: str) -> dict:
    """Load config from JSON file."""
    config_path = CONFIG_DIR / f"{repo_name}.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with open(config_path) as f:
        return json.load(f)


def get_repo_url(config: dict) -> str:
    """Get repo URL, deriving from repo name if not specified."""
    if "repo_url" in config:
        return config["repo_url"]
    return f"https://github.com/{config.get('repo', '')}.git"


def needs_android_sdk(config: dict) -> bool:
    """Check if repo needs Android SDK."""
    return bool(config.get("android_sdk_packages", []))


def generate_dockerfile(repo_name: str) -> str:
    """Generate a complete Dockerfile for a repository."""
    config = load_config(repo_name)
    
    repo_url = get_repo_url(config)
    base_commit = config.get("base_commit", "")
    jdk_version = config.get("jdk_version", "17.0.9-tem")
    has_android = needs_android_sdk(config)
    android_packages = config.get("android_sdk_packages", [])
    
    dockerfile = f'''# =============================================================================
# Kotlin-bench Pre-baked Docker Image: {repo_name}
# =============================================================================
# Auto-generated from agent-bench/config/{repo_name}.json
# DO NOT EDIT DIRECTLY - regenerate with: python generate_dockerfiles.py
#
# Repository: {config.get("repo", "unknown")}
# JDK: {jdk_version}
# Base Commit: {base_commit[:12]}...
# Android SDK: {has_android}
#
# Build:
#   docker build -f agent-bench/docker/generated/Dockerfile.{repo_name} -t kotlin-bench-{repo_name} .
#
# Run:
#   docker run -it --rm -p 8742:8742 kotlin-bench-{repo_name}
# =============================================================================

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# =============================================================================
# System Dependencies
# =============================================================================

RUN apt-get update && apt-get install -y \\
    git curl wget unzip zip ca-certificates jq \\
    xvfb x11-xserver-utils libx11-6 libxext6 libxrender1 \\
    libxtst6 libxi6 libxrandr2 x11-utils \\
    fontconfig fonts-dejavu fonts-liberation fonts-noto \\
    libfontconfig1 libfreetype6 libpng16-16 libasound2 \\
    libatk1.0-0 libatk-bridge2.0-0 libcairo2 libcups2 \\
    libdbus-1-3 libdrm2 libgbm1 libgdk-pixbuf2.0-0 libgtk-3-0 \\
    libnspr4 libnss3 libpango-1.0-0 libxcomposite1 libxcursor1 \\
    libxdamage1 libxfixes3 libxkbcommon0 libxshmfence1 \\
    procps htop lsof netcat-openbsd \\
    ripgrep fd-find \\
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Copy Config
# =============================================================================

COPY agent-bench/config/{repo_name}.json /config/repo.json

# =============================================================================
# Java 21 (for IntelliJ IDEA)
# =============================================================================
# IntelliJ 2025.1 requires Java 21. The repo-specific JDK is installed via
# SDKMAN and used at runtime for Gradle builds.

RUN apt-get update && apt-get install -y openjdk-21-jdk \\
    && rm -rf /var/lib/apt/lists/*

RUN JAVA_DIR=$(ls -d /usr/lib/jvm/java-21-openjdk-* | head -1) && \\
    ln -sf ${{JAVA_DIR}} /usr/lib/jvm/java-21

ENV JAVA_HOME=/usr/lib/jvm/java-21
ENV PATH="${{JAVA_HOME}}/bin:${{PATH}}"

# =============================================================================
# SDKMAN + Project JDK: {jdk_version}
# =============================================================================
# Install the repo-specific JDK via SDKMAN for use at runtime.
# The agent will switch to this JDK when running Gradle commands.

ENV SDKMAN_DIR=/root/.sdkman

RUN curl -s "https://get.sdkman.io" | bash

RUN bash -c "source $SDKMAN_DIR/bin/sdkman-init.sh && \\
    sdk install java {jdk_version} && \\
    sdk default java {jdk_version}"

# Verify Java 21 is active (for IntelliJ)
RUN java -version
'''

    # Android SDK section (conditional)
    if has_android:
        packages_str = " ".join(f'"{p}"' for p in android_packages)
        dockerfile += f'''
# =============================================================================
# Android SDK
# =============================================================================

ENV ANDROID_SDK_ROOT=/root/android-sdk
ENV ANDROID_HOME=${{ANDROID_SDK_ROOT}}
ENV PATH="${{ANDROID_SDK_ROOT}}/cmdline-tools/latest/bin:${{ANDROID_SDK_ROOT}}/platform-tools:${{PATH}}"

RUN mkdir -p ${{ANDROID_SDK_ROOT}}/cmdline-tools && \\
    cd ${{ANDROID_SDK_ROOT}}/cmdline-tools && \\
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -O cmdline-tools.zip && \\
    unzip -q cmdline-tools.zip && \\
    mv cmdline-tools latest && \\
    rm cmdline-tools.zip

RUN yes | ${{ANDROID_SDK_ROOT}}/cmdline-tools/latest/bin/sdkmanager --licenses || true

RUN ${{ANDROID_SDK_ROOT}}/cmdline-tools/latest/bin/sdkmanager {packages_str}
'''
    else:
        dockerfile += '''
# =============================================================================
# Android SDK: Not required for this project
# =============================================================================

ENV ANDROID_SDK_ROOT=/root/android-sdk
ENV ANDROID_HOME=${ANDROID_SDK_ROOT}
'''

    # IntelliJ installation
    dockerfile += '''
# =============================================================================
# IntelliJ IDEA Community Edition 2025.1.1
# =============================================================================

ENV IDEA_HOME=/opt/idea
ENV PATH="${IDEA_HOME}/bin:${PATH}"

RUN mkdir -p /opt && cd /opt && \\
    ARCH=$(uname -m) && \\
    echo "Detected architecture: ${ARCH}" && \\
    if [ "${ARCH}" = "aarch64" ] || [ "${ARCH}" = "arm64" ]; then \\
        IDEA_URL="https://download.jetbrains.com/idea/ideaIC-2025.1.1-aarch64.tar.gz"; \\
    else \\
        IDEA_URL="https://download.jetbrains.com/idea/ideaIC-2025.1.1.tar.gz"; \\
    fi && \\
    echo "Downloading IntelliJ IDEA from: ${IDEA_URL}" && \\
    wget --progress=dot:giga "${IDEA_URL}" -O idea.tar.gz && \\
    mkdir -p /opt/idea && \\
    tar -xzf idea.tar.gz -C /opt/idea --strip-components=1 && \\
    rm idea.tar.gz

# =============================================================================
# IDE Configuration
# =============================================================================

ENV IDEA_CONFIG_DIR=/root/.config/JetBrains/IdeaIC2025.1
ENV IDEA_CACHE_DIR=/root/.cache/JetBrains/IdeaIC2025.1
ENV IDEA_DATA_DIR=/root/.local/share/JetBrains/IdeaIC2025.1
ENV IDEA_PLUGINS_DIR=/root/.local/share/JetBrains/IdeaIC2025.1

RUN mkdir -p ${IDEA_CONFIG_DIR} ${IDEA_CACHE_DIR} ${IDEA_DATA_DIR} ${IDEA_PLUGINS_DIR}

RUN mkdir -p ${IDEA_CONFIG_DIR}/options && \\
    echo '<?xml version="1.0" encoding="UTF-8"?><application><component name="PropertiesComponent"><property name="ide.no.welcome.screen" value="true" /><property name="ide.first.run" value="false" /><property name="ide.splash.disabled" value="true" /></component></application>' > ${IDEA_CONFIG_DIR}/options/other.xml

RUN mkdir -p ${IDEA_CONFIG_DIR}/consentOptions && \\
    echo '<?xml version="1.0" encoding="UTF-8"?><root><accepted>999.999</accepted></root>' > ${IDEA_CONFIG_DIR}/consentOptions/accepted

RUN echo 'idea.initially.ask.config=false' > ${IDEA_CONFIG_DIR}/idea.properties && \\
    echo 'idea.trust.all.projects=true' >> ${IDEA_CONFIG_DIR}/idea.properties && \\
    echo 'nosplash=true' >> ${IDEA_CONFIG_DIR}/idea.properties
'''

    # Android plugins (always installed - needed for GradleSyncState API used by Firebender)
    dockerfile += '''
# =============================================================================
# Android Plugins
# =============================================================================
# Always installed to provide GradleSyncState API for Firebender plugin

RUN cd /tmp && \\
    wget -q "https://plugins.jetbrains.com/plugin/download?pluginId=org.jetbrains.android&version=251.25410.109" -O android-plugin.zip && \\
    unzip -q android-plugin.zip -d ${IDEA_PLUGINS_DIR}/ && \\
    rm android-plugin.zip

RUN cd /tmp && \\
    wget -q "https://plugins.jetbrains.com/plugin/download?pluginId=com.android.tools.design&version=251.25410.59" -O android-design-plugin.zip && \\
    unzip -q android-design-plugin.zip -d ${IDEA_PLUGINS_DIR}/ && \\
    rm android-design-plugin.zip

'''

    dockerfile += '''
RUN echo "Installed plugins:" && ls -la ${IDEA_PLUGINS_DIR}/
'''

    # Clone repository
    dockerfile += f'''
# =============================================================================
# Clone Repository: {config.get("repo", "unknown")}
# =============================================================================

WORKDIR /project

RUN git clone {repo_url} . && \\
    git checkout {base_commit} && \\
    if [ -f gradlew ]; then chmod +x gradlew; fi

# =============================================================================
# Install Script (from config)
# =============================================================================

RUN jq -r '.install_script' /config/repo.json > /tmp/install.sh && \\
    chmod +x /tmp/install.sh && \\
    cd /project && \\
    bash /tmp/install.sh && \\
    rm /tmp/install.sh
'''

    # Environment and warmup
    dockerfile += '''
# =============================================================================
# Environment
# =============================================================================

ENV DISPLAY=:99
ENV FIREBENDER_AGENT_SERVER=true
ENV FIREBENDER_AGENT_SERVER_PORT=8742
ENV PROJECT_PATH=/project

EXPOSE 8742

# =============================================================================
# Warmup
# =============================================================================

RUN export _JAVA_OPTIONS="-Djb.consents.confirmation.enabled=false \\
    -Djb.privacy.policy.text=<!--999.999--> \\
    -Didea.initially.ask.config=false \\
    -Dide.no.splash=true \\
    -Dnosplash=true \\
    -Dhidpi=false \\
    -Dsun.java2d.uiScale.enabled=false \\
    -Dsun.java2d.uiScale=1.0 \\
    -Dide.ui.scale=1.0 \\
    -Dawt.useSystemAAFontSettings=lcd \\
    -Dsun.java2d.xrender=false" && \\
    xvfb-run -a -s "-screen 0 1920x1080x24" \\
    /opt/idea/bin/idea.sh warmup \\
    --project-dir=/project

# =============================================================================
# Default
# =============================================================================

WORKDIR /project
CMD ["/bin/bash"]
'''

    return dockerfile


def generate_all(repos: list = None):
    """Generate Dockerfiles for specified repos (or all)."""
    repos = repos or AVAILABLE_REPOS
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating Dockerfiles in {OUTPUT_DIR}/")
    print(f"Reading configs from {CONFIG_DIR}/")
    print()
    
    for repo_name in repos:
        try:
            dockerfile = generate_dockerfile(repo_name)
            output_path = OUTPUT_DIR / f"Dockerfile.{repo_name}"
            
            with open(output_path, "w") as f:
                f.write(dockerfile)
            
            config = load_config(repo_name)
            print(f"  {repo_name}:")
            print(f"    Repo: {config.get('repo', 'unknown')}")
            print(f"    JDK: {config.get('jdk_version', 'default')}")
            print(f"    Android: {needs_android_sdk(config)}")
            print(f"    Output: {output_path}")
            print()
            
        except Exception as e:
            print(f"  {repo_name}: ERROR - {e}")
            print()
    
    print(f"Done! Generated {len(repos)} Dockerfile(s)")
    print(f"\nTo build:")
    print(f"  docker build -f agent-bench/docker/generated/Dockerfile.<repo> -t kotlin-bench-<repo> .")


def main():
    parser = argparse.ArgumentParser(description="Generate Dockerfiles for Kotlin-bench repos")
    parser.add_argument("--repo", help="Generate for specific repo only")
    parser.add_argument("--list", action="store_true", help="List available repos")
    parser.add_argument("--output-dir", help="Output directory (default: agent-bench/docker/generated)")
    args = parser.parse_args()
    
    if args.list:
        print("Available repositories:")
        for repo in AVAILABLE_REPOS:
            try:
                config = load_config(repo)
                print(f"  - {repo}: {config.get('repo', 'unknown')}")
            except FileNotFoundError:
                print(f"  - {repo}: (config missing)")
        return
    
    if args.output_dir:
        global OUTPUT_DIR
        OUTPUT_DIR = Path(args.output_dir)
    
    repos = [args.repo] if args.repo else None
    generate_all(repos)


if __name__ == "__main__":
    main()
