#!/bin/bash
#
# Shared helper functions for GAS clasp operations
# Source this file in other scripts: source "$(dirname "$0")/shared-helpers.sh"
#

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

# Normalize .clasp.json rootDir to "." for temp directories
normalize_clasp_json() {
    local source_file="$1"
    local dest_file="$2"
    
    if [ ! -f "$source_file" ]; then
        log_error ".clasp.json not found: $source_file"
        return 1
    fi
    
    if command -v jq >/dev/null 2>&1; then
        jq '.rootDir = "."' "$source_file" > "$dest_file"
    else
        sed 's/"rootDir"[[:space:]]*:[[:space:]]*"[^"]*"/"rootDir": "."/' "$source_file" > "$dest_file"
    fi
}

# Execute clasp command with error capture
execute_clasp() {
    local command="$1"
    local output_var="${2:-CLASP_OUTPUT}"
    local exit_code_var="${3:-CLASP_EXIT_CODE}"
    
    set +e  # Temporarily disable exit on error to capture output
    local output
    output=$(clasp $command 2>&1)
    local exit_code=$?
    set -e  # Re-enable exit on error
    
    eval "$output_var='$output'"
    eval "$exit_code_var=$exit_code"
    
    return $exit_code
}

# Cleanup temp directory
cleanup_temp_dir() {
    local temp_dir="$1"
    
    if [ -n "$temp_dir" ] && [ -d "$temp_dir" ]; then
        log_info "Cleaning up temporary directory: $temp_dir"
        rm -rf "$temp_dir"
        log_success "Cleanup complete"
    fi
}

# Clean GAS project build artifacts and temp files
# Usage: clean_gas_project "$project_dir"
# Returns: 0 on success, 1 on failure
clean_gas_project() {
    local project_dir="$1"
    local script_dir="${2:-}"
    
    if [ -z "$script_dir" ]; then
        script_dir=$(get_script_dir)
    fi
    
    local clean_script="$script_dir/clean.sh"
    
    if [ ! -f "$clean_script" ]; then
        log_error "Clean script not found: $clean_script"
        return 1
    fi
    
    bash "$clean_script" "$project_dir"
    return $?
}

# Setup cleanup trap
setup_cleanup_trap() {
    local temp_dir="$1"
    trap "cleanup_temp_dir '$temp_dir'" EXIT INT TERM
}

# Get script directory (works when sourced or executed)
get_script_dir() {
    if [ -n "${BASH_SOURCE[0]}" ]; then
        # Script is being sourced or executed directly
        dirname "$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")"
    else
        # Fallback for some shells
        dirname "$(readlink -f "$0" 2>/dev/null || echo "$0")"
    fi
}

# Get GAS root directory (GoogleAppsScripts/)
get_gas_root() {
    local script_dir="$1"
    if [ -z "$script_dir" ]; then
        script_dir=$(get_script_dir)
    fi
    
    # Navigate up from remote-sync-tools to GoogleAppsScripts
    local current="$script_dir"
    while [ "$current" != "/" ]; do
        if [ -d "$current/projects" ] && [ -d "$current/remote-sync-tools" ]; then
            echo "$current"
            return 0
        fi
        current=$(dirname "$current")
    done
    
    log_error "Could not find GoogleAppsScripts root directory"
    return 1
}

# Validate project exists and has .clasp.json
validate_project() {
    local project_name="$1"
    local gas_root="${2:-}"
    
    if [ -z "$gas_root" ]; then
        gas_root=$(get_gas_root)
    fi
    
    local project_path="$gas_root/projects/$project_name"
    
    if [ ! -d "$project_path" ]; then
        log_error "Project directory not found: $project_path"
        return 1
    fi
    
    if [ ! -f "$project_path/.clasp.json" ]; then
        log_error "No .clasp.json found in $project_path"
        return 1
    fi
    
    return 0
}

# Check if clasp is authenticated
check_clasp_auth() {
    if ! clasp status >/dev/null 2>&1; then
        log_error "Not logged in to clasp. Run 'clasp login' first."
        return 1
    fi
    return 0
}

