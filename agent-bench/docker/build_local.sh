#!/bin/bash
# =============================================================================
# Build Pre-baked Docker Images Locally
# =============================================================================
#
# Builds Docker images using pre-generated Dockerfiles from:
#   agent-bench/docker/generated/Dockerfile.{repo}
#
# Usage:
#   ./agent-bench/docker/build_local.sh anki
#   ./agent-bench/docker/build_local.sh --all
#   ./agent-bench/docker/build_local.sh --all --parallel
#   ./agent-bench/docker/build_local.sh --list
#   ./agent-bench/docker/build_local.sh --generate  # Regenerate Dockerfiles
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOCKERFILE_DIR="$SCRIPT_DIR/generated"
LOG_DIR="$SCRIPT_DIR/logs"

# Available repositories
AVAILABLE_REPOS=("anki" "coroutines" "datetime" "ktlint" "thunderbird" "wordpress")

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}"
}

print_success() { echo -e "${GREEN}$1${NC}"; }
print_error() { echo -e "${RED}ERROR: $1${NC}"; }
print_warning() { echo -e "${YELLOW}$1${NC}"; }
print_info() { echo -e "${CYAN}$1${NC}"; }

list_repos() {
    print_header "Available Repositories"
    for repo in "${AVAILABLE_REPOS[@]}"; do
        dockerfile="$DOCKERFILE_DIR/Dockerfile.$repo"
        if [ -f "$dockerfile" ]; then
            echo -e "  ${GREEN}$repo${NC}"
            echo "    Dockerfile: $dockerfile"
        else
            echo -e "  ${YELLOW}$repo${NC} (Dockerfile missing - run --generate)"
        fi
    done
    echo ""
}

generate_dockerfiles() {
    print_header "Generating Dockerfiles"
    python3 "$SCRIPT_DIR/generate_dockerfiles.py"
}

# Build a single image
build_image() {
    local repo_name="$1"
    local no_cache="$2"
    local log_file="$3"
    
    local dockerfile="$DOCKERFILE_DIR/Dockerfile.$repo_name"
    
    if [ ! -f "$dockerfile" ]; then
        echo "ERROR: Dockerfile not found: $dockerfile" >> "$log_file"
        echo "Run: ./build_local.sh --generate" >> "$log_file"
        return 1
    fi
    
    {
        echo "============================================================"
        echo "Building $repo_name"
        echo "============================================================"
        echo "  Dockerfile: $dockerfile"
        echo "  Image tag:  kotlin-bench-$repo_name"
        echo ""
    } >> "$log_file"
    
    local docker_args=()
    if [ "$no_cache" = "true" ]; then
        docker_args+=(--no-cache)
    fi
    
    cd "$PROJECT_ROOT"
    if docker build \
        -f "$dockerfile" \
        "${docker_args[@]}" \
        -t "kotlin-bench-$repo_name" \
        . >> "$log_file" 2>&1; then
        echo "" >> "$log_file"
        echo "SUCCESS: Image built: kotlin-bench-$repo_name" >> "$log_file"
        return 0
    else
        echo "" >> "$log_file"
        echo "FAILED: Build failed for $repo_name" >> "$log_file"
        return 1
    fi
}

