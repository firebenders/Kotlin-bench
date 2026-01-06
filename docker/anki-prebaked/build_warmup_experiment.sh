#!/bin/bash
# Build script for the warmup experiment Dockerfile
#
# This builds a Docker image that uses Android Studio's native warmup command
# instead of the Firebender plugin's warmupProject gradle task.
#
# Usage:
#   ./build_warmup_experiment.sh
#
# Run the container:
#   docker run -it --rm \
#     -v /path/to/firebender.zip:/plugins/firebender.zip \
#     -e FIREBENDER_PLUGIN_PATH=/plugins/firebender.zip \
#     anki-warmup-experiment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "Building warmup experiment Docker image..."
echo "Repository root: ${REPO_ROOT}"

cd "${REPO_ROOT}"

docker build \
    -f docker/anki-prebaked/Dockerfile.warmup-experiment \
    -t anki-warmup-experiment \
    .

echo ""
echo "Build complete!"
echo ""
echo "To run the container with the Firebender plugin:"
echo ""
echo "  docker run -it --rm \\"
echo "    -v /path/to/firebender.zip:/plugins/firebender.zip \\"
echo "    -e FIREBENDER_PLUGIN_PATH=/plugins/firebender.zip \\"
echo "    -p 8742:8742 \\"
echo "    anki-warmup-experiment"
echo ""
echo "The container will:"
echo "  1. Install the Firebender plugin at runtime"
echo "  2. Start Android Studio with the pre-warmed project"
echo ""
