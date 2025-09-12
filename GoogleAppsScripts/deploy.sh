#!/bin/bash

# Custom deployment script for organized Google Apps Script project
# Flattens directory structure for GAS while maintaining local organization

# Work from current directory (where symlink is called from)
SCRIPT_DIR="$(pwd)"
TEMP_DIR="$SCRIPT_DIR/.deploy_temp"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  push     Flatten directory structure and push to Google Apps Script"
    echo "  pull     Pull from Google Apps Script and organize into directories"
    echo "  status   Show clasp status"
    echo "  deploy   Deploy a new version (after push)"
    echo "  help     Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 push    # Push organized code to GAS"
    echo "  $0 pull    # Pull from GAS and organize locally"
    echo "  $0 deploy  # Create new deployment version"
}

function prepare_for_gas() {
    log_info "Preparing directory structure for Google Apps Script..."

    # Clean and create temp directory
    rm -rf "$TEMP_DIR"
    mkdir -p "$TEMP_DIR"

    # Copy appsscript.json (no modification needed)
    if [ -f "$SCRIPT_DIR/appsscript.json" ]; then
        cp "$SCRIPT_DIR/appsscript.json" "$TEMP_DIR/"
        log_info "Copied appsscript.json"
    fi

    # Copy .clasp.json if it exists
    if [ -f "$SCRIPT_DIR/.clasp.json" ]; then
        cp "$SCRIPT_DIR/.clasp.json" "$TEMP_DIR/"
        log_info "Copied .clasp.json"
    fi

    # Check if we have a src/ directory structure
    if [ -d "$SCRIPT_DIR/src" ]; then
        log_info "Copying and flattening src/ structure..."

        # Find all .gs/.js files in src/ and flatten them
        files_found=()
        while IFS= read -r file; do
            files_found+=("$file")
        done < <(find "$SCRIPT_DIR/src" -name "*.gs" -o -name "*.js" -type f)

        file_count=${#files_found[@]}

        for file in "${files_found[@]}"; do
            # Get relative path from src/
            rel_path="${file#$SCRIPT_DIR/src/}"

            # Extract directory and filename
            dir_part=$(dirname "$rel_path")
            file_part=$(basename "$rel_path")

            # Create flattened name (directory/filename.ext)
            if [ "$dir_part" = "." ]; then
                # File is directly in src/
                new_name="$file_part"
            else
                # File is in subdirectory - keep directory structure with slashes
                new_name="${dir_part}/${file_part}"
            fi

            # Create directory if needed for subdirectory files
            if [[ "$new_name" == *"/"* ]]; then
                mkdir -p "$(dirname "$TEMP_DIR/$new_name")"
            fi

            # Copy to deploy_temp with new name
            cp "$file" "$TEMP_DIR/$new_name"
            log_info "  $file → $new_name"
        done

        if [ $file_count -eq 0 ]; then
            log_warning "No .gs/.js files found in src/ directory"
        else
            log_success "Copied $file_count files with flattened structure"
        fi
    else
        # Fallback: Find all .gs files in subdirectories and copy them
        find "$SCRIPT_DIR" -name "*.gs" -type f | while read -r file; do
            # Skip files in deploy_temp
            if [[ "$file" == *"$TEMP_DIR"* ]]; then
                continue
            fi

            # Get relative path from script directory
            rel_path=$(echo "$file" | sed "s|^$SCRIPT_DIR/||")

            # Copy file maintaining directory structure (GAS supports slashes in filenames)
            cp "$file" "$TEMP_DIR/$rel_path"
            log_info "Copied: $rel_path → $rel_path"
        done
    fi

    log_success "Directory structure prepared in $TEMP_DIR"
}

function organize_from_gas() {
    log_info "Organizing files from Google Apps Script into directories..."

    # Create directories if they don't exist
    mkdir -p "$SCRIPT_DIR/shared-utilities"
    mkdir -p "$SCRIPT_DIR/processors"

    # Move files from temp directory back to organized structure
    for file in "$TEMP_DIR"/*.gs; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")

            # Determine target directory based on filename prefix
            if [[ "$filename" == shared-utilities_* ]]; then
                target_name=$(echo "$filename" | sed 's/shared-utilities_//')
                target_path="$SCRIPT_DIR/shared-utilities/$target_name"
            elif [[ "$filename" == processors_* ]]; then
                target_name=$(echo "$filename" | sed 's/processors_//')
                target_path="$SCRIPT_DIR/processors/$target_name"
            else
                # Files without directory prefix stay in root
                target_path="$SCRIPT_DIR/$filename"
            fi

            cp "$file" "$target_path"
            log_info "Organized: $filename → $target_path"
        fi
    done

    log_success "Files organized into directory structure"
}

function push_to_gas() {
    log_info "Pushing to Google Apps Script..."

    # Prepare structure
    prepare_for_gas

    # Change to temp directory for clasp operations
    cd "$TEMP_DIR" || exit 1

    # Verify .clasp.json exists (should have been copied by prepare_for_gas)
    if [ ! -f ".clasp.json" ]; then
        log_error ".clasp.json not found. Make sure this is a clasp project."
        cd "$SCRIPT_DIR" || exit 1
        return 1
    fi

    # Push to Google Apps Script
    if printf "y\n" | clasp push --force; then
        log_success "Successfully pushed to Google Apps Script!"
        log_info "Files in GAS with organized structure:"
        find . -name "*.gs" -o -name "*.js" -type f | sed 's|^\./||' | sort | sed 's/^/  • /'
    else
        log_error "Failed to push to Google Apps Script"
        cd "$SCRIPT_DIR" || exit 1
        return 1
    fi

    # Return to original directory
    cd "$SCRIPT_DIR" || exit 1

    # Clean up temp directory
    rm -rf "$TEMP_DIR"
}

function pull_from_gas() {
    log_info "Pulling from Google Apps Script..."

    # Create temp directory
    mkdir -p "$TEMP_DIR"
    cd "$TEMP_DIR" || exit 1

    # Copy .clasp.json
    if [ -f "$SCRIPT_DIR/.clasp.json" ]; then
        cp "$SCRIPT_DIR/.clasp.json" "$TEMP_DIR/"
    else
        log_error ".clasp.json not found. Make sure this is a clasp project."
        return 1
    fi

    # Pull from Google Apps Script
    if clasp pull; then
        log_success "Successfully pulled from Google Apps Script!"

        # Return to original directory and organize
        cd "$SCRIPT_DIR" || exit 1
        organize_from_gas

        # Clean up temp directory
        rm -rf "$TEMP_DIR"
    else
        log_error "Failed to pull from Google Apps Script"
        cd "$SCRIPT_DIR" || exit 1
        return 1
    fi
}

function show_status() {
    log_info "Checking clasp status..."

    if [ -f "$SCRIPT_DIR/.clasp.json" ]; then
        cd "$SCRIPT_DIR" || exit 1
        clasp status
    else
        log_error ".clasp.json not found. Make sure this is a clasp project."
        return 1
    fi
}

function deploy_version() {
    log_info "Creating new deployment..."

    # First push the latest changes
    if push_to_gas; then
        log_info "Now deploying new version..."

        # Create temp directory and copy .clasp.json for deployment
        mkdir -p "$TEMP_DIR"
        cd "$TEMP_DIR" || exit 1

        if [ -f "$SCRIPT_DIR/.clasp.json" ]; then
            cp "$SCRIPT_DIR/.clasp.json" "$TEMP_DIR/"

            if clasp deploy; then
                log_success "Successfully deployed new version!"
            else
                log_error "Failed to deploy new version"
                return 1
            fi
        fi

        cd "$SCRIPT_DIR" || exit 1
        rm -rf "$TEMP_DIR"
    else
        log_error "Push failed, skipping deployment"
        return 1
    fi
}

# Main command handling
case "${1:-help}" in
    push)
        push_to_gas
        ;;
    pull)
        pull_from_gas
        ;;
    status)
        show_status
        ;;
    deploy)
        deploy_version
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