# Check if required scripts exist
check_script_dependencies() {
    local gas_root="${1:-}"
    local missing_scripts=()
    
    if [ -z "$gas_root" ]; then
        gas_root=$(get_gas_root)
    fi
    
    local required_scripts=(
        "$gas_root/remote-sync-tools/push.sh"
        "$gas_root/remote-sync-tools/pull.sh"
        "$gas_root/remote-sync-tools/build.js"
    )
    
    for script in "${required_scripts[@]}"; do
        if [ ! -f "$script" ]; then
            missing_scripts+=("$script")
        fi
    done
    
    if [ ${#missing_scripts[@]} -gt 0 ]; then
        log_error "Missing required scripts:"
        for script in "${missing_scripts[@]}"; do
            echo "  - $script"
        done
        return 1
    fi
    
    return 0
}

# Parse clasp command arguments
# Usage: parse_clasp_args "$@"
# Sets: PROJECT_NAME, IS_DRY_RUN, IS_COMPARE_ONLY
parse_clasp_args() {
    PROJECT_NAME="${1:-}"
    MODE="${2:-}"
    
    if [ -z "$PROJECT_NAME" ]; then
        log_error "Project name required"
        echo "Usage: $0 <project-name> [--dry-run|--compare-only]"
        exit 1
    fi
    
    IS_DRY_RUN=false
    IS_COMPARE_ONLY=false
    
    if [ "$MODE" = "--dry-run" ]; then
        IS_DRY_RUN=true
        log_info "🔍 DRY RUN MODE - No changes will be made"
    elif [ "$MODE" = "--compare-only" ]; then
        IS_COMPARE_ONLY=true
        log_info "🔍 COMPARE ONLY MODE - Showing diff and exiting"
    fi
}

# Get project paths
# Usage: get_project_paths "$PROJECT_NAME"
# Sets: REPO_ROOT, GAS_ROOT, PROJECT_DIR
get_project_paths() {
    local project_name="$1"
    local script_dir="${2:-}"
    
    if [ -z "$script_dir" ]; then
        script_dir=$(get_script_dir)
    fi
    
    REPO_ROOT="$(cd "$script_dir/../.." && pwd)"
    GAS_ROOT="$REPO_ROOT/GoogleAppsScripts"
    PROJECT_DIR="$GAS_ROOT/projects/$project_name"
}

# Build GAS project using esbuild
# Usage: build_gas_project "$PROJECT_DIR" "$GAS_ROOT"
# Returns: 0 on success, 1 on failure
# Note: All validation and build logic is handled by build.js
build_gas_project() {
    local project_dir="$1"
    local gas_root="$2"
    
    log_info "📦 Building project..."
    
    if ! node "$gas_root/remote-sync-tools/build.js" "$project_dir"; then
        log_error "Build failed"
        return 1
    fi
    
    log_success "Build completed"
    return 0
}

# Parse comparison output to detect changes
# Usage: parse_comparison_output "$COMPARE_OUTPUT"
# Returns: 0 if no changes, 1 if changes detected
parse_comparison_output() {
    local compare_output="$1"
    
    if echo "$compare_output" | grep -q "Different files:"; then
        return 1
    elif echo "$compare_output" | grep -q "Files only in local:"; then
        return 1
    elif echo "$compare_output" | grep -q "Files only in remote:"; then
        return 1
    fi
    
    return 0
}

# Prompt user for confirmation
# Usage: prompt_user_confirmation "$has_changes" "$is_dry_run" "$action"
# Returns: 0 for yes, 1 for no
prompt_user_confirmation() {
    local has_changes="$1"
    local is_dry_run="$2"
    local action="${3:-push}"
    
    if [ "$has_changes" = false ]; then
        log_warning "No changes detected between local and remote"
        if [ "$is_dry_run" = true ]; then
            log_info "🔍 DRY RUN: Would prompt '${action^} anyway? (y/N)'"
            return 0
        else
            read -p "${action^} anyway? (y/N): " -n 1 -r
            echo ""
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "${action^} cancelled"
                return 1
            fi
        fi
    else
        log_warning "Changes detected between local and remote"
        if [ "$is_dry_run" = true ]; then
            log_info "🔍 DRY RUN: Would prompt '${action^} changes? (Y/n)' (default: yes)"
            return 0
        else
            read -p "${action^} changes? (Y/n): " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Nn]$ ]]; then
                log_info "${action^} cancelled"
                return 1
            fi
        fi
    fi
    
    return 0
}

