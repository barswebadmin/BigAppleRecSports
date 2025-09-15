#!/bin/bash

# Deploy ScheduleChangesForShopifyProductsLambda manually
# This script packages and deploys the lambda function to AWS

set -e

echo "🚀 Deploying ScheduleChangesForShopifyProductsLambda..."

# Function details
FUNCTION_NAME="ScheduleChangesForShopifyProductsLambda"
FUNCTION_DIR="lambda-functions/$FUNCTION_NAME"
ZIP_FILE="${FUNCTION_NAME}.zip"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Check if function directory exists
if [ ! -d "$FUNCTION_DIR" ]; then
    echo "❌ Function directory $FUNCTION_DIR not found!"
    exit 1
fi

# Check AWS credentials
echo "🔐 Checking AWS credentials..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS credentials not configured or expired!"
    echo "Please run: aws configure or aws sso login"
    exit 1
fi

# Create deployment package
echo "📦 Creating deployment package..."
cd "$FUNCTION_DIR"

# Remove old zip if exists
rm -f "$ZIP_FILE"

# Create zip with all python files
zip -r "$ZIP_FILE" *.py bars_common_utils/

# Check if zip was created successfully
if [ ! -f "$ZIP_FILE" ]; then
    echo "❌ Failed to create deployment package!"
    exit 1
fi

echo "📊 Package size: $(du -h $ZIP_FILE | cut -f1)"

# Deploy to AWS Lambda
echo "☁️ Deploying to AWS Lambda..."
aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file "fileb://$ZIP_FILE" \
    --region "$AWS_REGION"

if [ $? -eq 0 ]; then
    echo "✅ Successfully deployed $FUNCTION_NAME!"
else
    echo "❌ Deployment failed!"
    exit 1
fi

# Clean up
rm -f "$ZIP_FILE"
echo "🧹 Cleaned up deployment package"

echo "🎉 Deployment complete!"
echo ""
echo "📋 Changes included:"
echo "   - Added numberVetSpotsToReleaseAtGoLive support"
echo "   - Enhanced logging for inventory information"
echo "   - Updated documentation"
