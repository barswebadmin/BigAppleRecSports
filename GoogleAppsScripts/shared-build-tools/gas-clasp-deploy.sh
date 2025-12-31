#!/bin/bash

# Generic Google Apps Script deployment helper
# Builds project with esbuild, then deploys to GAS using clasp
# Configurable via environment variables or clasp-deploy.config.sh

set -e

# Default configuration (can be overridden)
PROJECT_NAME=${PROJECT_NAME:-$(basename "$(pwd)")}
DEPLOY_TEMP=${DEPLOY_TEMP:-"deploy_temp"}
BUILD_DIR=${BUILD_DIR:-"build"}
OUTPUT_FILE=${OUTPUT_FILE:-"Code.js"}
PACKAGE_MANAGER=${PACKAGE_MANAGER:-"pnpm"}
ORIGINAL_DIR="$(pwd)"

# Load project-specific config if it exists
if [ -f "clasp-deploy.config.sh" ]; then
    source clasp-deploy.config.sh
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Cleanup function - always runs
cleanup() {
    # Always return to original directory first
    cd "$ORIGINAL_DIR" 2>/dev/null || true
    
    if [ -d "$DEPLOY_TEMP" ]; then
        log_info "Cleaning up temporary deployment directory..."
        rm -rf "$DEPLOY_TEMP"
        log_success "Cleanup completed"
    fi
}

# Set trap to ensure cleanup happens even if script fails
trap cleanup EXIT

