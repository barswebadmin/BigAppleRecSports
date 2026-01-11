#!/bin/bash
#
# Compare AWS Lambda function code with local code
# Usage: ./compare_aws_to_local.sh [function-name]
#

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAMBDA_DIR="$REPO_ROOT/lambda/functions"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

log_error() {
    echo -e "${RED}❌${NC} $1"
}

# Check AWS credentials
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    log_error "AWS credentials not configured or expired!"
    echo "   Please run: assume bars (or aws configure/aws sso login)"
    exit 1
fi

# Get function name from argument or discover all functions
if [ -n "$1" ]; then
    FUNCTIONS=("$1")
else
    # Discover all Lambda functions
    FUNCTIONS=()
    for dir in "$LAMBDA_DIR"/*; do
        if [ -d "$dir" ] && [ -f "$dir/lambda_function.py" ]; then
            FUNCTIONS+=("$(basename "$dir")")
        fi
    done
fi

if [ ${#FUNCTIONS[@]} -eq 0 ]; then
    log_error "No Lambda functions found in $LAMBDA_DIR"
    exit 1
fi

log_info "Found ${#FUNCTIONS[@]} function(s) to compare"
echo ""

# Create temp directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

for FUNCTION in "${FUNCTIONS[@]}"; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔍 Comparing: $FUNCTION"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    LOCAL_DIR="$LAMBDA_DIR/$FUNCTION"
    
    if [ ! -d "$LOCAL_DIR" ]; then
        log_warning "Local directory not found: $LOCAL_DIR"
        echo ""
        continue
    fi
    
    # Download AWS function code
    AWS_TEMP="$TEMP_DIR/$FUNCTION"
    mkdir -p "$AWS_TEMP"
    
    log_info "Downloading AWS function code..."
    if ! aws lambda get-function --function-name "$FUNCTION" --region "$AWS_REGION" \
        --query 'Code.Location' --output text 2>/dev/null | xargs curl -s -o "$AWS_TEMP/function.zip"; then
        log_warning "Could not download function code (function may not exist in AWS)"
        echo ""
        continue
    fi
    
    if [ ! -f "$AWS_TEMP/function.zip" ] || [ ! -s "$AWS_TEMP/function.zip" ]; then
        log_warning "Downloaded file is empty or missing"
        echo ""
        continue
    fi
    
    unzip -q "$AWS_TEMP/function.zip" -d "$AWS_TEMP" 2>/dev/null || {
        log_warning "Could not unzip AWS function code (might be a container image)"
        echo ""
        continue
    }
    
    # Compare main lambda_function.py
    LOCAL_FILE="$LOCAL_DIR/lambda_function.py"
    AWS_FILE=$(find "$AWS_TEMP" -name "lambda_function.py" -type f | head -1)
    
    if [ -f "$LOCAL_FILE" ] && [ -f "$AWS_FILE" ]; then
        if diff -q "$LOCAL_FILE" "$AWS_FILE" &>/dev/null; then
            log_success "lambda_function.py: IDENTICAL"
        else
            log_warning "lambda_function.py: DIFFERENT"
            echo ""
            echo "Differences:"
            diff -u "$AWS_FILE" "$LOCAL_FILE" | head -50 || true
            echo ""
        fi
    else
        if [ ! -f "$LOCAL_FILE" ]; then
            log_warning "Local lambda_function.py not found"
        fi
        if [ ! -f "$AWS_FILE" ]; then
            log_warning "AWS lambda_function.py not found in downloaded code"
        fi
    fi
    
    # Compare other Python files
    for local_file in "$LOCAL_DIR"/*.py; do
        if [ -f "$local_file" ]; then
            filename=$(basename "$local_file")
            aws_file=$(find "$AWS_TEMP" -name "$filename" -type f | head -1)
            
            if [ -f "$aws_file" ]; then
                if diff -q "$local_file" "$aws_file" &>/dev/null; then
                    log_success "$filename: IDENTICAL"
                else
                    log_warning "$filename: DIFFERENT"
                fi
            else
                log_warning "$filename: Only in local"
            fi
        fi
    done
    
    # Check for files only in AWS
    for aws_file in "$AWS_TEMP"/*.py; do
        if [ -f "$aws_file" ]; then
            filename=$(basename "$aws_file")
            if [ ! -f "$LOCAL_DIR/$filename" ]; then
                log_warning "$filename: Only in AWS"
            fi
        fi
    done
    
    echo ""
done

log_success "Comparison complete"
