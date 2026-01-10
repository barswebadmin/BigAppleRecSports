#!/bin/bash

# Script to compare AWS Lambda function code with local code
# Usage: ./compare_aws_to_local.sh

set -e

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

AWS_REGION="${AWS_REGION:-us-east-1}"
FUNCTIONS=(
    "MoveInventoryLambda"
    "ScheduleChangesForShopifyProductsLambda"
    "changePricesOfOpenAndWaitlistVariants"
    "setProductLiveByAddingInventory"
    "shopifyProductUpdateHandler"
)

LAYER_NAME="bars-common-utils"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Check AWS credentials
if ! aws sts get-caller-identity &>/dev/null; then
    log_error "AWS credentials not configured. Please run 'aws configure' or set AWS credentials."
    exit 1
fi

log_info "AWS credentials verified"
echo ""

# Create temp directory for AWS code
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

log_info "Created temporary directory: $TEMP_DIR"
echo ""

# Compare Lambda Functions
echo "=========================================="
echo "LAMBDA FUNCTION COMPARISON"
echo "=========================================="
echo ""

for FUNCTION in "${FUNCTIONS[@]}"; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "Comparing: $FUNCTION"
    echo ""
    
    LOCAL_DIR="$PROJECT_ROOT/lambda-functions/$FUNCTION"
    
    # Check if function exists locally
    if [ ! -d "$LOCAL_DIR" ]; then
        log_warning "Local directory not found: $LOCAL_DIR"
        echo ""
        continue
    fi
    
    # Check if function exists in AWS
    if ! aws lambda get-function --function-name "$FUNCTION" --region "$AWS_REGION" &>/dev/null; then
        log_warning "Function not found in AWS: $FUNCTION"
        echo ""
        continue
    fi
    
    # Download AWS function code
    AWS_TEMP="$TEMP_DIR/$FUNCTION"
    mkdir -p "$AWS_TEMP"
    
    log_info "Downloading AWS function code..."
    aws lambda get-function --function-name "$FUNCTION" --region "$AWS_REGION" \
        --query 'Code.Location' --output text | xargs curl -s -o "$AWS_TEMP/function.zip"
    
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
    elif [ ! -f "$LOCAL_FILE" ]; then
        log_error "Local lambda_function.py not found: $LOCAL_FILE"
    elif [ ! -f "$AWS_FILE" ]; then
        log_warning "AWS lambda_function.py not found in downloaded code"
    fi
    
    # Compare other Python files
    echo ""
    log_info "Comparing other Python files..."
    LOCAL_PY_FILES=$(find "$LOCAL_DIR" -name "*.py" -type f ! -name "__*" | sort)
    AWS_PY_FILES=$(find "$AWS_TEMP" -name "*.py" -type f ! -name "__*" | sort)
    
    # Files only in local
    for file in $LOCAL_PY_FILES; do
        rel_path="${file#$LOCAL_DIR/}"
        aws_file=$(find "$AWS_TEMP" -name "$(basename "$file")" -type f | head -1)
        if [ -z "$aws_file" ]; then
            log_warning "  Only in local: $rel_path"
        fi
    done
    
    # Files only in AWS
    for file in $AWS_PY_FILES; do
        rel_path="${file#$AWS_TEMP/}"
        local_file="$LOCAL_DIR/$(basename "$file")"
        if [ ! -f "$local_file" ]; then
            log_warning "  Only in AWS: $rel_path"
        fi
    done
    
    # Compare requirements.txt if exists
    if [ -f "$LOCAL_DIR/requirements.txt" ]; then
        AWS_REQ=$(find "$AWS_TEMP" -name "requirements.txt" -type f | head -1)
        if [ -f "$AWS_REQ" ]; then
            if diff -q "$LOCAL_DIR/requirements.txt" "$AWS_REQ" &>/dev/null; then
                log_success "requirements.txt: IDENTICAL"
            else
                log_warning "requirements.txt: DIFFERENT"
            fi
        else
            log_warning "requirements.txt: Only in local"
        fi
    fi
    
    echo ""
done

# Compare Lambda Layer
echo "=========================================="
echo "LAMBDA LAYER COMPARISON"
echo "=========================================="
echo ""

log_info "Comparing layer: $LAYER_NAME"
echo ""

LOCAL_LAYER_DIR="$PROJECT_ROOT/lambda-layers/$LAYER_NAME/python/bars_common_utils"

# Check if layer exists locally
if [ ! -d "$LOCAL_LAYER_DIR" ]; then
    log_warning "Local layer directory not found: $LOCAL_LAYER_DIR"
else
    # Get latest layer version from AWS
    LAYER_VERSION=$(aws lambda list-layer-versions \
        --layer-name "$LAYER_NAME" \
        --region "$AWS_REGION" \
        --query 'LayerVersions[0].Version' \
        --output text 2>/dev/null)
    
    if [ "$LAYER_VERSION" = "None" ] || [ -z "$LAYER_VERSION" ]; then
        log_warning "Layer not found in AWS: $LAYER_NAME"
    else
        log_info "Latest layer version in AWS: $LAYER_VERSION"
        
        # Download layer
        LAYER_TEMP="$TEMP_DIR/layer"
        mkdir -p "$LAYER_TEMP"
        
        log_info "Downloading layer code..."
        aws lambda get-layer-version \
            --layer-name "$LAYER_NAME" \
            --version-number "$LAYER_VERSION" \
            --region "$AWS_REGION" \
            --query 'Content.Location' \
            --output text | xargs curl -s -o "$LAYER_TEMP/layer.zip"
        
        unzip -q "$LAYER_TEMP/layer.zip" -d "$LAYER_TEMP" 2>/dev/null
        
        AWS_LAYER_DIR="$LAYER_TEMP/python/bars_common_utils"
        
        if [ -d "$AWS_LAYER_DIR" ]; then
            # Compare Python files in layer
            log_info "Comparing layer Python files..."
            
            LOCAL_PY_FILES=$(find "$LOCAL_LAYER_DIR" -name "*.py" -type f ! -name "__*" | sort)
            AWS_PY_FILES=$(find "$AWS_LAYER_DIR" -name "*.py" -type f ! -name "__*" | sort)
            
            for local_file in $LOCAL_PY_FILES; do
                rel_path="${local_file#$LOCAL_LAYER_DIR/}"
                aws_file="$AWS_LAYER_DIR/$rel_path"
                
                if [ -f "$aws_file" ]; then
                    if diff -q "$local_file" "$aws_file" &>/dev/null; then
                        log_success "  $rel_path: IDENTICAL"
                    else
                        log_warning "  $rel_path: DIFFERENT"
                        echo "    Differences:"
                        diff -u "$aws_file" "$local_file" | head -20 | sed 's/^/    /' || true
                    fi
                else
                    log_warning "  $rel_path: Only in local"
                fi
            done
            
            # Files only in AWS
            for aws_file in $AWS_PY_FILES; do
                rel_path="${aws_file#$AWS_LAYER_DIR/}"
                local_file="$LOCAL_LAYER_DIR/$rel_path"
                
                if [ ! -f "$local_file" ]; then
                    log_warning "  $rel_path: Only in AWS"
                fi
            done
        else
            log_warning "Could not extract layer code for comparison"
        fi
    fi
fi

echo ""
log_success "Comparison complete!"
echo ""
log_info "Temporary files will be cleaned up automatically"