# Setup temp workspace with cleanup trap
# Usage: setup_temp_workspace "$project_dir" "$workspace_type" TEMP_DIR_VAR
# Sets: TEMP_DIR variable and cleanup trap
setup_temp_workspace() {
    local project_dir="$1"
    local workspace_type="$2"
    local temp_dir_var="$3"
    
    local temp_dir="$project_dir/.clasp_${workspace_type}_temp"
    
    # Clean up any existing temp directory
    if [ -d "$temp_dir" ]; then
        log_info "Removing existing temp directory..."
        rm -rf "$temp_dir"
    fi
    
    mkdir -p "$temp_dir"
    
    # Set the variable name passed in
    eval "$temp_dir_var='$temp_dir'"
    
    # Setup cleanup trap
    cleanup_on_exit() {
        log_warning "Interrupted - cleaning up..."
        cleanup_temp_dir "$temp_dir"
        exit 130
    }
    trap cleanup_on_exit INT TERM
}

# Setup multiple temp directories with cleanup trap
# Usage: setup_multi_temp_workspace TEMP_DIRS_ARRAY
# Sets: Cleanup trap for all temp dirs in array
setup_multi_temp_workspace() {
    local temp_dirs_var="$1"
    
    cleanup_on_exit() {
        log_warning "Interrupted - cleaning up..."
        eval "local temp_dirs=(\"\${${temp_dirs_var}[@]}\")"
        for temp_dir in "${temp_dirs[@]}"; do
            if [ -n "$temp_dir" ] && [ -d "$temp_dir" ]; then
                cleanup_temp_dir "$temp_dir"
            fi
        done
        exit 130
    }
    trap cleanup_on_exit INT TERM
}

# Discover GAS projects by scanning projects/ directory
# Usage: discover_gas_projects "$gas_root"
# Returns: Array of project names via stdout (one per line)
discover_gas_projects() {
    local gas_root="${1:-}"
    
    if [ -z "$gas_root" ]; then
        gas_root=$(get_gas_root)
    fi
    
    local projects_dir="$gas_root/projects"
    
    if [ ! -d "$projects_dir" ]; then
        return 1
    fi
    
    # Find all directories with .clasp.json
    find "$projects_dir" -maxdepth 1 -mindepth 1 -type d | while read -r dir; do
        if [ -f "$dir/.clasp.json" ]; then
            basename "$dir"
        fi
    done
}

