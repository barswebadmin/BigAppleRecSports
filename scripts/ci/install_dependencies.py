#!/usr/bin/env python3
"""Install dependencies for CI workflows.

Note: CI uses system Python, not UV venvs. Dependencies are installed globally
for the CI run. For local development, use UV with per-project venvs.
"""
import os
import subprocess
import sys
from pathlib import Path

# Add shared utilities to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared_utilities"))
from paths import get_repo_root

project_root = get_repo_root()
sys.path.insert(0, str(project_root))

from scripts._shared.path_utils import PROJECT_ROOT


def install_backend_deps():
    """Install backend dependencies including dev dependencies for testing."""
    backend_dir = PROJECT_ROOT / "backend"
    
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "--upgrade", "pip"],
        env={**os.environ, "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_PROGRESS_BAR": "off", "PIP_NO_INPUT": "1"},
        check=True
    )
    
    # Install shared_utilities first
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "-e", str(PROJECT_ROOT / "shared_utilities")],
        env={**os.environ, "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_PROGRESS_BAR": "off", "PIP_NO_INPUT": "1"},
        check=True
    )
    
    # Install backend dependencies from pyproject.toml
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "-e", str(backend_dir)],
        env={**os.environ, "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_PROGRESS_BAR": "off", "PIP_NO_INPUT": "1"},
        check=True
    )
    
    # Install dev dependencies
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "-e", f"{backend_dir}[dev]"],
        env={**os.environ, "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_PROGRESS_BAR": "off", "PIP_NO_INPUT": "1"},
        check=True
    )
    
    # Install rich for CI output formatting
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "rich"],
        env={**os.environ, "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_PROGRESS_BAR": "off", "PIP_NO_INPUT": "1"},
        check=True
    )


def install_lambda_deps():
    """Install Lambda test dependencies."""
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "--upgrade", "pip"],
        env={**os.environ, "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_PROGRESS_BAR": "off", "PIP_NO_INPUT": "1"},
        check=True
    )
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "pytest", "pytest-asyncio", "rich", "ruff==0.14.0"],
        env={**os.environ, "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_PROGRESS_BAR": "off", "PIP_NO_INPUT": "1"},
        check=True
    )


def install_deploy_deps():
    """Install deployment dependencies."""
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "--upgrade", "pip"],
        env={**os.environ, "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_PROGRESS_BAR": "off", "PIP_NO_INPUT": "1"},
        check=True
    )
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "boto3", "requests"],
        env={**os.environ, "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_PROGRESS_BAR": "off", "PIP_NO_INPUT": "1"},
        check=True
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/ci/install_dependencies.py <backend|lambda|deploy>")
        sys.exit(1)

    command = sys.argv[1]
    if command == "backend":
        install_backend_deps()
    elif command == "lambda":
        install_lambda_deps()
    elif command == "deploy":
        install_deploy_deps()
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)

