#!/bin/bash

# Script to sync secrets from .env file to GitHub repository
# Usage: ./sync-secrets-from-env.sh [env-file] [environment]

set -e

ENV_FILE=${1:-".env"}
ENVIRONMENT=${2:-production}
REPO="barswebadmin/BigAppleRecSports"

echo "🔑 Syncing secrets from $ENV_FILE to GitHub"
echo "🎯 Repository: $REPO"
echo "🌍 Environment: $ENVIRONMENT"
echo

# Check if env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Environment file not found: $ENV_FILE"
    echo "💡 Create one or specify path: ./sync-secrets-from-env.sh /path/to/.env"
    exit 1
fi

# Check if gh CLI is installed and authenticated
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed."
    echo "📥 Install with: brew install gh"
    exit 1
fi

if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub CLI."
    echo "🔐 Run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI ready"
echo

# List of secrets to sync (add/remove as needed)
SECRETS_TO_SYNC=(
    "SLACK_REFUNDS_BOT_TOKEN"
    "SHOPIFY_TOKEN"
    "SHOPIFY_STORE"
    "SLACK_WEBHOOK_SECRET"
    "AWS_ACCESS_KEY_ID"
    "AWS_SECRET_ACCESS_KEY"
    "RENDER_DEPLOY_HOOK_URL"
)

# Function to get value from env file
get_env_value() {
    local key=$1
    grep "^$key=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2- | sed 's/^"\(.*\)"$/\1/' || echo ""
}

# Sync secrets
echo "🔄 Syncing secrets..."
synced=0
skipped=0

for secret in "${SECRETS_TO_SYNC[@]}"; do
    value=$(get_env_value "$secret")

    if [ -z "$value" ]; then
        echo "⚠️  Skipping $secret (not found in $ENV_FILE)"
        ((skipped++))
        continue
    fi

    echo "🔐 Syncing: $secret"
    echo "$value" | gh secret set "$secret" --repo="$REPO"
    ((synced++))
done

echo
echo "📊 Summary:"
echo "   ✅ Synced: $synced secrets"
echo "   ⚠️  Skipped: $skipped secrets"
echo
echo "🔍 View in GitHub: https://github.com/$REPO/settings/environments/$ENVIRONMENT"
echo
echo "🛡️  Security reminders:"
echo "   • Never commit .env files to git"
echo "   • Rotate secrets regularly"
echo "   • Use different secrets for different environments"
