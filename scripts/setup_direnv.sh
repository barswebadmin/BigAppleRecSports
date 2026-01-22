#!/bin/bash
# Setup direnv for the BARS project
# This script handles:
# - Checking/installing direnv
# - Setting up direnv hook in .zshrc
# - Creating .envrc file if needed
# - Allowing direnv for the current directory

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "  Checking for direnv..."
if ! command -v direnv >/dev/null 2>&1; then
    echo "    ⚠️  direnv not found. Installing via Homebrew..."
    if command -v brew >/dev/null 2>&1; then
        brew install direnv && echo "    ✅ direnv installed" || echo "    ⚠️  Failed to install direnv"
    else
        echo "    ❌ Homebrew not found. Please install direnv manually: https://direnv.net/docs/installation.html"
    fi
else
    echo "    ✅ direnv already installed"
fi

echo "  Setting up direnv hook in .zshrc..."
if ! grep -q 'eval "$(direnv hook zsh)"' ~/.zshrc 2>/dev/null; then
    echo '' >> ~/.zshrc
    echo '# direnv hook for automatic .envrc loading' >> ~/.zshrc
    echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc
    echo "    ✅ Added direnv hook to ~/.zshrc"
else
    echo "    ℹ️  direnv hook already exists in ~/.zshrc"
fi

echo "  Setting up .envrc file..."
if [ ! -f .envrc ]; then
    if [ -f .envrc.example ]; then
        cp .envrc.example .envrc
        echo "    ✅ Created .envrc from .envrc.example"
    else
        echo "    ⚠️  .envrc.example not found. Creating basic .envrc..."
        cat > .envrc << 'ENVRC_EOF'
#!/bin/sh
# direnv configuration - see .envrc.example for full template
export PYTHONPATH="$(pwd)/backend:$(pwd)/lambda-layers/bars-common-utils/python:$(pwd)/shared-utilities/src:${PYTHONPATH}"
ENVRC_EOF
    fi
else
    echo "    ℹ️  .envrc already exists"
fi

echo "  Setting up IDE Python interpreter..."
if [ -d "$HOME/.local/pipx/venvs/bars" ]; then
    PIPX_PYTHON="$HOME/.local/pipx/venvs/bars/bin/python"
    if [ -f "$PIPX_PYTHON" ]; then
        mkdir -p .vscode
        # Update .vscode/settings.json with Python interpreter (using jq if available, else python)
        if command -v jq >/dev/null 2>&1; then
            # Use jq to merge the setting
            if [ -f .vscode/settings.json ]; then
                jq ". + {\"python.defaultInterpreterPath\": \"$PIPX_PYTHON\"}" .vscode/settings.json > .vscode/settings.json.tmp && mv .vscode/settings.json.tmp .vscode/settings.json 2>/dev/null && echo "    ✅ Updated .vscode/settings.json with pipx Python interpreter" || echo "    ⚠️  Failed to update .vscode/settings.json"
            else
                echo "{\"python.defaultInterpreterPath\": \"$PIPX_PYTHON\"}" > .vscode/settings.json && echo "    ✅ Created .vscode/settings.json with pipx Python interpreter" || echo "    ⚠️  Failed to create .vscode/settings.json"
            fi
        else
            # Fallback to python for JSON manipulation
            python3 -c "
import json
import os
settings_file = '.vscode/settings.json'
try:
    with open(settings_file, 'r') as f:
        settings = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    settings = {}
settings['python.defaultInterpreterPath'] = '$PIPX_PYTHON'
with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)
" 2>/dev/null && echo "    ✅ Updated .vscode/settings.json with pipx Python interpreter" || echo "    ⚠️  Failed to update .vscode/settings.json"
        fi
    else
        echo "    ⚠️  pipx Python interpreter not found at $PIPX_PYTHON"
    fi
else
    echo "    ℹ️  pipx venv not found, skipping IDE setup"
fi

echo "  Allowing direnv for this directory..."
if command -v direnv >/dev/null 2>&1; then
    direnv allow . 2>/dev/null && echo "    ✅ direnv allowed" || echo "    ⚠️  direnv allow failed (may need manual approval)"
else
    echo "    ⚠️  direnv not available. Run 'direnv allow' manually after installation."
fi
