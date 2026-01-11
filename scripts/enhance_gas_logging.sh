#!/bin/bash
#
# Enhance logging in GAS projects by adding robust error handling and logging
# This script adds logging wrappers and error handling to key functions
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GAS_ROOT="$REPO_ROOT/GoogleAppsScripts"
PROJECTS_DIR="$GAS_ROOT/projects"
LOGGER_UTILS="$GAS_ROOT/shared-utilities/LoggerUtils.gs"

# Projects to enhance
PROJECTS=(
    "waitlist-script-comprehensive"
    "veteran-tags"
    "process-refunds-exchanges"
    "create-products-new"
    "add-sold-out-product-to-waitlist"
)

log_info() {
    echo -e "\033[0;34m[INFO]\033[0m $1"
}

log_success() {
    echo -e "\033[0;32m[SUCCESS]\033[0m $1"
}

log_warning() {
    echo -e "\033[1;33m[WARNING]\033[0m $1"
}

log_error() {
    echo -e "\033[0;31m[ERROR]\033[0m $1"
}

# Check if LoggerUtils exists
if [ ! -f "$LOGGER_UTILS" ]; then
    log_error "LoggerUtils.gs not found at $LOGGER_UTILS"
    exit 1
fi

log_info "Logger utilities found at: $LOGGER_UTILS"
echo ""

# Copy LoggerUtils to each project's shared-utilities if it doesn't exist
for PROJECT_NAME in "${PROJECTS[@]}"; do
    PROJECT_DIR="$PROJECTS_DIR/$PROJECT_NAME"
    PROJECT_SHARED_UTILS="$PROJECT_DIR/src/shared-utilities"
    
    if [ ! -d "$PROJECT_DIR" ]; then
        log_warning "Project not found: $PROJECT_DIR - skipping"
        continue
    fi
    
    # Create shared-utilities directory if it doesn't exist
    if [ ! -d "$PROJECT_SHARED_UTILS" ]; then
        mkdir -p "$PROJECT_SHARED_UTILS"
        log_info "Created shared-utilities directory for $PROJECT_NAME"
    fi
    
    # Copy LoggerUtils if it doesn't exist
    if [ ! -f "$PROJECT_SHARED_UTILS/LoggerUtils.js" ] && [ ! -f "$PROJECT_SHARED_UTILS/LoggerUtils.gs" ]; then
        cp "$LOGGER_UTILS" "$PROJECT_SHARED_UTILS/LoggerUtils.gs"
        log_success "Copied LoggerUtils to $PROJECT_NAME"
    else
        log_info "LoggerUtils already exists in $PROJECT_NAME - skipping copy"
    fi
done

log_success "Logging enhancement setup complete!"
log_info "Next: Manually add logging imports and wrap functions in each project"
log_info "See COMPARISON_ARCHITECTURE_ANALYSIS.md for logging patterns"
