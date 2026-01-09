#!/bin/bash

# Deployment helper for Google Apps Script projects
# push: Creates temp directory, flattens src/ structure, pushes to GAS, then cleans up
# pull: Pulls from GAS, reorganizes flattened files back into src/ structure, then cleans up

set -e

PROJECT_NAME=$(basename "$(pwd)")
DEPLOY_TEMP="deploy_temp"
ORIGINAL_PWD="$(pwd)"
DEPLOY_TEMP_PATH="$ORIGINAL_PWD/$DEPLOY_TEMP"

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
    if [ "$(pwd)" != "$ORIGINAL_PWD" ]; then
        cd "$ORIGINAL_PWD" || true
    fi
    if [ -d "$DEPLOY_TEMP_PATH" ]; then
        log_info "Cleaning up temporary deployment directory..."
        rm -rf "$DEPLOY_TEMP_PATH"
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
    if [ -d "$DEPLOY_TEMP_PATH" ]; then
        log_info "Removing existing deploy_temp directory..."
        rm -rf "$DEPLOY_TEMP_PATH"
    fi

    log_info "Creating temporary deployment directory..."
    mkdir -p "$DEPLOY_TEMP_PATH"

    # Copy appsscript.json if it exists in project root
    if [ -f "appsscript.json" ]; then
        cp "appsscript.json" "$DEPLOY_TEMP_PATH/"
        log_info "Copied appsscript.json"
    fi

    # Copy .clasp.json if it exists, but normalize rootDir for flattened deploy
    if [ -f ".clasp.json" ]; then
        # If rootDir is present, rewrite it to "." for deploy_temp
        if grep -q '"rootDir"' .clasp.json; then
            sed '/"rootDir"/s#"rootDir"[[:space:]]*:[[:space:]]*"[^"]*"#"rootDir": "."#' .clasp.json > "$DEPLOY_TEMP_PATH/.clasp.json"
            log_info "Copied .clasp.json (rootDir normalized to .)"
        else
            cp ".clasp.json" "$DEPLOY_TEMP_PATH/"
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
            mkdir -p "$(dirname "$DEPLOY_TEMP_PATH/$new_name")"
        fi

        # Copy to deploy_temp with new name
        cp "$file" "$DEPLOY_TEMP_PATH/$new_name"
        log_info "  $file → $new_name"
        file_count=$((file_count + 1))

    done < <(find src \( -name "*.gs" -o -name "*.html" -o -name "*.js" \) -type f -print0)

    if [ $file_count -eq 0 ]; then
        log_warning "No source files found in src/ directory (.gs/.html/.js)"
    else
        log_success "Copied $file_count files with flattened structure"
    fi

    # Change to deploy_temp directory for clasp operations
    cd "$DEPLOY_TEMP_PATH"

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
    cd "$ORIGINAL_PWD"

    log_success "Deployment completed successfully!"
    log_warning "Code pushed to Google Apps Script but NOT deployed to web app"
    log_info "To deploy manually: cd $PROJECT_NAME && clasp deploy --description 'Manual deployment'"
}

# Pull function - reverse of deploy
pull() {
    log_info "Starting pull from Google Apps Script for $PROJECT_NAME..."

    # Create clean deploy temp directory
    if [ -d "$DEPLOY_TEMP_PATH" ]; then
        log_info "Removing existing deploy_temp directory..."
        rm -rf "$DEPLOY_TEMP_PATH"
    fi

    log_info "Creating temporary pull directory..."
    mkdir -p "$DEPLOY_TEMP_PATH"

    # Copy .clasp.json if it exists, but normalize rootDir for flattened pull
    if [ -f ".clasp.json" ]; then
        # If rootDir is present, rewrite it to "." for deploy_temp
        if grep -q '"rootDir"' .clasp.json; then
            sed '/"rootDir"/s#"rootDir"[[:space:]]*:[[:space:]]*"[^"]*"#"rootDir": "."#' .clasp.json > "$DEPLOY_TEMP_PATH/.clasp.json"
            log_info "Copied .clasp.json (rootDir normalized to .)"
        else
            cp ".clasp.json" "$DEPLOY_TEMP_PATH/"
            log_info "Copied .clasp.json"
        fi
    else
        log_error ".clasp.json not found. Cannot pull without clasp configuration."
        exit 1
    fi

    # Change to deploy_temp directory for clasp operations
    cd "$DEPLOY_TEMP_PATH"

    # Pull from Google Apps Script
    log_info "Pulling code from Google Apps Script..."

    if command -v clasp >/dev/null 2>&1; then
        if clasp pull; then
            log_success "Code pulled from Google Apps Script successfully"
        else
            log_error "Failed to pull code from Google Apps Script"
            exit 1
        fi
    else
        log_error "clasp command not found. Please install clasp CLI."
        exit 1
    fi

    # Return to original directory
    cd "$ORIGINAL_PWD"

    # Ensure src/ directory exists
    if [ ! -d "src" ]; then
        log_info "Creating src/ directory..."
        mkdir -p "src"
    fi

    # Reorganize pulled files back into src/ structure
    log_info "Reorganizing files back into src/ structure..."

    file_count=0
    while IFS= read -r -d '' file; do
        # Skip .clasp.json and appsscript.json (handle separately)
        if [[ "$file" == *"/.clasp.json" ]] || [[ "$file" == *"/appsscript.json" ]]; then
            continue
        fi

        # Get relative path from deploy_temp
        rel_path="${file#$DEPLOY_TEMP_PATH/}"

        # Determine destination in src/
        if [[ "$rel_path" == *"/"* ]]; then
            # File is in a subdirectory (e.g., shared-utilities/ShopifyUtils.js)
            dest_path="src/$rel_path"
        else
            # File is in root (e.g., Utils.js)
            dest_path="src/$rel_path"
        fi

        # Create destination directory if needed
        dest_dir=$(dirname "$dest_path")
        if [ ! -d "$dest_dir" ]; then
            mkdir -p "$dest_dir"
        fi

        # Copy file to src/ structure
        cp "$file" "$dest_path"
        log_info "  $rel_path → $dest_path"
        file_count=$((file_count + 1))

    done < <(find "$DEPLOY_TEMP_PATH" \( -name "*.gs" -o -name "*.html" -o -name "*.js" \) -type f -print0)

    # Copy appsscript.json back to project root if it was pulled
    if [ -f "$DEPLOY_TEMP_PATH/appsscript.json" ]; then
        cp "$DEPLOY_TEMP_PATH/appsscript.json" "$ORIGINAL_PWD/appsscript.json"
        log_info "Copied appsscript.json to project root"
    fi

    if [ $file_count -eq 0 ]; then
        log_warning "No source files found in pulled code (.gs/.html/.js)"
    else
        log_success "Reorganized $file_count files into src/ structure"
    fi

    log_success "Pull completed successfully!"
}

# Handle command line arguments
case "${1:-push}" in
    push)
        deploy
        ;;
    pull)
        pull
        ;;
    clean)
        cleanup
        log_info "Cleanup completed"
        ;;
    *)
        echo "Usage: $0 [push|pull|clean]"
        echo "  push  - Deploy code to Google Apps Script (default)"
        echo "  pull  - Pull code from Google Apps Script and reorganize into src/"
        echo "  clean - Clean up temporary files only"
        exit 1
        ;;
esac



