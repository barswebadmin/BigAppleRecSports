#!/bin/bash

# Deployment helper for Google Apps Script projects
# Creates temp directory, flattens src/ structure, pushes to GAS, then cleans up

set -e

PROJECT_NAME=$(basename "$(pwd)")
DEPLOY_TEMP="deploy_temp"

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

    # Copy appsscript.json if it exists
    if [ -f "appsscript.json" ]; then
        cp "appsscript.json" "$DEPLOY_TEMP/"
        log_info "Copied appsscript.json"
    fi

    # Copy .clasp.json if it exists, but normalize rootDir for flattened deploy
    if [ -f ".clasp.json" ]; then
        # If rootDir is present, rewrite it to "." for deploy_temp
        if grep -q '"rootDir"' .clasp.json; then
            sed '/"rootDir"/s#"rootDir"[[:space:]]*:[[:space:]]*"[^"]*"#"rootDir": "."#' .clasp.json > "$DEPLOY_TEMP/.clasp.json"
            log_info "Copied .clasp.json (rootDir normalized to .)"
        else
            cp ".clasp.json" "$DEPLOY_TEMP/"
            log_info "Copied .clasp.json"
        fi
    fi

    # Find and copy all source files from src/ with flattened names (.gs, .html, .js)
    log_info "Copying and flattening src/ structure..."

    file_count=0
    while IFS= read -r -d '' file; do
        # Get relative path from src/
        rel_path="${file#src/}"

        # Extract directory and filename
        dir_part=$(dirname "$rel_path")
        file_part=$(basename "$rel_path")

        # Create flattened name (directory/filename.gs)
        if [ "$dir_part" = "." ]; then
            # File is directly in src/
            new_name="$file_part"
        else
            # File is in subdirectory - keep directory structure with slashes
            new_name="${dir_part}/${file_part}"
        fi

        # Create directory if needed for subdirectory files
        if [[ "$new_name" == *"/"* ]]; then
            mkdir -p "$(dirname "$DEPLOY_TEMP/$new_name")"
        fi

        # Copy to deploy_temp with new name
        cp "$file" "$DEPLOY_TEMP/$new_name"
        log_info "  $file → $new_name"
        file_count=$((file_count + 1))

    done < <(find src \( -name "*.gs" -o -name "*.html" -o -name "*.js" \) -type f -print0)

    if [ $file_count -eq 0 ]; then
        log_warning "No source files found in src/ directory (.gs/.html/.js)"
    else
        log_success "Copied $file_count files with flattened structure"
    fi

    # Change to deploy_temp directory for clasp operations
    cd "$DEPLOY_TEMP"

    # Push to Google Apps Script
    log_info "Pushing code to Google Apps Script..."

    if command -v clasp >/dev/null 2>&1; then
        # Use printf to auto-answer any prompts with 'y' and capture output
        if printf "y\n" | clasp push --force; then
            log_success "Code pushed to Google Apps Script successfully"
        else
            log_error "Failed to push code to Google Apps Script"
            exit 1
        fi
    else
        log_error "clasp command not found. Please install clasp CLI."
        exit 1
    fi

    # Return to original directory
    cd ..

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
