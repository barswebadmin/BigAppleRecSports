#!/usr/bin/env python3
"""Install dependencies for CI workflows."""
import subprocess
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts._shared.path_utils import PROJECT_ROOT


def install_backend_deps():
    """Install backend test dependencies."""
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
        check=True
    )
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(PROJECT_ROOT / "backend" / "requirements.txt")],
        check=True
    )
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "rich"],
        check=True
    )


def install_lambda_deps():
    """Install Lambda test dependencies."""
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
        check=True
    )
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "pytest", "pytest-asyncio", "rich"],
        check=True
    )


def install_deploy_deps():
    """Install deployment dependencies."""
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
        check=True
    )
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "boto3", "requests"],
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