# Prepare comparison paths for pull operation
# Usage: prepare_comparison_paths "$project_dir" "$temp_pull_dir" "$has_esbuild" LOCAL_PATH_VAR REMOTE_PATH_VAR
# Sets: LOCAL_PATH and REMOTE_PATH variables
prepare_comparison_paths() {
    local project_dir="$1"
    local temp_pull_dir="$2"
    local has_esbuild="$3"
    local local_path_var="$4"
    local remote_path_var="$5"
    
    if [ "$has_esbuild" = true ]; then
        # For esbuild projects, compare local build vs remote Code.js
        # build.js now handles all artifacts, so we can use build/ directly
        # Just need to copy to temp for comparison (to avoid modifying original)
        local temp_build_compare_dir="$project_dir/.clasp_pull_build_compare"
        if [ -d "$temp_build_compare_dir" ]; then
            rm -rf "$temp_build_compare_dir"
        fi
        mkdir -p "$temp_build_compare_dir"
        
        # Copy entire build/ directory contents (Code.js, appsscript.json, HTML files)
        if [ -d "$project_dir/build" ]; then
            cp -r "$project_dir/build"/* "$temp_build_compare_dir/" 2>/dev/null || true
        fi
        
        eval "$local_path_var='$temp_build_compare_dir'"
        eval "$remote_path_var='$temp_pull_dir'"
    else
        # For non-esbuild projects, compare local src/ vs remote pulled files
        local temp_organized_dir="$project_dir/.clasp_pull_organized"
        if [ -d "$temp_organized_dir" ]; then
            rm -rf "$temp_organized_dir"
        fi
        mkdir -p "$temp_organized_dir/src"
        
        # Copy all pulled files to organized structure
        if [ -d "$temp_pull_dir" ]; then
            find "$temp_pull_dir" -type f \( -name "*.gs" -o -name "*.js" -o -name "*.html" \) ! -name "Code.js" | while read -r file; do
                rel_path="${file#$temp_pull_dir/}"
                cp "$file" "$temp_organized_dir/src/$rel_path"
            done
        fi
        
        eval "$local_path_var='$project_dir/src'"
        eval "$remote_path_var='$temp_organized_dir/src'"
    fi
}

# Copy build artifacts to temp directory for push
# Usage: copy_build_artifacts "$project_dir" "$temp_build_dir"
# Note: build.js now handles copying Code.js, appsscript.json, and HTML files to build/
# This function just copies everything from build/ to temp directory
copy_build_artifacts() {
    local project_dir="$1"
    local temp_build_dir="$2"
    
    local build_dir="$project_dir/build"
    
    if [ ! -d "$build_dir" ]; then
        log_error "Build directory not found: $build_dir"
        return 1
    fi
    
    # Copy all files from build/ to temp directory
    log_info "Copying build artifacts to temp directory..."
    
    # Copy Code.js (required)
    if [ ! -f "$build_dir/Code.js" ]; then
        log_error "Build output not found: $build_dir/Code.js"
        return 1
    fi
    cp "$build_dir/Code.js" "$temp_build_dir/Code.js"
    
    # Copy appsscript.json if it exists in build/
    if [ -f "$build_dir/appsscript.json" ]; then
        cp "$build_dir/appsscript.json" "$temp_build_dir/appsscript.json"
    fi
    
    # Copy all HTML files from build/ (build.js now copies them there)
    if [ -d "$build_dir" ]; then
        find "$build_dir" -name "*.html" -type f | while read -r html_file; do
            rel_path="${html_file#$build_dir/}"
            dest_path="$temp_build_dir/$rel_path"
            dest_dir=$(dirname "$dest_path")
            mkdir -p "$dest_dir"
            cp "$html_file" "$dest_path"
        done
    fi
    
    # Copy .clasp.json to temp with normalized rootDir
    if [ -f "$project_dir/.clasp.json" ]; then
        normalize_clasp_json "$project_dir/.clasp.json" "$temp_build_dir/.clasp.json"
    else
        log_error ".clasp.json not found in project directory"
        return 1
    fi
    
    log_success "Build artifacts copied"
    return 0
}

# Check if project uses esbuild
# Usage: check_project_type "$project_dir" HAS_ESBUILD_VAR
# Sets: HAS_ESBUILD variable (true/false)
check_project_type() {
    local project_dir="$1"
    local has_esbuild_var="$2"
    
    if [ -f "$project_dir/esbuild.config.js" ]; then
        eval "$has_esbuild_var=true"
    else
        eval "$has_esbuild_var=false"
    fi
}

# Validate project has required structure
# Usage: validate_project_structure "$project_dir" "$has_esbuild"
# Returns: 0 on success, 1 on failure
validate_project_structure() {
    local project_dir="$1"
    local has_esbuild="$2"
    
    if [ "$has_esbuild" = false ]; then
        if [ ! -d "$project_dir/src" ]; then
            log_error "src/ directory not found in project directory"
            return 1
        fi
    fi
    
    return 0
}

# Run comparison between local and remote
# Usage: run_comparison "$local_path" "$remote_path" "$compare_type" HAS_CHANGES_VAR ["$project_name"]
# Sets: HAS_CHANGES variable (true/false) and displays comparison output
run_comparison() {
    local local_path="$1"
    local remote_path="$2"
    local compare_type="$3"  # "push" or "pull"
    local has_changes_var="$4"
    local project_name="${5:-}"  # Optional project name for identifier
    
    local compare_script=""
    local compare_cmd=""
    
    if [ "$compare_type" = "push" ]; then
        compare_script="$REPO_ROOT/scripts/file_comparison/compare_project_remote_with_local.py"
        if [ ! -f "$compare_script" ]; then
            log_error "Comparison script not found: $compare_script"
            return 1
        fi
        if [ -n "$project_name" ]; then
            compare_cmd="python3 \"$compare_script\" --local-path \"$local_path\" --identifier \"$project_name\" --keep-temp 2>&1"
        else
            compare_cmd="python3 \"$compare_script\" --local-path \"$local_path\" --keep-temp 2>&1"
        fi
    else
        compare_script="$REPO_ROOT/scripts/file_comparison/compare_at_path.py"
        if [ ! -f "$compare_script" ]; then
            log_error "Comparison script not found: $compare_script"
            return 1
        fi
        compare_cmd="python3 \"$compare_script\" \"$local_path\" \"$remote_path\" 2>&1"
    fi
    
    log_info "🔍 Comparing local vs remote..."
    
    local compare_output
    compare_output=$(eval "$compare_cmd")
    local compare_exit_code=$?
    
    # Display comparison results
    echo ""
    echo "$compare_output"
    echo ""
    
    # Parse comparison output
    if parse_comparison_output "$compare_output"; then
        eval "$has_changes_var=false"
    else
        eval "$has_changes_var=true"
    fi
    
    return 0
}

# Check for doGet/doPost function changes (warning only)
# Usage: check_webapp_changes "$gas_root"
# Returns: 0 if no changes or check skipped, 1 if error
check_webapp_changes() {
    local gas_root="$1"
    local detect_script="$gas_root/remote-sync-tools/detect-webapp-changes.sh"
    
    if [ -f "$detect_script" ]; then
        "$detect_script" --staged >/dev/null 2>&1 || true
    fi
    
    return 0
}

# Cleanup old GAS deployments
# Usage: cleanup_old_deployments MAX_VERSIONS CLEANUP_THRESHOLD KEEP_RECENT
# Returns: 0 on success, 1 on failure
cleanup_old_deployments() {
    local max_versions="${1:-200}"
    local cleanup_threshold="${2:-190}"
    local keep_recent="${3:-10}"
    
    log_info "🧹 Checking if version cleanup is needed..."
    
    # Get deployments (try JSON first, fallback to text)
    local deployments_json
    deployments_json=$(clasp deployments --json 2>/dev/null || echo "")
    local deployment_count=0
    local deployments_data=""
    
    if [ -n "$deployments_json" ] && echo "$deployments_json" | grep -q "deploymentId"; then
        # JSON format - count deployments with version numbers
        deployment_count=$(echo "$deployments_json" | grep -c '"versionNumber"' || echo "0")
        deployments_data="$deployments_json"
    else
        # Text format fallback
        local deployments_output
        deployments_output=$(clasp deployments 2>&1 || echo "")
        deployment_count=$(echo "$deployments_output" | grep -c "@[0-9]" || echo "0")
        deployments_data="$deployments_output"
    fi
    
    if [ "$deployment_count" -lt "$cleanup_threshold" ]; then
        log_info "✅ No cleanup needed (${deployment_count} < ${cleanup_threshold})"
        return 0
    fi
    
    log_warning "🚨 Cleanup needed! Current: $deployment_count, Threshold: $cleanup_threshold"
    
    # Parse deployment IDs and versions
    local target_count=$((max_versions - 20))
    local to_delete=$((deployment_count - target_count))
    
    if [ "$to_delete" -le 0 ]; then
        log_info "✅ No cleanup needed (within target range)"
        return 0
    fi
    
    log_info "🗑️  Deleting $to_delete old deployments..."
    
    local deleted_count=0
    local failed_count=0
    
    # Extract deployment IDs with versions, sort by version (oldest first)
    if echo "$deployments_data" | grep -q '"versionNumber"'; then
        # JSON format
        while IFS= read -r deployment_id; do
            local version
            version=$(echo "$deployments_data" | grep -A 5 "\"$deployment_id\"" | grep -oP '"versionNumber"\s*:\s*\d+' | grep -oP '\d+' | head -1)
            if [ -n "$deployment_id" ] && [ -n "$version" ]; then
                log_info "  Deleting deployment $deployment_id (version $version)..."
                if clasp undeploy "$deployment_id" >/dev/null 2>&1; then
                    deleted_count=$((deleted_count + 1))
                else
                    failed_count=$((failed_count + 1))
                    log_warning "  Failed to delete $deployment_id"
                fi
                sleep 1  # Rate limiting
            fi
        done < <(echo "$deployments_data" | grep -oP '"deploymentId"\s*:\s*"[^"]+"' | sed 's/.*"\([^"]*\)".*/\1/' | head -n "$to_delete")
    else
        # Text format
        while IFS= read -r version deployment_id; do
            if [ -n "$deployment_id" ]; then
                log_info "  Deleting deployment $deployment_id (version $version)..."
                if clasp undeploy "$deployment_id" >/dev/null 2>&1; then
                    deleted_count=$((deleted_count + 1))
                else
                    failed_count=$((failed_count + 1))
                    log_warning "  Failed to delete $deployment_id"
                fi
                sleep 1  # Rate limiting
            fi
        done < <(echo "$deployments_data" | grep "@[0-9]" | sed 's/^-\s*\([A-Za-z0-9_-]*\)\s*@\([0-9]*\).*/\2 \1/' | sort -n | head -n "$to_delete")
    fi
    
    log_success "Cleanup complete: ${deleted_count} deleted, ${failed_count} failed"
    return 0
}

