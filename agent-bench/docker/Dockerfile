# =============================================================================
# Kotlin-bench Pre-baked Docker Image (Parameterized)
# =============================================================================
#
# A universal Dockerfile for building pre-baked images for any Kotlin project.
# Uses build-args to configure for different repositories.
#
# IntelliJ IDEA Community Edition 2025.1.1 - handles ARM64/x86_64 automatically.
#
# Build Args:
#   - REPO_NAME:   Config name (e.g., "anki", "coroutines", "ktlint")
#   - REPO_URL:    Git clone URL (e.g., "https://github.com/ankidroid/Anki-Android.git")
#   - BASE_COMMIT: Git commit to checkout
#   - NEEDS_ANDROID_SDK: "true" or "false" - whether to install Android SDK
#
# Usage:
#   docker build -f agent-bench/docker/Dockerfile \
#     --build-arg REPO_NAME=anki \
#     --build-arg REPO_URL=https://github.com/ankidroid/Anki-Android.git \
#     --build-arg BASE_COMMIT=bbfd8f4a10c796d4b955d54530c7f11e81ca250d \
#     --build-arg NEEDS_ANDROID_SDK=true \
#     -t kotlin-bench-anki .
#
# =============================================================================

FROM ubuntu:22.04

# Build arguments
ARG REPO_NAME
ARG REPO_URL
ARG BASE_COMMIT
ARG NEEDS_ANDROID_SDK=false

ENV DEBIAN_FRONTEND=noninteractive

# =============================================================================
# System Dependencies
# =============================================================================

RUN apt-get update && apt-get install -y \
    git curl wget unzip zip ca-certificates jq \
    xvfb x11-xserver-utils libx11-6 libxext6 libxrender1 \
    libxtst6 libxi6 libxrandr2 x11-utils \
    fontconfig fonts-dejavu fonts-liberation fonts-noto \
    libfontconfig1 libfreetype6 libpng16-16 libasound2 \
    libatk1.0-0 libatk-bridge2.0-0 libcairo2 libcups2 \
    libdbus-1-3 libdrm2 libgbm1 libgdk-pixbuf2.0-0 libgtk-3-0 \
    libnspr4 libnss3 libpango-1.0-0 libxcomposite1 libxcursor1 \
    libxdamage1 libxfixes3 libxkbcommon0 libxshmfence1 \
    procps htop lsof netcat-openbsd \
    ripgrep fd-find \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Copy Config (single source of truth)
# =============================================================================
# Note: COPY doesn't support ARG variable expansion, so we copy all configs
# and then select the right one with a RUN command

COPY agent-bench/config/ /config/all/

RUN cp /config/all/${REPO_NAME}.json /config/repo.json && \
    rm -rf /config/all

# =============================================================================
# Java (from config via SDKMAN)
# =============================================================================
# JDK version is read from config (e.g., "17.0.9-tem", "11.0.20-tem", "8.0.392-zulu")

ENV SDKMAN_DIR=/root/.sdkman

# Install SDKMAN and JDK from config
RUN curl -s "https://get.sdkman.io" | bash && \
    bash -c "source $SDKMAN_DIR/bin/sdkman-init.sh && \
    JDK_VERSION=\$(jq -r '.jdk_version // \"17.0.9-tem\"' /config/repo.json) && \
    echo \"Installing JDK: \$JDK_VERSION\" && \
    sdk install java \$JDK_VERSION && \
    sdk default java \$JDK_VERSION"

# Set JAVA_HOME to SDKMAN's current java
ENV JAVA_HOME=/root/.sdkman/candidates/java/current
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# Verify Java installation
RUN java -version

# =============================================================================
# Android SDK (conditional - only for Android projects)
# =============================================================================

ENV ANDROID_SDK_ROOT=/root/android-sdk
ENV ANDROID_HOME=${ANDROID_SDK_ROOT}
ENV PATH="${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin:${ANDROID_SDK_ROOT}/platform-tools:${PATH}"

