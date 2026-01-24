#!/bin/bash
#
# Unified GAS push script with change detection (dry-run support)
# Usage: push.sh <project-name> [--dry-run|--compare-only]
#

set -e

# Source shared helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/google/shared_helpers.sh"

# Parse arguments
parse_clasp_args "$@"

# Get paths
get_project_paths "$PROJECT_NAME" "$SCRIPT_DIR"

# Validate project
if [ ! -d "$PROJECT_DIR" ]; then
    log_error "Project directory not found: $PROJECT_DIR"
    exit 1
fi

log_info "🚀 Preparing to push: $PROJECT_NAME"

# Setup temp workspace
setup_temp_workspace "$PROJECT_DIR" "push" "TEMP_BUILD_DIR"

# Build project
if ! build_gas_project "$PROJECT_DIR" "$GAS_ROOT"; then
    cleanup_temp_dir "$TEMP_BUILD_DIR"
    exit 1
fi

# Copy build artifacts to temp directory
if ! copy_build_artifacts "$PROJECT_DIR" "$TEMP_BUILD_DIR"; then
    cleanup_temp_dir "$TEMP_BUILD_DIR"
    exit 1
fi

# Compare local build vs remote
REMOTE_AHEAD=false
LOCAL_AHEAD=false
if ! run_comparison "$TEMP_BUILD_DIR" "" "push" "HAS_CHANGES" "$PROJECT_NAME" "REMOTE_AHEAD" "LOCAL_AHEAD"; then
    cleanup_temp_dir "$TEMP_BUILD_DIR"
    exit 1
fi

# If compare-only mode, exit after showing diff
if [ "$IS_COMPARE_ONLY" = true ]; then
    if [ "$HAS_CHANGES" = false ]; then
        log_success "✅ No differences detected between local build and remote"
    else
        log_info "📊 Differences shown above"
        if [ "$REMOTE_AHEAD" = true ]; then
            log_warning "⚠️  Remote is ahead of local"
        fi
    fi
    cleanup_temp_dir "$TEMP_BUILD_DIR"
    exit 0
fi

# Prompt user for confirmation (handles remote-ahead detection)
if ! prompt_user_confirmation "$HAS_CHANGES" "$IS_DRY_RUN" "push" "$REMOTE_AHEAD" "$PROJECT_NAME"; then
    cleanup_temp_dir "$TEMP_BUILD_DIR"
    exit 0
fi

# Push (if not dry run)
if [ "$IS_DRY_RUN" = true ]; then
    log_info "🔍 DRY RUN: Would push to remote using clasp"
    log_info "🔍 DRY RUN: Would clean up build/ directory on success"
else
    log_info "☁️  Pushing to Google Apps Script..."
    
    cd "$TEMP_BUILD_DIR"
    
    execute_clasp "push --force" CLASP_OUTPUT CLASP_EXIT_CODE
    
    if [ $CLASP_EXIT_CODE -ne 0 ]; then
        log_error "Failed to push code to Google Apps Script"
        log_error "clasp output: $CLASP_OUTPUT"
        cleanup_temp_dir "$TEMP_BUILD_DIR"
        exit 1
    fi
    
    log_success "Code pushed successfully!"
    
    # Clean up build directory on success
    clean_gas_project "$PROJECT_DIR" "$SCRIPT_DIR"
fi

# Cleanup temp directory
cleanup_temp_dir "$TEMP_BUILD_DIR"

if [ "$IS_DRY_RUN" = true ]; then
    log_success "🔍 DRY RUN complete - No changes were made"
else
    log_success "Push completed successfully!"
fi
