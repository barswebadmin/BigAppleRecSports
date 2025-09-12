#!/bin/bash

# Google Apps Script Project Deployment Script
# Usage: ./deploy-project.sh [project-name] [--force]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

function log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

function log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

function log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

function log_error() {
    echo -e "${RED}❌ $1${NC}"
}

function show_help() {
    echo "Google Apps Script Deployment Tool"
    echo ""
    echo "Usage: $0 [project-name] [options]"
    echo ""
    echo "Arguments:"
    echo "  project-name    Name of the GAS project to deploy (optional - will auto-detect)"
    echo ""
    echo "Options:"
    echo "  --force         Force deployment even if no changes detected"
    echo "  --version-only  Only create a new version, don't deploy"
    echo "  --cleanup-only  Only cleanup old versions, don't deploy"
    echo "  --help          Show this help message"
    echo ""
    echo "Available projects:"
    for dir in projects/*/; do
        if [ -f "$dir.clasp.json" ]; then
            echo "  - $(basename "${dir%/}")"
        fi
    done
}

# Parse command line arguments
PROJECT_NAME=""
FORCE_DEPLOY=false
VERSION_ONLY=false
CLEANUP_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_DEPLOY=true
            shift
            ;;
        --version-only)
            VERSION_ONLY=true
            shift
            ;;
        --cleanup-only)
            CLEANUP_ONLY=true
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        -*)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
        *)
            if [ -z "$PROJECT_NAME" ]; then
                PROJECT_NAME="$1"
            else
                log_error "Multiple project names specified"
                exit 1
            fi
            shift
            ;;
    esac
done

# Auto-detect project if not specified
if [ -z "$PROJECT_NAME" ]; then
    # Check if we're inside a project directory
    if [ -f ".clasp.json" ]; then
        # We're in a project directory, extract project name
        CURRENT_DIR=$(basename "$(pwd)")
        PARENT_DIR=$(basename "$(dirname "$(pwd)")")
        if [ "$PARENT_DIR" = "projects" ]; then
            PROJECT_NAME="$CURRENT_DIR"
            log_info "Auto-detected project: $PROJECT_NAME"
        else
            log_error "Auto-detection failed: not in a projects subdirectory"
            show_help
            exit 1
        fi
    else
        log_error "No project specified and no .clasp.json found in current directory"
        show_help
        exit 1
    fi
fi

# Validate project exists (check in projects/ directory)
PROJECT_PATH="projects/$PROJECT_NAME"
if [ ! -d "$PROJECT_PATH" ]; then
    log_error "Project directory '$PROJECT_PATH' not found"
    exit 1
fi

if [ ! -f "$PROJECT_PATH/.clasp.json" ]; then
    log_error "No .clasp.json found in '$PROJECT_PATH'"
    exit 1
fi

# Change to project directory
cd "$PROJECT_PATH"
log_info "Working in project: $PROJECT_NAME"

# Check clasp authentication
if ! clasp status >/dev/null 2>&1; then
    log_error "Not logged in to clasp. Run 'clasp login' first."
    exit 1
fi

# Check for doGet/doPost functions
DOGET_DOPOST_FILES=()
while IFS= read -r -d '' file; do
    if grep -l "function\s\+do\(Get\|Post\)" "$file" >/dev/null 2>&1; then
        DOGET_DOPOST_FILES+=("$file")
    fi
done < <(find . -name "*.gs" -print0)

if [ ${#DOGET_DOPOST_FILES[@]} -gt 0 ]; then
    log_warning "doGet/doPost functions detected in:"
    for file in "${DOGET_DOPOST_FILES[@]}"; do
        echo "  - $file"
    done
    log_warning "These changes require deployment to take effect in web apps!"
fi

# Check for uncommitted changes
if command -v git >/dev/null 2>&1 && [ -d ../.git ]; then
    if ! git diff --quiet HEAD -- . || ! git diff --cached --quiet -- .; then
        log_warning "Uncommitted changes detected in this project"
        if [ "$FORCE_DEPLOY" != true ]; then
            read -p "Continue with deployment? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "Deployment cancelled"
                exit 0
            fi
        fi
    fi
fi

# Push code to Google Apps Script
if [ "$CLEANUP_ONLY" != true ]; then
    log_info "Pushing code to Google Apps Script..."
    
    if [ -f clasp_helpers.sh ]; then
        log_info "Using project-specific clasp helper script..."
        ./clasp_helpers.sh push
    else
        log_info "Using direct clasp push..."
        clasp push --force
    fi
    
    log_success "Code pushed successfully"
fi

# Run version management and deployment
if [ "$VERSION_ONLY" == true ]; then
    log_info "Creating new version only..."
    clasp version "Manual version $(date '+%Y-%m-%d %H:%M:%S')"
elif [ "$CLEANUP_ONLY" == true ]; then
    log_info "Running version cleanup only..."
    PROJECT_NAME="$PROJECT_NAME" node ../../scripts/manage-versions-and-deploy.js --cleanup-only
else
    log_info "Running full deployment with version management..."
    PROJECT_NAME="$PROJECT_NAME" node ../../scripts/manage-versions-and-deploy.js
fi

# Show final status
log_success "Deployment completed for project: $PROJECT_NAME"

if [ ${#DOGET_DOPOST_FILES[@]} -gt 0 ]; then
    echo
    log_info "🌐 Web app functions were updated. The following URLs should now reflect changes:"
    
    # Try to extract script ID and show web app URL
    if [ -f .clasp.json ]; then
        SCRIPT_ID=$(grep -o '"scriptId":"[^"]*"' .clasp.json | cut -d'"' -f4)
        if [ -n "$SCRIPT_ID" ]; then
            echo "📋 Script ID: $SCRIPT_ID"
            echo "🌐 Web App URL: https://script.google.com/macros/s/[DEPLOYMENT_ID]/exec"
            echo "   (Replace [DEPLOYMENT_ID] with the actual deployment ID from above)"
        fi
    fi
fi
