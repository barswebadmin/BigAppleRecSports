#!/bin/bash
#
# Unified Lambda function deployment script
# Supports both interactive (single function) and batch (CI/CD) modes
#
# Usage:
#   Interactive: deploy_aws.sh <function-name> [--skip-diff] [--skip-confirm] [--no-update-description]
#   Batch:       deploy_aws.sh --batch <function1> [<function2> ...] [--no-update-description]
#

set -e

# Detect if running in CI/CD (non-interactive) environment
IS_CI="${CI:-false}"
if [ -z "${TERM:-}" ] || [ ! -t 0 ]; then
    IS_CI="true"
fi

# Parse arguments
BATCH_MODE=false
FUNCTIONS=()
SKIP_DIFF=false
SKIP_CONFIRM=false
UPDATE_DESCRIPTION=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --batch)
            BATCH_MODE=true
            shift
            ;;
        --skip-diff)
            SKIP_DIFF=true
            shift
            ;;
        --skip-confirm)
            SKIP_CONFIRM=true
            shift
            ;;
        --no-update-description)
            UPDATE_DESCRIPTION=false
            shift
            ;;
        *)
            FUNCTIONS+=("$1")
            shift
            ;;
    esac
done

# In CI mode, auto-skip diff and confirm
if [ "$IS_CI" = "true" ]; then
    SKIP_DIFF=true
    SKIP_CONFIRM=true
    # In CI, don't update description by default (version management handles it)
    if [ "$UPDATE_DESCRIPTION" = "true" ] && [ -z "${FORCE_UPDATE_DESCRIPTION:-}" ]; then
        UPDATE_DESCRIPTION=false
    fi
fi

