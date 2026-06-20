#!/usr/bin/env python3
"""Install dependencies for CI workflows using uv.

CI uses uv for fast, reliable dependency installation.
"""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared_utilities"))
from paths import get_repo_root

project_root = get_repo_root()
sys.path.insert(0, str(project_root))

from scripts._shared.path_utils import PROJECT_ROOT


def install_backend_deps():
    """Install backend dependencies including dev dependencies for testing."""
    backend_dir = PROJECT_ROOT / "backend"

    subprocess.run(
        ["uv", "sync"],
        cwd=backend_dir,
        env={**os.environ, "UV_NO_PROGRESS": "1"},
        check=True
    )

    subprocess.run(
        ["uv", "tool", "install", "rich"],
        env={**os.environ, "UV_NO_PROGRESS": "1"},
        check=True
    )


def install_lambda_deps():
    """Install Lambda test dependencies."""
    subprocess.run(
        ["uv", "tool", "install", "pytest"],
        env={**os.environ, "UV_NO_PROGRESS": "1"},
        check=True
    )
    subprocess.run(
        ["uv", "tool", "install", "pytest-asyncio"],
        env={**os.environ, "UV_NO_PROGRESS": "1"},
        check=True
    )
    subprocess.run(
        ["uv", "tool", "install", "rich"],
        env={**os.environ, "UV_NO_PROGRESS": "1"},
        check=True
    )
    subprocess.run(
        ["uv", "tool", "install", "ruff==0.14.0"],
        env={**os.environ, "UV_NO_PROGRESS": "1"},
        check=True
    )


def install_deploy_deps():
    """Install deployment dependencies."""
    subprocess.run(
        ["uv", "tool", "install", "boto3"],
        env={**os.environ, "UV_NO_PROGRESS": "1"},
        check=True
    )
    subprocess.run(
        ["uv", "tool", "install", "requests"],
        env={**os.environ, "UV_NO_PROGRESS": "1"},
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