# Main deployment function
deploy() {
    log_info "Starting deployment for $PROJECT_NAME..."

    # Clean previous build artifacts
    log_info "Cleaning previous build artifacts..."
    if ! $PACKAGE_MANAGER clean; then
        log_error "Clean failed - cannot proceed with deployment"
        exit 1
    fi
    log_success "Clean completed"

    # Run esbuild to bundle and transpile ES6 modules
    log_info "Building ES6 modules with esbuild..."
    if ! $PACKAGE_MANAGER build; then
        log_error "Build failed - cannot proceed with deployment"
        exit 1
    fi
    log_success "Build completed"

    # Check if build/ directory exists (output from esbuild)
    if [ ! -d "$BUILD_DIR" ]; then
        log_error "No $BUILD_DIR/ directory found after build step"
        exit 1
    fi

    # Create clean deploy temp directory
    if [ -d "$DEPLOY_TEMP" ]; then
        log_info "Removing existing deploy_temp directory..."
        rm -rf "$DEPLOY_TEMP"
    fi

    log_info "Creating temporary deployment directory..."
    mkdir "$DEPLOY_TEMP"

    # Copy appsscript.json from build/ (created by esbuild)
    if [ -f "$BUILD_DIR/appsscript.json" ]; then
        cp "$BUILD_DIR/appsscript.json" "$DEPLOY_TEMP/"
        log_info "Copied appsscript.json from $BUILD_DIR/"
    elif [ -f "appsscript.json" ]; then
        cp "appsscript.json" "$DEPLOY_TEMP/"
        log_info "Copied appsscript.json from root"
    fi

    # Copy and modify .clasp.json if it exists
    if [ -f ".clasp.json" ]; then
        # Copy .clasp.json and update rootDir to "." since we're flattening to deploy_temp root
        if command -v jq >/dev/null 2>&1; then
            jq '.rootDir = "."' ".clasp.json" > "$DEPLOY_TEMP/.clasp.json"
            log_info "Copied and updated .clasp.json (rootDir set to '.')"
        else
            # Fallback if jq not available - use sed
            sed 's/"rootDir"[[:space:]]*:[[:space:]]*"[^"]*"/"rootDir": "."/' ".clasp.json" > "$DEPLOY_TEMP/.clasp.json"
            log_info "Copied and updated .clasp.json (rootDir set to '.' via sed)"
        fi
    fi

    # Copy the unified bundle from build/ directory
    log_info "Copying unified bundle from $BUILD_DIR/ directory..."

    if [ -f "$BUILD_DIR/$OUTPUT_FILE" ]; then
        cp "$BUILD_DIR/$OUTPUT_FILE" "$DEPLOY_TEMP/$OUTPUT_FILE"
        log_info "  $BUILD_DIR/$OUTPUT_FILE → $OUTPUT_FILE"
        log_success "Copied unified bundle"
    else
        log_error "No $OUTPUT_FILE found in $BUILD_DIR/ directory"
        exit 1
    fi

    # Change to deploy_temp directory for clasp operations
    cd "$DEPLOY_TEMP"
    
    # Note: No deployment marker needed - esbuild adds unique timestamps in file banners

    # Push to Google Apps Script and capture output
    log_info "Pushing code to Google Apps Script..."

    if ! command -v clasp >/dev/null 2>&1; then
        log_error "clasp command not found. Please install clasp CLI."
        exit 1
    fi

    # Capture clasp push output (disable set -e temporarily to ensure we capture output)
    log_info "Running: clasp push --force"
    set +e  # Temporarily disable exit on error
    push_output=$(printf "y\n" | clasp push --force 2>&1)
    push_exit_code=$?
    set -e  # Re-enable exit on error
    
    log_info "Push exit code: $push_exit_code"

    # Check for errors in output (clasp returns exit 0 even on syntax errors!)
    if echo "$push_output" | grep -qiE "(syntax error|error:|failed)"; then
        log_error "❌ Push failed with errors detected in output"
        log_error "$push_output"
        exit 1
    fi

    # Check if clasp reported "already up to date"
    if echo "$push_output" | grep -q "already up to date"; then
        log_warning "clasp reports 'Script is already up to date' - clearing cache and retrying..."
        
        # Clear clasp cache files
        if [ -f ".clasprc.json" ]; then
            rm -f ".clasprc.json"
            log_info "Cleared local .clasprc.json cache"
        fi
        
        if [ -f "$HOME/.clasprc.json" ]; then
            rm -f "$HOME/.clasprc.json"
            log_info "Cleared global .clasprc.json cache"
        fi
        
        # Add a unique marker to the output file to force clasp to detect changes
        RETRY_ID="$(date -u +"%Y%m%d%H%M%S")_RETRY_${RANDOM}"
        echo "// Retry_Deploy_ID: ${RETRY_ID}" >> "$OUTPUT_FILE"
        log_info "Added retry deployment marker: ${RETRY_ID}"
        
        # Retry the push
        log_info "Retrying push..."
        log_info "Running: clasp push --force (retry)"
        push_output=$(printf "y\n" | clasp push --force 2>&1)
        push_exit_code=$?
        log_info "Retry exit code: $push_exit_code"
        log_info "Retry output: $push_output"
        
        # Check again if still "already up to date"
        if echo "$push_output" | grep -q "already up to date"; then
            log_error "Push still reports 'already up to date' after cache clear and retry!"
            log_error "This indicates a deeper clasp issue."
            log_error "Manual intervention required:"
            log_info "  cd $(pwd)"
            log_info "  clasp status"
            log_info "  clasp push --force"
            exit 1
        fi
    fi

    if [ $push_exit_code -ne 0 ]; then
        log_error "Failed to push code to Google Apps Script (exit code: $push_exit_code)"
        exit 1
    fi

    log_success "Code pushed to Google Apps Script successfully!"

    # Return to original directory
    cd "$ORIGINAL_DIR"

    log_success "Deployment completed successfully!"
    log_warning "Code pushed to Google Apps Script but NOT deployed to web app"
    log_info "To deploy manually: cd $PROJECT_NAME && clasp deploy --description 'Manual deployment'"
}

# Handle command line arguments
case "${1:-push}" in
    push)
        deploy
        ;;
    clean)
        cleanup
        log_info "Cleanup completed"
        ;;
    *)
        echo "Usage: $0 [push|clean]"
        echo "  push  - Deploy code to Google Apps Script (default)"
        echo "  clean - Clean up temporary files only"
        exit 1
        ;;
esac