# Create new GAS deployment
# Usage: create_deployment "$project_dir" DEPLOYMENT_ID_VAR VERSION_NUMBER_VAR WEB_APP_URL_VAR
# Sets: DEPLOYMENT_ID, VERSION_NUMBER, WEB_APP_URL variables
create_deployment() {
    local project_dir="$1"
    local deployment_id_var="$2"
    local version_number_var="$3"
    local web_app_url_var="$4"
    
    log_info "🚀 Creating new deployment..."
    
    # Generate deployment description
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local git_commit
    git_commit=$(git rev-parse --short HEAD 2>/dev/null || echo "local")
    local description="Auto-deploy ${timestamp} (${git_commit})"
    
    # Create deployment
    local deploy_output
    deploy_output=$(clasp deploy --description "$description" 2>&1)
    
    # Parse deployment ID and version from output
    local deployment_id
    deployment_id=$(echo "$deploy_output" | grep -oP '(?<=- )AKfycb[a-zA-Z0-9_-]+' | head -1)
    local version_number
    version_number=$(echo "$deploy_output" | grep -oP '(?<=Version )\d+' | head -1)
    
    eval "$deployment_id_var='$deployment_id'"
    eval "$version_number_var='$version_number'"
    
    if [ -n "$deployment_id" ] && [ -n "$version_number" ]; then
        log_success "✅ Deployment successful!"
        log_info "🏷️  Version: $version_number"
        log_info "🆔 Deployment ID: $deployment_id"
        
        # Get script ID for web app URL
        local script_id
        script_id=$(grep -oP '(?<="scriptId":")[^"]+' "$project_dir/.clasp.json" 2>/dev/null || echo "")
        if [ -n "$script_id" ] && [ -n "$deployment_id" ]; then
            local web_app_url="https://script.google.com/macros/s/${deployment_id}/exec"
            eval "$web_app_url_var='$web_app_url'"
            log_info "🌐 Web App URL: $web_app_url"
        fi
    else
        log_warning "⚠️  Deployment may have succeeded, but couldn't parse output"
        echo "$deploy_output"
    fi
    
    return 0
}
