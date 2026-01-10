#!/bin/bash
#
# Deploy a single Lambda function
# Usage: deploy_lambda_function.sh <function-name> [--skip-diff] [--skip-confirm]
#

set -e

FUNCTION_NAME="$1"
SKIP_DIFF="${2:-}"
SKIP_CONFIRM="${3:-}"

if [ -z "$FUNCTION_NAME" ]; then
    echo "❌ Function name required"
    echo "Usage: $0 <function-name> [--skip-diff] [--skip-confirm]"
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FUNCTION_DIR="$REPO_ROOT/lambda/functions/$FUNCTION_NAME"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Validate function directory exists
if [ ! -d "$FUNCTION_DIR" ]; then
    echo "❌ Function directory not found: $FUNCTION_DIR"
    exit 1
fi

if [ ! -f "$FUNCTION_DIR/lambda_function.py" ]; then
    echo "❌ lambda_function.py not found in $FUNCTION_DIR"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS credentials not configured or expired!"
    echo "   Please run: assume bars (or aws configure/aws sso login)"
    exit 1
fi

# Check for diffs if comparison script exists
if [ "$SKIP_DIFF" != "--skip-diff" ]; then
    COMPARE_SCRIPT="$REPO_ROOT/scripts/file_comparison/compare_project_remote_with_local.py"
    if [ -f "$COMPARE_SCRIPT" ]; then
        echo "🔍 Checking for differences with remote..."
        COMPARE_OUTPUT=$(python3 "$COMPARE_SCRIPT" --local-path "lambda/functions/$FUNCTION_NAME" 2>&1)
        echo "$COMPARE_OUTPUT"
        if echo "$COMPARE_OUTPUT" | grep -qi "no changes detected\|identical\|no differences"; then
            echo ""
            echo "✅ No changes detected - skipping deployment"
            exit 0
        fi
        echo ""
        echo "⚠️  Differences detected. Review the output above."
        echo ""
    else
        echo "ℹ️  Comparison script not found - skipping diff check"
    fi
fi

# Prompt for confirmation
if [ "$SKIP_CONFIRM" != "--skip-confirm" ]; then
    read -p "🚀 Deploy $FUNCTION_NAME? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Deployment cancelled"
        exit 0
    fi
fi

# Deploy function
echo "🚀 Deploying Lambda function: $FUNCTION_NAME"
echo "📁 Directory: $FUNCTION_DIR"

cd "$FUNCTION_DIR"

# Extract version
VERSION=$(grep "__version__" lambda_function.py 2>/dev/null | cut -d'"' -f2 || echo "1.0.0")
echo "📦 Version: $VERSION"

# Create deployment package
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

echo "📦 Creating deployment package..."
cp *.py "$TEMP_DIR/" 2>/dev/null || true

if [ -d "bars_common_utils" ]; then
    cp -r bars_common_utils "$TEMP_DIR/"
fi

if [ -f "requirements.txt" ]; then
    echo "📋 Installing dependencies..."
    pip install -r requirements.txt -t "$TEMP_DIR/" --quiet
fi

cd "$TEMP_DIR"
ZIP_FILE="/tmp/$FUNCTION_NAME.zip"
zip -r "$ZIP_FILE" . -q
cd - > /dev/null

echo "📊 Package size: $(du -h $ZIP_FILE | cut -f1)"

# Deploy to AWS Lambda
echo "☁️  Deploying to AWS Lambda..."
DESCRIPTION="Version $VERSION - Updated $(date '+%Y-%m-%d %H:%M:%S')"
aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --description "$DESCRIPTION" \
    --region "$AWS_REGION" > /dev/null 2>&1 || true

aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$AWS_REGION" 2>/dev/null || true

aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file "fileb://$ZIP_FILE" \
    --region "$AWS_REGION" \
    --publish

rm -f "$ZIP_FILE"
echo "✅ Successfully deployed $FUNCTION_NAME version $VERSION!"
