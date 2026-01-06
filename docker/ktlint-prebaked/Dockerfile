# ktlint Pre-baked Docker Image
# 
# Config loaded from: agent-bench/config/ktlint.json (single source of truth)
#
# IMPORTANT: Must be built on x86_64 Linux (warmupProject needs real JBR)
#
# Build:
#   modal run docker/ktlint-prebaked/build_modal.py

FROM ubuntu:22.04

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

COPY agent-bench/config/ktlint.json /config/ktlint.json

# =============================================================================
# Java 21 (for IntelliJ)
# =============================================================================

RUN apt-get update && apt-get install -y openjdk-21-jdk \
    && rm -rf /var/lib/apt/lists/*

RUN JAVA_DIR=$(ls -d /usr/lib/jvm/java-21-openjdk-* | head -1) && \
    ln -sf ${JAVA_DIR} /usr/lib/jvm/java-21

ENV JAVA_HOME=/usr/lib/jvm/java-21
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# =============================================================================
# SDKMAN + Project JDK (from config)
# =============================================================================

ENV SDKMAN_DIR=/root/.sdkman

RUN curl -s "https://get.sdkman.io" | bash

# Install JDK version from config
RUN JDK_VERSION=$(jq -r '.jdk_version' /config/ktlint.json) && \
    bash -c "source $SDKMAN_DIR/bin/sdkman-init.sh && \
    sdk install java ${JDK_VERSION} && \
    sdk default java ${JDK_VERSION}"

# =============================================================================
# Clone Firebender
# =============================================================================

ARG FIREBENDER_BRANCH=aman/firebender-harness
ARG GITHUB_TOKEN

WORKDIR /firebender

RUN if [ -n "${GITHUB_TOKEN}" ]; then \
        git clone --branch ${FIREBENDER_BRANCH} --single-branch \
            https://${GITHUB_TOKEN}@github.com/firebenders/android-studio-copilot.git . && \
        chmod +x gradlew ; \
    else \
        echo "ERROR: GITHUB_TOKEN not set." && exit 1 ; \
    fi

RUN ./gradlew --version --no-daemon

# =============================================================================
# Clone ktlint (commit from config)
# =============================================================================

WORKDIR /project

RUN REPO_URL=$(jq -r '.repo_url' /config/ktlint.json) && \
    BASE_COMMIT=$(jq -r '.base_commit' /config/ktlint.json) && \
    git clone ${REPO_URL} . && \
    git checkout ${BASE_COMMIT} && \
    chmod +x gradlew

# =============================================================================
# Run Install Script (from config) - AFTER clone, BEFORE warmup
# =============================================================================

RUN jq -r '.install_script' /config/ktlint.json > /tmp/install.sh && \
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
# Warmup (AFTER install script has patched the project)
# =============================================================================

WORKDIR /firebender

RUN export _JAVA_OPTIONS="-Djb.consents.confirmation.enabled=false -Djb.privacy.policy.text=<!--999.999--> -Didea.initially.ask.config=false -Dide.no.splash=true -Dnosplash=true -Dhidpi=false -Dsun.java2d.uiScale.enabled=false -Dsun.java2d.uiScale=1.0 -Dide.ui.scale=1.0 -Dawt.useSystemAAFontSettings=lcd -Dsun.java2d.xrender=false" && \
    xvfb-run -a -s "-screen 0 1920x1080x24" \
    ./gradlew warmupProject \
    -PprojectPath=/project \
    -PskipObfuscation=true \
    --no-daemon \
    --no-configuration-cache


