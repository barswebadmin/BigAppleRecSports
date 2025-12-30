#!/bin/bash

# Deployment helper for add-sold-out-product-to-waitlist
# Creates temp directory, flattens src/ structure, pushes to GAS, then cleans up

set -e

PROJECT_NAME=$(basename "$(pwd)")
DEPLOY_TEMP="deploy_temp"
ORIGINAL_DIR="$(pwd)"

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

    # Check if src/ directory exists
    if [ ! -d "src" ]; then
        log_error "No src/ directory found. Expected structure: src/core/, src/handlers/, etc."
        exit 1
    fi

    # Create clean deploy temp directory
    if [ -d "$DEPLOY_TEMP" ]; then
        log_info "Removing existing deploy_temp directory..."
        rm -rf "$DEPLOY_TEMP"
    fi

    log_info "Creating temporary deployment directory..."
    mkdir "$DEPLOY_TEMP"

    # Copy appsscript.json from src/ if it exists
    if [ -f "src/appsscript.json" ]; then
        cp "src/appsscript.json" "$DEPLOY_TEMP/"
        log_info "Copied appsscript.json from src/"
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

    # Find and copy all .js/.gs files from src/ subdirectories with flattened names
    log_info "Copying and flattening src/ structure..."

    file_count=0
    while IFS= read -r -d '' file; do
        # Get relative path from src/
        rel_path="${file#src/}"

        # Extract directory and filename
        dir_part=$(dirname "$rel_path")
        file_part=$(basename "$rel_path")

        # Create flattened name (directory/filename.js/.gs)
        if [ "$dir_part" = "." ]; then
            # File is directly in src/
            new_name="$file_part"
        else
            # File is in subdirectory - keep directory structure with slashes
            new_name="${dir_part}/${file_part}"
        fi

        # Create directory if needed and copy to deploy_temp with new name
        if [[ "$new_name" == *"/"* ]]; then
            mkdir -p "$(dirname "$DEPLOY_TEMP/$new_name")"
        fi
        cp "$file" "$DEPLOY_TEMP/$new_name"
        log_info "  $file → $new_name"
        ((file_count++))

    done < <(find src \( -name "*.js" -o -name "*.gs" \) -type f -print0)

    if [ $file_count -eq 0 ]; then
        log_warning "No .js/.gs files found in src/ directory"
    else
        log_success "Copied $file_count files with flattened structure"
    fi

    # Change to deploy_temp directory for clasp operations
    cd "$DEPLOY_TEMP"
    
    # Add a unique version marker with timestamp + random number to force clasp to detect changes
    if [ -f "config/constants.js" ]; then
        UNIQUE_ID="$(date -u +"%Y%m%d%H%M%S")_${RANDOM}"
        echo "" >> "config/constants.js"
        echo "// Deploy_ID: ${UNIQUE_ID}" >> "config/constants.js"
        log_info "Added unique deployment marker: ${UNIQUE_ID}"
    fi

    # Push to Google Apps Script and capture output
    log_info "Pushing code to Google Apps Script..."

    if ! command -v clasp >/dev/null 2>&1; then
        log_error "clasp command not found. Please install clasp CLI."
        exit 1
    fi

    # Capture clasp push output
    log_info "Running: clasp push --force"
    push_output=$(printf "y\n" | clasp push --force 2>&1)
    push_exit_code=$?
    log_info "Push exit code: $push_exit_code"
    log_info "Push output: $push_output"

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
        
        # Add another unique marker to ensure it's different
        if [ -f "config/constants.js" ]; then
            RETRY_ID="$(date -u +"%Y%m%d%H%M%S")_RETRY_${RANDOM}"
            echo "// Retry_Deploy_ID: ${RETRY_ID}" >> "config/constants.js"
            log_info "Added retry deployment marker: ${RETRY_ID}"
        fi
        
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
