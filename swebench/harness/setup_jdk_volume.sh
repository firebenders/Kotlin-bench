#!/bin/bash
set -e

# Function to handle errors
handle_error() {
    echo "Error occurred at line $1"
    # Remove the in-progress marker on error
    rm -f /jdk_volume/.jdk_setup_in_progress
    exit 1
}

# Set up trap to catch errors
trap 'handle_error $LINENO' ERR

echo "====== SDKMAN JDK Volume Setup ======"
echo "Starting JDK volume initialization"

# Create JDK directory in the volume
echo "Creating JDK volume directories..."
mkdir -p /jdk_volume
mkdir -p /jdk_volume/candidates/java

# Mark script as running
touch /jdk_volume/.jdk_setup_in_progress

# If JDKs are already installed in the volume, check but continue
if [ -f /jdk_volume/.jdk_setup_complete ]; then
    echo "JDK volume already has a setup_complete marker."
    echo "Will check for missing JDK versions."
fi

# Configure SDKMAN to use volume for installations
echo "Configuring SDKMAN to use volume for installations..."

# Create symlink to point SDKMAN candidates to the volume
if [ ! -L "$HOME/.sdkman/candidates/java" ]; then
    # Backup existing java candidates if any
    if [ -d "$HOME/.sdkman/candidates/java" ]; then
        echo "Backing up existing java candidates..."
        mv "$HOME/.sdkman/candidates/java" "$HOME/.sdkman/candidates/java.bak"
    fi
    
    # Create symlink
    echo "Creating symlink from SDKMAN to JDK volume..."
    ln -sf /jdk_volume/candidates/java "$HOME/.sdkman/candidates/java"
    echo "Created symlink to JDK volume"
else
    echo "SDKMAN java symlink already exists, using existing configuration."
fi

# Ensure SDKMAN directories exist
mkdir -p "$HOME/.sdkman/tmp"
mkdir -p "$HOME/.sdkman/var"
mkdir -p "$HOME/.sdkman/etc"

# Source SDKMAN - fail if cannot source
echo "Initializing SDKMAN..."
if [ -f "$HOME/.sdkman/bin/sdkman-init.sh" ]; then
    source "$HOME/.sdkman/bin/sdkman-init.sh"
    echo "SDKMAN initialized successfully."
else
    echo "ERROR: SDKMAN init script not found!"
    handle_error $LINENO
fi

# Verify SDKMAN is working
echo "Verifying SDKMAN installation..."
if ! command -v sdk &> /dev/null; then
    echo "ERROR: SDKMAN 'sdk' command not available!"
    handle_error $LINENO
fi

# The script is designed to be called with specific JDK versions
# JDK installation commands will be inserted here by the Python script

# Mark setup as complete
echo "Finalizing JDK volume setup..."
rm -f /jdk_volume/.jdk_setup_in_progress
touch /jdk_volume/.jdk_setup_complete

echo "JDK volume setup complete. Installed versions:"
ls -la /jdk_volume/candidates/java/
echo "====== JDK Volume Setup Complete ======" 