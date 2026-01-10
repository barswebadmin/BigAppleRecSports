#!/bin/bash
#
# Unified GAS pull script with change detection (dry-run support)
# Usage: pull.sh <project-name> [--dry-run|--compare-only]
#

set -e

# Source shared helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/shared-helpers.sh"

# Parse arguments
parse_clasp_args "$@"

# Get paths
get_project_paths "$PROJECT_NAME" "$SCRIPT_DIR"

# Validate project
if [ ! -d "$PROJECT_DIR" ]; then
    log_error "Project directory not found: $PROJECT_DIR"
    exit 1
fi

log_info "📥 Preparing to pull: $PROJECT_NAME"

# Check if project uses esbuild
check_project_type "$PROJECT_DIR" "HAS_ESBUILD"

# Validate project structure
if ! validate_project_structure "$PROJECT_DIR" "$HAS_ESBUILD"; then
    exit 1
fi

# Build local project first (only if using esbuild)
if [ "$HAS_ESBUILD" = true ]; then
    if ! build_gas_project "$PROJECT_DIR" "$GAS_ROOT"; then
        exit 1
    fi
fi

# Setup temp directories
TEMP_DIRS=()
TEMP_PULL_DIR="$PROJECT_DIR/.clasp_pull_temp"
TEMP_DIRS+=("$TEMP_PULL_DIR")

# Clean up any existing temp directories
for temp_dir in "${TEMP_DIRS[@]}"; do
    if [ -d "$temp_dir" ]; then
        cleanup_temp_dir "$temp_dir"
    fi
done

# Setup cleanup trap for all temp dirs
setup_multi_temp_workspace "TEMP_DIRS"

# Create temp directory for clasp pull
mkdir -p "$TEMP_PULL_DIR"

# Copy .clasp.json to temp with normalized rootDir
if [ -f "$PROJECT_DIR/.clasp.json" ]; then
    normalize_clasp_json "$PROJECT_DIR/.clasp.json" "$TEMP_PULL_DIR/.clasp.json"
else
    log_error ".clasp.json not found in project directory"
    exit 1
fi

# Pull from remote
log_info "📥 Pulling Code.js from Google Apps Script..."

cd "$TEMP_PULL_DIR"

if ! command -v clasp >/dev/null 2>&1; then
    log_error "clasp command not found. Please install clasp CLI."
    exit 1
fi

execute_clasp "pull" CLASP_OUTPUT CLASP_EXIT_CODE

if [ $CLASP_EXIT_CODE -ne 0 ]; then
    log_error "Failed to pull code from Google Apps Script"
    log_error "clasp output: $CLASP_OUTPUT"
    exit 1
fi

if [ -n "$CLASP_OUTPUT" ]; then
    log_info "clasp output: $CLASP_OUTPUT"
fi

if [ ! -f "Code.js" ]; then
    log_error "Code.js not found after pull"
    exit 1
fi

log_success "Code.js pulled successfully"

# Prepare comparison paths
prepare_comparison_paths "$PROJECT_DIR" "$TEMP_PULL_DIR" "$HAS_ESBUILD" "LOCAL_COMPARE_PATH" "REMOTE_COMPARE_PATH"

# Add additional temp dirs to cleanup list
if [ "$HAS_ESBUILD" = true ]; then
    TEMP_BUILD_COMPARE_DIR="$PROJECT_DIR/.clasp_pull_build_compare"
    TEMP_DIRS+=("$TEMP_BUILD_COMPARE_DIR")
else
    TEMP_ORGANIZED_DIR="$PROJECT_DIR/.clasp_pull_organized"
    TEMP_DIRS+=("$TEMP_ORGANIZED_DIR")
fi

# Compare local build vs remote Code.js
if ! run_comparison "$LOCAL_COMPARE_PATH" "$REMOTE_COMPARE_PATH" "pull" "HAS_CHANGES"; then
    exit 1
fi

if [ "$HAS_CHANGES" = false ]; then
    log_success "✅ No differences detected between local build and remote"
else
    log_info "📊 Differences shown above"
fi

# Cleanup temp directories
for temp_dir in "${TEMP_DIRS[@]}"; do
    if [ -n "$temp_dir" ] && [ -d "$temp_dir" ]; then
        cleanup_temp_dir "$temp_dir"
    fi
done

log_info "Comparison complete - exiting without applying changes"
exit 0
