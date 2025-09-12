#!/bin/bash
#
# Deploy to Render with automatic secret sync
#
# Usage:
#   ./scripts/deploy_to_render.sh [--dry-run] [--secrets-only]
#
# Options:
#   --dry-run       Show what would change without making changes
#   --secrets-only  Sync secrets but don't trigger deployment
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Parse arguments
DRY_RUN=""
SECRETS_ONLY=""
DEPLOY_FLAG="--deploy"

for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN="--dry-run"
            ;;
        --secrets-only)
            SECRETS_ONLY="true"
            DEPLOY_FLAG=""
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Usage: $0 [--dry-run] [--secrets-only]"
            exit 1
            ;;
    esac
done

cd "$PROJECT_ROOT"

echo "🎯 BARS Render Deployment Script"
echo "================================="

# Check if we're in the right directory
if [ ! -f ".env" ]; then
    echo "❌ No .env file found in current directory"
    echo "   Please run this script from the project root"
    exit 1
fi

# Check for required environment variables
if [ -z "$RENDER_API_KEY" ]; then
    echo "❌ RENDER_API_KEY not set. Run setup first:"
    echo "   ./setup_render_env.sh"
    exit 1
fi

if [ -z "$RENDER_SERVICE_ID" ]; then
    echo "❌ RENDER_SERVICE_ID not set. Run setup first:"
    echo "   ./setup_render_env.sh"
    exit 1
fi

# Show what we're about to do
if [ -n "$DRY_RUN" ]; then
    echo "🔍 DRY RUN MODE - No changes will be made"
elif [ -n "$SECRETS_ONLY" ]; then
    echo "🔐 SECRETS ONLY MODE - Will sync secrets but not deploy"
else
    echo "🚀 FULL DEPLOYMENT MODE - Will sync secrets and deploy"
fi

echo ""

# Run the pre-deploy script
python3 scripts/pre_deploy_render.py $DRY_RUN $DEPLOY_FLAG

# Show next steps if secrets-only
if [ -n "$SECRETS_ONLY" ] && [ -z "$DRY_RUN" ]; then
    echo ""
    echo "✅ Secrets synced successfully!"
    echo "🚀 To deploy now, run:"
    echo "   ./scripts/deploy_to_render.sh"
    echo ""
    echo "🌐 Or manually trigger deployment in Render dashboard:"
    echo "   https://dashboard.render.com/web/$RENDER_SERVICE_ID"
fi
