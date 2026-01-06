# Anki-Android Pre-baked Docker Image
# 
# This image uses IntelliJ IDEA Community Edition 2025.1.1 and handles both
# ARM64 (Mac) and x86_64 (Modal/Linux) architectures automatically.
#
# Matches Firebender plugin's target platform:
#   platformType = IC
#   platformVersion = 2025.1.1
#   pluginSinceBuild = 251
#
# Pre-installed Plugins:
#   - org.jetbrains.android:251.25410.109 (Android plugin)
#   - com.android.tools.design:251.25410.59 (Android Designer)
#   - Bundled: java, kotlin, gradle, terminal, git4idea, json
#
# NOTE: Firebender plugin is NOT included - it's installed at runtime
# to allow easy version swapping. See run_eval.py for installation logic.
#
# Build:
#   docker build -f docker/anki-prebaked/Dockerfile -t anki-prebaked .
#
# Run:
#   docker run -it --rm -p 8742:8742 anki-prebaked

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

COPY agent-bench/config/anki.json /config/anki.json

# =============================================================================
# Java 17 (matches project requirements)
# =============================================================================

RUN apt-get update && apt-get install -y openjdk-17-jdk \
    && rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME dynamically based on architecture
RUN JAVA_DIR=$(ls -d /usr/lib/jvm/java-17-openjdk-* 2>/dev/null | head -1) && \
    if [ -n "$JAVA_DIR" ]; then \
        ln -sf "$JAVA_DIR" /usr/lib/jvm/java-17; \
    fi

ENV JAVA_HOME=/usr/lib/jvm/java-17
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# =============================================================================
# Android SDK (command line tools are architecture-independent)
# =============================================================================

ENV ANDROID_SDK_ROOT=/root/android-sdk
ENV ANDROID_HOME=${ANDROID_SDK_ROOT}
ENV PATH="${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin:${ANDROID_SDK_ROOT}/platform-tools:${PATH}"

RUN mkdir -p ${ANDROID_SDK_ROOT}/cmdline-tools && \
    cd ${ANDROID_SDK_ROOT}/cmdline-tools && \
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -O cmdline-tools.zip && \
    unzip -q cmdline-tools.zip && \
    mv cmdline-tools latest && \
    rm cmdline-tools.zip

RUN yes | ${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin/sdkmanager --licenses || true

# Install SDK packages from config
RUN PACKAGES=$(jq -r '.android_sdk_packages | join(" ")' /config/anki.json) && \
    ${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin/sdkmanager ${PACKAGES}

# =============================================================================
# IntelliJ IDEA Community Edition 2025.1.1 Installation
# =============================================================================

ARG IDEA_VERSION=2025.1.1

ENV IDEA_HOME=/opt/idea
ENV PATH="${IDEA_HOME}/bin:${PATH}"

# Download IntelliJ IDEA Community Edition (auto-detect architecture)
# ARM64: ideaIC-VERSION-aarch64.tar.gz
# x86_64: ideaIC-VERSION.tar.gz
RUN cd /tmp && \
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

# IntelliJ CE config directories (Linux paths) - 2025.1
# Community Edition uses IdeaIC* directories (not IntelliJIdea*)
ENV IDEA_CONFIG_DIR=/root/.config/JetBrains/IdeaIC2025.1
ENV IDEA_CACHE_DIR=/root/.cache/JetBrains/IdeaIC2025.1
ENV IDEA_DATA_DIR=/root/.local/share/JetBrains/IdeaIC2025.1
# Plugins go DIRECTLY under DATA_DIR (not in a /plugins subdirectory)
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
# Install Marketplace Plugins (Android and Android Designer)
# =============================================================================
# These plugins are required for Android development in IntelliJ CE.
# Download from JetBrains Plugin Repository and extract to plugins directory.

# Android Plugin (org.jetbrains.android)
RUN echo "Installing Android plugin (org.jetbrains.android)..." && \
    cd /tmp && \
    wget -q "https://plugins.jetbrains.com/plugin/download?pluginId=org.jetbrains.android&version=251.25410.109" \
        -O android-plugin.zip && \
    unzip -q android-plugin.zip -d ${IDEA_PLUGINS_DIR}/ && \
    rm android-plugin.zip && \
    echo "Android plugin installed"

# Android Designer Plugin (com.android.tools.design)
RUN echo "Installing Android Designer plugin (com.android.tools.design)..." && \
    cd /tmp && \
    wget -q "https://plugins.jetbrains.com/plugin/download?pluginId=com.android.tools.design&version=251.25410.59" \
        -O android-design-plugin.zip && \
    unzip -q android-design-plugin.zip -d ${IDEA_PLUGINS_DIR}/ && \
    rm android-design-plugin.zip && \
    echo "Android Designer plugin installed"

# List installed plugins
RUN echo "Installed plugins:" && ls -la ${IDEA_PLUGINS_DIR}/

# =============================================================================
# Clone Anki-Android (commit from config)
# =============================================================================

WORKDIR /project

RUN BASE_COMMIT=$(jq -r '.base_commit' /config/anki.json) && \
    git clone https://github.com/ankidroid/Anki-Android.git . && \
    git checkout ${BASE_COMMIT} && \
    chmod +x gradlew

# =============================================================================
# Run Install Script (from config) - AFTER clone, BEFORE warmup
# =============================================================================

RUN jq -r '.install_script' /config/anki.json > /tmp/install.sh && \
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
# The warmup command will:
# 1. Download all Gradle dependencies → cached in ~/.gradle/caches/
# 2. Run Gradle sync → generates .gradle/ project cache
# 3. Build IDE indices → cached in ~/.cache/JetBrains/IdeaIC2025.1/
#
# NOTE: Firebender plugin is NOT installed during warmup - it's added at runtime.

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
