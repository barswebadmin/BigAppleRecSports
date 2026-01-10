#!/bin/bash
#
# Google Apps Script Deployment Script (Push + Version Management)
# Usage: deploy.sh <project-name>
#
# Always performs: push code + cleanup old versions + create new deployment
#

set -e

# Source shared helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/shared-helpers.sh"

# Parse project name
PROJECT_NAME="${1:-}"

if [ -z "$PROJECT_NAME" ]; then
    log_error "Project name required"
    echo "Usage: $0 <project-name>"
    echo ""
    echo "Available projects:"
    GAS_ROOT=$(get_gas_root "$SCRIPT_DIR")
    discover_gas_projects "$GAS_ROOT" | while read -r project; do
        echo "  - $project"
    done
    exit 1
fi

# Get paths
get_project_paths "$PROJECT_NAME" "$SCRIPT_DIR"

# Validate project
if ! validate_project "$PROJECT_NAME" "$GAS_ROOT"; then
    exit 1
fi

# Change to project directory
cd "$PROJECT_DIR"
log_info "Working in project: $PROJECT_NAME"

# Check clasp authentication
if ! check_clasp_auth; then
    exit 1
fi

# Check for doGet/doPost functions (warning only)
check_webapp_changes "$GAS_ROOT"

# Step 1: Push code to Google Apps Script
log_info "📤 Step 1: Pushing code to Google Apps Script..."
bash "$GAS_ROOT/remote-sync-tools/push.sh" "$PROJECT_NAME"

log_success "Code pushed successfully"

# Step 2: Cleanup old versions if needed
cleanup_old_deployments 200 190 10

# Step 3: Create new deployment
create_deployment "$PROJECT_DIR" "DEPLOYMENT_ID" "VERSION_NUMBER" "WEB_APP_URL"

log_success "🎉 Deployment completed for project: $PROJECT_NAME"
