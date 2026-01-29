#!/usr/bin/env python3
"""
Local development setup script.

Sets up development environment tools:
- direnv hook in .zshrc
- .envrc file creation
- IDE Python interpreter configuration
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def setup_direnv() -> bool:
    """Setup direnv hook and .envrc file."""
    print("  Setting up direnv...")
    
    result = subprocess.run(["command", "-v", "direnv"], shell=True, capture_output=True)
    if result.returncode != 0:
        print("    ⚠️  direnv not found. Installing via Homebrew...")
        if subprocess.run(["command", "-v", "brew"], shell=True, capture_output=True).returncode == 0:
            result = subprocess.run(["brew", "install", "direnv"], capture_output=True, text=True)
            if result.returncode == 0:
                print("    ✅ direnv installed")
            else:
                print("    ⚠️  Failed to install direnv")
                return False
        else:
            print("    ❌ Homebrew not found. Please install direnv manually: https://direnv.net/docs/installation.html")
            return False
    else:
        print("    ✅ direnv already installed")

    zshrc_path = Path.home() / '.zshrc'
    if not zshrc_path.exists():
        zshrc_path.touch()

    zshrc_content = zshrc_path.read_text()
    if 'eval "$(direnv hook zsh)"' not in zshrc_content:
        with zshrc_path.open('a') as f:
            f.write('\n')
            f.write('# direnv hook for automatic .envrc loading\n')
            f.write('eval "$(direnv hook zsh)"\n')
        print("    ✅ Added direnv hook to ~/.zshrc")
    else:
        print("    ℹ️  direnv hook already exists in ~/.zshrc")

    envrc_path = REPO_ROOT / ".envrc"
    if not envrc_path.exists():
        envrc_example = REPO_ROOT / ".envrc.example"
        if envrc_example.exists():
            import shutil
            shutil.copy(envrc_example, envrc_path)
            print("    ✅ Created .envrc from .envrc.example")
        else:
            envrc_content = """#!/bin/sh
# direnv configuration - see .envrc.example for full template
export PYTHONPATH="$(pwd)/backend:$(pwd)/lambda/layers/bars-common-utils/python:$(pwd)/shared-utilities/src:${PYTHONPATH}"
"""
            envrc_path.write_text(envrc_content)
            print("    ✅ Created basic .envrc")
    else:
        print("    ℹ️  .envrc already exists")

    result = subprocess.run(["command", "-v", "direnv"], shell=True, capture_output=True)
    if result.returncode == 0:
        result = subprocess.run(["direnv", "allow", str(REPO_ROOT)], capture_output=True, text=True)
        if result.returncode == 0:
            print("    ✅ direnv allowed")
        else:
            print("    ⚠️  direnv allow failed (may need manual approval)")
    else:
        print("    ⚠️  direnv not available. Run 'direnv allow' manually after installation.")

    return True


def setup_ide_interpreter() -> bool:
    """Setup VS Code Python interpreter from pipx venv."""
    print("  Setting up IDE Python interpreter...")
    
    pipx_venv = Path.home() / ".local" / "pipx" / "venvs" / "bars"
    if not pipx_venv.exists():
        print("    ℹ️  pipx venv not found, skipping IDE setup")
        return True

    pipx_python = pipx_venv / "bin" / "python"
    if not pipx_python.exists():
        print("    ⚠️  pipx Python interpreter not found")
        return False

    vscode_dir = REPO_ROOT / ".vscode"
    vscode_dir.mkdir(exist_ok=True)
    settings_file = vscode_dir / "settings.json"

    try:
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                settings = json.load(f)
        else:
            settings = {}

        settings['python.defaultInterpreterPath'] = str(pipx_python)

        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)

        print(f"    ✅ Updated .vscode/settings.json with pipx Python interpreter")
        return True
    except Exception as e:
        print(f"    ⚠️  Failed to update .vscode/settings.json: {e}")
        return False


def install_local_dev() -> bool:
    """Run all local development setup steps."""
    print("🔧 Setting up local development environment...")
    
    success = True
    success &= setup_direnv()
    success &= setup_ide_interpreter()
    
    return success


if __name__ == "__main__":
    success = install_local_dev()
    sys.exit(0 if success else 1)
