#!/bin/bash
#
# Setup script for Render API credentials
# Run this once after getting your API key and Service ID
#

echo "🔧 Setting up Render API credentials..."
echo ""

# Get API key
read -p "Enter your Render API Key: " -s RENDER_API_KEY
echo ""

# Get Service ID
read -p "Enter your Render Service ID (srv-xxxxx): " RENDER_SERVICE_ID
echo ""

# Add to shell profile
SHELL_PROFILE=""
if [ -f ~/.zshrc ]; then
    SHELL_PROFILE=~/.zshrc
elif [ -f ~/.bashrc ]; then
    SHELL_PROFILE=~/.bashrc
elif [ -f ~/.bash_profile ]; then
    SHELL_PROFILE=~/.bash_profile
else
    echo "❌ Could not find shell profile file"
    exit 1
fi

echo "📝 Adding environment variables to $SHELL_PROFILE"

# Append to shell profile
cat >> "$SHELL_PROFILE" << EOF

# Render API credentials for BARS project
export RENDER_API_KEY="$RENDER_API_KEY"
export RENDER_SERVICE_ID="$RENDER_SERVICE_ID"
EOF

echo "✅ Environment variables added to $SHELL_PROFILE"
echo ""
echo "🔄 Please restart your terminal or run:"
echo "   source $SHELL_PROFILE"
echo ""
echo "🧪 Test the setup with:"
echo "   ./scripts/deploy_to_render.sh --dry-run"
echo ""
echo "🚀 Deploy to Render with:"
echo "   ./scripts/deploy_to_render.sh"
echo ""
echo "🔐 Sync secrets only (no deployment):"
echo "   ./scripts/deploy_to_render.sh --secrets-only"