# Validate arguments
if [ "$BATCH_MODE" = "false" ] && [ ${#FUNCTIONS[@]} -eq 0 ]; then
    echo "❌ Function name required"
    echo ""
    echo "Usage:"
    echo "  Interactive: $0 <function-name> [--skip-diff] [--skip-confirm] [--no-update-description]"
    echo "  Batch:       $0 --batch <function1> [<function2> ...] [--no-update-description]"
    exit 1
fi

if [ "$BATCH_MODE" = "true" ] && [ ${#FUNCTIONS[@]} -eq 0 ]; then
    echo "❌ At least one function name required in batch mode"
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Check AWS credentials
if ! aws sts get-caller-identity --region "$AWS_REGION" > /dev/null 2>&1; then
    echo "❌ AWS credentials not configured or expired!"
    if [ "$IS_CI" != "true" ]; then
        echo "   Please run: assume bars (or aws configure/aws sso login)"
    fi
    exit 1
fi

# Function to deploy a single Lambda function
deploy_function() {
    local FUNCTION_NAME="$1"
    local FUNCTION_DIR="$REPO_ROOT/lambda/functions/$FUNCTION_NAME"
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🚀 Deploying Lambda function: $FUNCTION_NAME"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Validate function directory exists
    if [ ! -d "$FUNCTION_DIR" ]; then
        echo "❌ Function directory not found: $FUNCTION_DIR"
        return 1
    fi
    
    if [ ! -f "$FUNCTION_DIR/lambda_function.py" ]; then
        echo "❌ lambda_function.py not found in $FUNCTION_DIR"
        return 1
    fi
    
    # Check for differences with remote (interactive mode only)
    if [ "$SKIP_DIFF" = "false" ]; then
        COMPARE_SCRIPT="$REPO_ROOT/scripts/file_comparison/compare_project_remote_with_local.py"
        if [ -f "$COMPARE_SCRIPT" ]; then
            echo "🔍 Checking for differences with remote..."
            COMPARE_OUTPUT=$(python3 "$COMPARE_SCRIPT" --remote-origin-type aws --project-name "$FUNCTION_NAME" --local-path "$FUNCTION_DIR" 2>&1 || true)
            echo "$COMPARE_OUTPUT"
            if echo "$COMPARE_OUTPUT" | grep -qi "no changes detected\|identical\|no differences"; then
                echo ""
                echo "✅ No changes detected - skipping deployment"
                return 0
            fi
            echo ""
            echo "⚠️  Differences detected. Review the output above."
            echo ""
        else
            echo "ℹ️  Comparison script not found - skipping diff check"
        fi
    fi
    
    # Prompt for confirmation (interactive mode only)
    if [ "$SKIP_CONFIRM" = "false" ]; then
        read -p "🚀 Deploy $FUNCTION_NAME? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "❌ Deployment cancelled"
            return 0
        fi
    fi
    
    echo "📁 Directory: $FUNCTION_DIR"
    
    # Store version file path and read current version for description
    VERSION_FILE="$FUNCTION_DIR/version.json"
    CURRENT_VERSION=""
    if [ -f "$VERSION_FILE" ]; then
        CURRENT_VERSION=$(python3 -c "import json; print(json.load(open('$VERSION_FILE'))['version'])" 2>/dev/null || echo "")
    fi
    
    # Create temporary directory for packaging
    TEMP_DIR=$(mktemp -d)
    trap "rm -rf $TEMP_DIR" EXIT
    
    echo "📦 Creating deployment package..."
    
    # Copy all Python files
    cp "$FUNCTION_DIR"/*.py "$TEMP_DIR/" 2>/dev/null || true
    
    # Copy version.json if it exists
    if [ -f "$VERSION_FILE" ]; then
        echo "  📋 Copying version.json..."
        cp "$VERSION_FILE" "$TEMP_DIR/"
    fi
    
    # Copy bars_common_utils if it exists (legacy)
    if [ -d "$FUNCTION_DIR/bars_common_utils" ]; then
        echo "  📋 Copying bars_common_utils..."
        cp -r "$FUNCTION_DIR/bars_common_utils" "$TEMP_DIR/"
    fi
    
    # Copy shared_utilities if it exists (symlinked from repo root)
    if [ -d "$FUNCTION_DIR/shared_utilities" ]; then
        echo "  📋 Copying shared_utilities..."
        cp -r "$FUNCTION_DIR/shared_utilities" "$TEMP_DIR/"
    fi
    
    # Install dependencies if requirements.txt exists
    if [ -f "$FUNCTION_DIR/requirements.txt" ]; then
        echo "  📋 Installing dependencies..."
        pip install -r "$FUNCTION_DIR/requirements.txt" -t "$TEMP_DIR/" --quiet
    fi
    
    # Create deployment zip
    cd "$TEMP_DIR"
    ZIP_FILE="/tmp/${FUNCTION_NAME}.zip"
    zip -r "$ZIP_FILE" . -q
    cd - > /dev/null
    
    echo "  📊 Package size: $(du -h $ZIP_FILE | cut -f1)"
    
    # Update function configuration with description (if requested)
    if [ "$UPDATE_DESCRIPTION" = "true" ]; then
        echo "☁️  Updating function configuration..."
        if [ -n "$CURRENT_VERSION" ]; then
            DESCRIPTION="Version ${CURRENT_VERSION} - Updated $(date '+%Y-%m-%d %H:%M:%S')"
        else
            DESCRIPTION="Updated $(date '+%Y-%m-%d %H:%M:%S')"
        fi
        aws lambda update-function-configuration \
            --function-name "$FUNCTION_NAME" \
            --description "$DESCRIPTION" \
            --region "$AWS_REGION" > /dev/null 2>&1 || true
        
        # Wait for configuration update to complete
        echo "  ⏳ Waiting for configuration update..."
        aws lambda wait function-updated \
            --function-name "$FUNCTION_NAME" \
            --region "$AWS_REGION" 2>/dev/null || true
    fi
    
    # Deploy function code
    echo "☁️  Deploying to AWS Lambda..."
    if ! aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file "fileb://$ZIP_FILE" \
        --region "$AWS_REGION" \
        --publish; then
        echo "❌ Failed to update function code"
        rm -f "$ZIP_FILE"
        rm -rf "$TEMP_DIR"
        return 1
    fi
    
    # Wait for code update to complete
    echo "  ⏳ Waiting for function update to complete..."
    if ! aws lambda wait function-updated \
        --function-name "$FUNCTION_NAME" \
        --region "$AWS_REGION"; then
        echo "⚠️  Function update wait timed out or failed, but deployment may have succeeded"
    fi
    
    # Clean up
    rm -f "$ZIP_FILE"
    rm -rf "$TEMP_DIR"
    
    # Increment version.json only after successful deployment
    NEW_VERSION=""
    if [ -f "$VERSION_FILE" ]; then
        echo "📈 Incrementing version after successful deployment..."
        
        # Determine bump type (default to patch for manual deployments)
        BUMP_TYPE="patch"
        if [ "$IS_CI" = "true" ]; then
            # In CI, try to determine from commit messages
            if git log -1 --pretty=%B | grep -qiE "BREAKING|breaking change|major"; then
                BUMP_TYPE="major"
            elif git log -1 --pretty=%B | grep -qiE "feat:|feature:|add:|new:"; then
                BUMP_TYPE="minor"
            elif git log -1 --pretty=%B | grep -qiE "fix:|bugfix:|patch:|hotfix:"; then
                BUMP_TYPE="patch"
            fi
        fi
        
        # Get recent commit messages for changelog (newline-separated)
        COMMIT_MESSAGES=$(git log -5 --pretty=%B 2>/dev/null | head -20 || echo "Deployment")
        if [ -z "$COMMIT_MESSAGES" ] || [ "$COMMIT_MESSAGES" = "" ]; then
            COMMIT_MESSAGES="Deployment"
        fi
        
        # Create temp file for commit messages (version_manager expects newline-separated)
        COMMIT_MSG_FILE=$(mktemp)
        echo "$COMMIT_MESSAGES" > "$COMMIT_MSG_FILE"
        
        # Increment version using version_manager.py
        if python3 "$REPO_ROOT/scripts/deployment/version_manager.py" \
            --lambda-update "$FUNCTION_NAME:$VERSION_FILE:$BUMP_TYPE" \
            --commit-messages "$(cat "$COMMIT_MSG_FILE")" 2>&1; then
            # Read new version from version.json
            NEW_VERSION=$(python3 -c "import json; print(json.load(open('$VERSION_FILE'))['version'])" 2>/dev/null || echo "")
            if [ -n "$NEW_VERSION" ]; then
                echo "✅ Version incremented to: $NEW_VERSION"
            else
                # Fallback: try to read version directly
                NEW_VERSION=$(python3 -c "import json; f=open('$VERSION_FILE'); d=json.load(f); print(d.get('version', ''))" 2>/dev/null || echo "")
            fi
        else
            echo "⚠️  Version increment failed, trying to read current version..."
            # Try to read current version even if increment failed
            NEW_VERSION=$(python3 -c "import json; print(json.load(open('$VERSION_FILE'))['version'])" 2>/dev/null || echo "")
        fi
        rm -f "$COMMIT_MSG_FILE"
        
        # Stage version file for batch commit later (CI only)
        if [ "$IS_CI" = "true" ]; then
            # Check if version.json was modified
            if ! git diff --quiet "$VERSION_FILE" 2>/dev/null; then
                # Stage the version file for later commit
                git add "$VERSION_FILE" || true
            fi
        fi
    else
        echo "⚠️  version.json not found, skipping version increment"
    fi
    
    if [ -n "$NEW_VERSION" ]; then
        echo "✅ Successfully deployed $FUNCTION_NAME version $NEW_VERSION!"
    else
        echo "✅ Successfully deployed $FUNCTION_NAME!"
    fi
    
    return 0
}

# Deploy functions
EXIT_CODE=0
DEPLOYED_COUNT=0
FAILED_COUNT=0

if [ "$BATCH_MODE" = "true" ]; then
    echo "🚀 Batch deployment mode: ${#FUNCTIONS[@]} function(s)"
    for FUNC in "${FUNCTIONS[@]}"; do
        if deploy_function "$FUNC"; then
            ((DEPLOYED_COUNT++))
        else
            ((FAILED_COUNT++))
            EXIT_CODE=1
        fi
    done
    
    # Commit all version increments together after all functions are deployed (CI only)
    if [ "$IS_CI" = "true" ]; then
        # Check if any version.json files are staged
        if ! git diff --cached --quiet --exit-code 2>/dev/null; then
            echo ""
            echo "📝 Committing all version increments to merge commit..."
            # Amend to the current HEAD (merge commit) to include all version increments
            if git commit --amend --no-edit 2>/dev/null; then
                # Force push with lease to update the merge commit (safe in CI)
                if git push origin main --force-with-lease 2>/dev/null; then
                    echo "✅ All version increments included in merge commit"
                else
                    echo "⚠️  Failed to push version increments (may have been pushed already)"
                fi
            else
                echo "⚠️  Failed to amend commit (may have been committed already)"
            fi
        fi
    fi
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 Deployment Summary"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ Successfully deployed: $DEPLOYED_COUNT"
    if [ $FAILED_COUNT -gt 0 ]; then
        echo "❌ Failed: $FAILED_COUNT"
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    # Single function deployment
    deploy_function "${FUNCTIONS[0]}"
    EXIT_CODE=$?
    
    # Commit version increment for single function (CI only)
    if [ "$IS_CI" = "true" ]; then
        # Check if version.json is staged
        if ! git diff --cached --quiet --exit-code 2>/dev/null; then
            echo ""
            echo "📝 Committing version increment to merge commit..."
            # Amend to the current HEAD (merge commit) to include version increment
            if git commit --amend --no-edit 2>/dev/null; then
                # Force push with lease to update the merge commit (safe in CI)
                if git push origin main --force-with-lease 2>/dev/null; then
                    echo "✅ Version increment included in merge commit"
                else
                    echo "⚠️  Failed to push version increment (may have been pushed already)"
                fi
            else
                echo "⚠️  Failed to amend commit (may have been committed already)"
            fi
        fi
    fi
fi

exit $EXIT_CODE
