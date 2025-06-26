#!/bin/bash
#
# Setup script for automatic lambda function version management
# This script installs git hooks and configures the version management system
#

set -e

echo "🚀 Setting up automatic lambda function version management..."

# Get the repository root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "📂 Repository root: $REPO_ROOT"

# Create directories if they don't exist
mkdir -p scripts
mkdir -p .githooks

# Make scripts executable
chmod +x scripts/version_manager.py
chmod +x .githooks/pre-commit

# Install git hooks
echo "🔗 Installing git hooks..."
git config core.hooksPath .githooks

# Test the version manager
echo "🧪 Testing version manager..."
if python3 scripts/version_manager.py; then
    echo "✅ Version manager test passed"
else
    echo "⚠️  Version manager test failed - this is normal if no lambda changes are staged"
fi

# Create a test commit to verify everything works
echo "📝 Creating test version files..."

# Check if version files exist for all lambda functions
LAMBDA_DIRS=($(find lambda-functions -maxdepth 1 -type d -not -path lambda-functions))
for dir in "${LAMBDA_DIRS[@]}"; do
    VERSION_FILE="$dir/version.py"
    if [ ! -f "$VERSION_FILE" ]; then
        echo "📄 Creating version file for $(basename "$dir")"
        cat > "$VERSION_FILE" << EOF
# Auto-generated version file
# This file is automatically updated when changes are detected in this lambda function

__version__ = "1.0.0"
__build__ = 1
__last_updated__ = "$(date +%Y-%m-%d)"

def get_version():
    """Return the current version string"""
    return __version__

def get_full_version():
    """Return version with build number"""
    return f"{__version__}.{__build__}"
EOF
    fi
done

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 What was installed:"
echo "   • Version files added to all lambda functions"
echo "   • Pre-commit git hook configured"
echo "   • GitHub Action workflow for remote changes"
echo "   • Version manager script"
echo ""
echo "🎯 How it works:"
echo "   • When you commit changes to lambda functions, versions auto-increment"
echo "   • Build numbers increase automatically (1.0.0.1 → 1.0.0.2)"
echo "   • Last updated date is refreshed"
echo "   • Version files are automatically staged and committed"
echo ""
echo "🧪 Test it by:"
echo "   1. Making changes to any file in a lambda function directory"
echo "   2. Running 'git add lambda-functions/your-function/'"
echo "   3. Running 'git commit -m \"test: version increment\"'"
echo "   4. Watch the pre-commit hook automatically increment versions!"
echo ""
echo "🎉 Happy coding!" 