# Build images in parallel
build_parallel() {
    local no_cache="$1"
    shift
    local repos=("$@")
    local num_repos=${#repos[@]}
    
    print_header "Building $num_repos images in parallel"
    
    mkdir -p "$LOG_DIR"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    local pids=()
    local log_files=()
    
    for i in "${!repos[@]}"; do
        local repo="${repos[$i]}"
        local log_file="$LOG_DIR/${repo}_${timestamp}.log"
        log_files[$i]="$log_file"
        
        print_info "  Starting: $repo"
        build_image "$repo" "$no_cache" "$log_file" &
        pids[$i]=$!
    done
    
    echo ""
    print_info "Waiting for builds to complete..."
    echo ""
    
    local results=()
    local failed=()
    local passed=()
    
    for i in "${!repos[@]}"; do
        local repo="${repos[$i]}"
        local pid="${pids[$i]}"
        if wait "$pid"; then
            results[$i]="passed"
            passed+=("$repo")
            print_success "  Completed: $repo"
        else
            results[$i]="failed"
            failed+=("$repo")
            print_error "  Failed: $repo"
        fi
    done
    
    echo ""
    print_header "Build Summary"
    echo "  Total:  $num_repos"
    echo "  Passed: ${#passed[@]}"
    echo "  Failed: ${#failed[@]}"
    echo ""
    
    for i in "${!repos[@]}"; do
        local repo="${repos[$i]}"
        local status="${results[$i]}"
        local log="${log_files[$i]}"
        if [ "$status" = "passed" ]; then
            echo -e "  ${GREEN}$repo${NC}: PASSED"
        else
            echo -e "  ${RED}$repo${NC}: FAILED"
        fi
        echo "    Log: $log"
    done
    
    if [ ${#failed[@]} -gt 0 ]; then
        echo ""
        print_error "Failed repos: ${failed[*]}"
        return 1
    fi
    
    print_success "\nAll builds completed!"
    return 0
}

# Build images sequentially
build_serial() {
    local no_cache="$1"
    shift
    local repos=("$@")
    
    print_header "Building ${#repos[@]} images sequentially"
    
    mkdir -p "$LOG_DIR"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    local failed=()
    for repo in "${repos[@]}"; do
        local log_file="$LOG_DIR/${repo}_${timestamp}.log"
        
        print_header "Building $repo"
        echo "  Dockerfile: $DOCKERFILE_DIR/Dockerfile.$repo"
        echo "  Log: $log_file"
        echo ""
        
        if build_image "$repo" "$no_cache" "$log_file"; then
            print_success "Image built: kotlin-bench-$repo"
            echo ""
            echo "To run:"
            echo "  docker run -it --rm -p 8742:8742 kotlin-bench-$repo"
        else
            print_error "Build failed for $repo"
            echo "See log: $log_file"
            failed+=("$repo")
        fi
        echo ""
    done
    
    print_header "Build Summary"
    echo "  Total:  ${#repos[@]}"
    echo "  Passed: $((${#repos[@]} - ${#failed[@]}))"
    echo "  Failed: ${#failed[@]}"
    
    if [ ${#failed[@]} -gt 0 ]; then
        print_error "Failed repos: ${failed[*]}"
        return 1
    fi
    
    print_success "\nAll builds completed!"
    return 0
}

# =============================================================================
# Main
# =============================================================================

usage() {
    echo "Usage: $0 [OPTIONS] [REPO_NAME...]"
    echo ""
    echo "Build pre-baked Docker images using generated Dockerfiles."
    echo ""
    echo "Arguments:"
    echo "  REPO_NAME     Repository name (e.g., anki, coroutines, ktlint)"
    echo ""
    echo "Options:"
    echo "  --list        List available repositories"
    echo "  --all         Build all repositories"
    echo "  --parallel    Build in parallel (default for multiple repos)"
    echo "  --serial      Build sequentially"
    echo "  --no-cache    Build without Docker cache"
    echo "  --generate    Regenerate Dockerfiles from configs"
    echo "  -h, --help    Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 anki                    # Build single repo"
    echo "  $0 anki coroutines         # Build multiple in parallel"
    echo "  $0 --all                   # Build all in parallel"
    echo "  $0 --generate --all        # Regenerate then build all"
    echo ""
    echo "Available: ${AVAILABLE_REPOS[*]}"
}

# Parse arguments
NO_CACHE="false"
BUILD_ALL="false"
PARALLEL=""
GENERATE="false"
REPOS_TO_BUILD=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --list)
            list_repos
            exit 0
            ;;
        --all)
            BUILD_ALL="true"
            shift
            ;;
        --parallel)
            PARALLEL="true"
            shift
            ;;
        --serial)
            PARALLEL="false"
            shift
            ;;
        --no-cache)
            NO_CACHE="true"
            shift
            ;;
        --generate)
            GENERATE="true"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            print_error "Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            REPOS_TO_BUILD+=("$1")
            shift
            ;;
    esac
done

# Generate Dockerfiles if requested
if [ "$GENERATE" = "true" ]; then
    generate_dockerfiles
    echo ""
fi

# Determine what to build
if [ "$BUILD_ALL" = "true" ]; then
    REPOS_TO_BUILD=("${AVAILABLE_REPOS[@]}")
fi

if [ ${#REPOS_TO_BUILD[@]} -eq 0 ]; then
    if [ "$GENERATE" = "true" ]; then
        exit 0  # Just generated, nothing to build
    fi
    print_error "No repository specified"
    echo ""
    usage
    exit 1
fi

# Auto-detect parallel mode
if [ -z "$PARALLEL" ]; then
    if [ ${#REPOS_TO_BUILD[@]} -gt 1 ]; then
        PARALLEL="true"
    else
        PARALLEL="false"
    fi
fi

# Validate repos
for repo in "${REPOS_TO_BUILD[@]}"; do
    valid="false"
    for available in "${AVAILABLE_REPOS[@]}"; do
        if [ "$repo" = "$available" ]; then
            valid="true"
            break
        fi
    done
    if [ "$valid" = "false" ]; then
        print_error "Unknown repository: $repo"
        echo "Available: ${AVAILABLE_REPOS[*]}"
        exit 1
    fi
done

# Check Dockerfiles exist
missing=()
for repo in "${REPOS_TO_BUILD[@]}"; do
    if [ ! -f "$DOCKERFILE_DIR/Dockerfile.$repo" ]; then
        missing+=("$repo")
    fi
done

if [ ${#missing[@]} -gt 0 ]; then
    print_warning "Missing Dockerfiles for: ${missing[*]}"
    echo "Generating Dockerfiles..."
    generate_dockerfiles
    echo ""
fi

# Check dependencies
if ! command -v docker &> /dev/null; then
    print_error "docker is required but not installed"
    exit 1
fi

# Build
if [ "$PARALLEL" = "true" ]; then
    build_parallel "$NO_CACHE" "${REPOS_TO_BUILD[@]}"
else
    build_serial "$NO_CACHE" "${REPOS_TO_BUILD[@]}"
fi