RUN if [ "$NEEDS_ANDROID_SDK" = "true" ]; then \
    mkdir -p ${ANDROID_SDK_ROOT}/cmdline-tools && \
    cd ${ANDROID_SDK_ROOT}/cmdline-tools && \
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -O cmdline-tools.zip && \
    unzip -q cmdline-tools.zip && \
    mv cmdline-tools latest && \
    rm cmdline-tools.zip && \
    yes | ${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin/sdkmanager --licenses || true && \
    PACKAGES=$(jq -r '.android_sdk_packages | join(" ")' /config/repo.json) && \
    if [ -n "$PACKAGES" ] && [ "$PACKAGES" != "null" ]; then \
        ${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin/sdkmanager ${PACKAGES}; \
    fi; \
fi

# =============================================================================
# IntelliJ IDEA Community Edition 2025.1.1 Installation
# =============================================================================

ARG IDEA_VERSION=2025.1.1

ENV IDEA_HOME=/opt/idea
ENV PATH="${IDEA_HOME}/bin:${PATH}"

# Download IntelliJ IDEA Community Edition (auto-detect architecture)
# Note: Download to /opt instead of /tmp to avoid disk space issues
RUN mkdir -p /opt && cd /opt && \
    ARCH=$(uname -m) && \
    echo "Detected architecture: ${ARCH}" && \
    if [ "${ARCH}" = "aarch64" ] || [ "${ARCH}" = "arm64" ]; then \
        IDEA_URL="https://download.jetbrains.com/idea/ideaIC-${IDEA_VERSION}-aarch64.tar.gz"; \
    else \
        IDEA_URL="https://download.jetbrains.com/idea/ideaIC-${IDEA_VERSION}.tar.gz"; \
    fi && \
    echo "Downloading IntelliJ IDEA Community Edition from: ${IDEA_URL}" && \
    wget --progress=dot:giga "${IDEA_URL}" -O idea.tar.gz && \
    echo "Extracting IntelliJ IDEA CE..." && \
    mkdir -p /opt/idea && \
    tar -xzf idea.tar.gz -C /opt/idea --strip-components=1 && \
    rm idea.tar.gz && \
    echo "IntelliJ IDEA Community Edition installed to /opt/idea"

# =============================================================================
# IDE Configuration - Pre-accept licenses and disable first-run dialogs
# =============================================================================

ENV IDEA_CONFIG_DIR=/root/.config/JetBrains/IdeaIC2025.1
ENV IDEA_CACHE_DIR=/root/.cache/JetBrains/IdeaIC2025.1
ENV IDEA_DATA_DIR=/root/.local/share/JetBrains/IdeaIC2025.1
ENV IDEA_PLUGINS_DIR=/root/.local/share/JetBrains/IdeaIC2025.1

RUN mkdir -p ${IDEA_CONFIG_DIR} ${IDEA_CACHE_DIR} ${IDEA_DATA_DIR} ${IDEA_PLUGINS_DIR}

# Pre-configure IDE settings to skip first-run wizard
RUN mkdir -p ${IDEA_CONFIG_DIR}/options && \
    echo '<?xml version="1.0" encoding="UTF-8"?><application><component name="PropertiesComponent"><property name="ide.no.welcome.screen" value="true" /><property name="ide.first.run" value="false" /><property name="ide.splash.disabled" value="true" /></component></application>' > ${IDEA_CONFIG_DIR}/options/other.xml

# Disable consent dialogs and data sharing
RUN mkdir -p ${IDEA_CONFIG_DIR}/consentOptions && \
    echo '<?xml version="1.0" encoding="UTF-8"?><root><accepted>999.999</accepted></root>' > ${IDEA_CONFIG_DIR}/consentOptions/accepted

# Create IDE properties to disable first-run checks
RUN echo 'idea.initially.ask.config=false' > ${IDEA_CONFIG_DIR}/idea.properties && \
    echo 'idea.trust.all.projects=true' >> ${IDEA_CONFIG_DIR}/idea.properties && \
    echo 'nosplash=true' >> ${IDEA_CONFIG_DIR}/idea.properties

# =============================================================================
# Install Marketplace Plugins (Android plugins - conditional)
# =============================================================================

RUN if [ "$NEEDS_ANDROID_SDK" = "true" ]; then \
    echo "Installing Android plugin (org.jetbrains.android)..." && \
    cd /tmp && \
    wget -q "https://plugins.jetbrains.com/plugin/download?pluginId=org.jetbrains.android&version=251.25410.109" \
        -O android-plugin.zip && \
    unzip -q android-plugin.zip -d ${IDEA_PLUGINS_DIR}/ && \
    rm android-plugin.zip && \
    echo "Android plugin installed" && \
    echo "Installing Android Designer plugin (com.android.tools.design)..." && \
    wget -q "https://plugins.jetbrains.com/plugin/download?pluginId=com.android.tools.design&version=251.25410.59" \
        -O android-design-plugin.zip && \
    unzip -q android-design-plugin.zip -d ${IDEA_PLUGINS_DIR}/ && \
    rm android-design-plugin.zip && \
    echo "Android Designer plugin installed"; \
fi

# List installed plugins
RUN echo "Installed plugins:" && ls -la ${IDEA_PLUGINS_DIR}/

# =============================================================================
# Clone Repository (from build args)
# =============================================================================

WORKDIR /project

RUN git clone ${REPO_URL} . && \
    git checkout ${BASE_COMMIT} && \
    if [ -f gradlew ]; then chmod +x gradlew; fi

# =============================================================================
# Run Install Script (from config) - AFTER clone, BEFORE warmup
# =============================================================================

RUN jq -r '.install_script' /config/repo.json > /tmp/install.sh && \
    chmod +x /tmp/install.sh && \
    cd /project && \
    bash /tmp/install.sh

# =============================================================================
# Environment
# =============================================================================

ENV DISPLAY=:99
ENV FIREBENDER_AGENT_SERVER=true
ENV FIREBENDER_AGENT_SERVER_PORT=8742
ENV PROJECT_PATH=/project

EXPOSE 8742

# =============================================================================
# Warmup using IDE's native warmup command
# =============================================================================

RUN export _JAVA_OPTIONS="-Djb.consents.confirmation.enabled=false \
    -Djb.privacy.policy.text=<!--999.999--> \
    -Didea.initially.ask.config=false \
    -Dide.no.splash=true \
    -Dnosplash=true \
    -Dhidpi=false \
    -Dsun.java2d.uiScale.enabled=false \
    -Dsun.java2d.uiScale=1.0 \
    -Dide.ui.scale=1.0 \
    -Dawt.useSystemAAFontSettings=lcd \
    -Dsun.java2d.xrender=false" && \
    xvfb-run -a -s "-screen 0 1920x1080x24" \
    /opt/idea/bin/idea.sh warmup \
    --project-dir=/project

# =============================================================================
# Default to bash shell
# =============================================================================

WORKDIR /project
CMD ["/bin/bash"]
