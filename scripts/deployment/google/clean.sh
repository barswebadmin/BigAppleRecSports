#!/bin/bash
#
# Clean build artifacts and temporary files for a GAS project
# Usage: clean.sh <project-dir>
#

set -e

# Source shared helpers for logging
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/shared_helpers.sh"

PROJECT_DIR="${1:-}"

if [ -z "$PROJECT_DIR" ]; then
    log_error "Project directory required"
    echo "Usage: $0 <project-dir>"
    exit 1
fi

if [ ! -d "$PROJECT_DIR" ]; then
    log_error "Project directory not found: $PROJECT_DIR"
    exit 1
fi

log_info "🧹 Cleaning project: $(basename "$PROJECT_DIR")"

CLEANED_COUNT=0

# Clean deploy temp directories
if [ -d "$PROJECT_DIR/deploy_temp" ]; then
    log_info "  Removing deploy_temp/ directory..."
    rm -rf "$PROJECT_DIR/deploy_temp"
    CLEANED_COUNT=$((CLEANED_COUNT + 1))
fi

# Clean legacy build directory (for backwards compatibility)
if [ -d "$PROJECT_DIR/build" ]; then
    log_info "  Removing legacy build/ directory..."
    rm -rf "$PROJECT_DIR/build"
    CLEANED_COUNT=$((CLEANED_COUNT + 1))
fi

# Clean temp directories (clasp operations)
TEMP_PATTERNS=(
    ".clasp_push_temp"
    ".clasp_pull_temp"
    ".clasp_pull_organized"
    ".clasp_push_compare"
    ".clasp_pull_compare"
    ".clasp_pull_build_compare"
    ".clasp_pull_backup"
    "pull_validation"
)

for pattern in "${TEMP_PATTERNS[@]}"; do
    if [ -d "$PROJECT_DIR/$pattern" ] || [ -f "$PROJECT_DIR/$pattern" ]; then
        log_info "  Removing $pattern..."
        rm -rf "$PROJECT_DIR/$pattern"
        CLEANED_COUNT=$((CLEANED_COUNT + 1))
    fi
done

if [ $CLEANED_COUNT -eq 0 ]; then
    log_info "✅ No files to clean"
else
    log_success "✅ Cleaned $CLEANED_COUNT item(s)"
fi

exit 0
