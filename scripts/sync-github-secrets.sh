#!/bin/bash

# Script to sync environment variables to GitHub repository secrets
# Usage: ./sync-github-secrets.sh [environment]
# Environment: production (default) or staging

set -e

ENVIRONMENT=${1:-production}
REPO="barswebadmin/BigAppleRecSports"

echo "🔑 Syncing secrets to GitHub repository: $REPO"
echo "🎯 Environment: $ENVIRONMENT"
echo

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed."
    echo "Install with: brew install gh"
    echo "Then authenticate with: gh auth login"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub CLI."
    echo "Run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI is installed and authenticated"
echo

# Function to add secret
add_secret() {
    local secret_name=$1
    local secret_value=$2

    if [ -z "$secret_value" ]; then
        echo "⚠️  Skipping $secret_name (empty value)"
        return
    fi

    echo "🔐 Adding secret: $secret_name"
    echo "$secret_value" | gh secret set "$secret_name" --repo="$REPO" --env="$ENVIRONMENT"
}

# Backend/API secrets
echo "📦 Adding backend secrets..."
add_secret "SLACK_REFUNDS_BOT_TOKEN" "$SLACK_REFUNDS_BOT_TOKEN"
add_secret "SHOPIFY_TOKEN" "$SHOPIFY_TOKEN"
add_secret "SHOPIFY_STORE" "$SHOPIFY_STORE"
add_secret "SLACK_WEBHOOK_SECRET" "$SLACK_WEBHOOK_SECRET"

# AWS secrets for Lambda deployment
echo "⚡ Adding AWS secrets..."
add_secret "AWS_ACCESS_KEY_ID" "$AWS_ACCESS_KEY_ID"
add_secret "AWS_SECRET_ACCESS_KEY" "$AWS_SECRET_ACCESS_KEY"

# Render deployment secrets
echo "🌐 Adding Render secrets..."
add_secret "RENDER_DEPLOY_HOOK_URL" "$RENDER_DEPLOY_HOOK_URL"

echo
echo "✅ All secrets have been synced to GitHub!"
echo "🔍 View secrets: https://github.com/$REPO/settings/environments/$ENVIRONMENT"
echo
echo "💡 Usage tips:"
echo "   • Secrets are encrypted and only accessible to workflows"
echo "   • Use \${{ secrets.SECRET_NAME }} in your workflows"
echo "   • Never log secret values in workflows"
