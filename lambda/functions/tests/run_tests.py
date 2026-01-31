#!/usr/bin/env python3
"""Lambda test runner."""

import os
import subprocess
import sys
from pathlib import Path


def setup_test_environment():
    """Set up environment variables and paths for Lambda tests."""
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    
    # Add lambda functions and common utils to path
    lambda_root = Path(__file__).parent.parent.parent
    functions_root = lambda_root / "functions"
    common_utils = lambda_root / "layers" / "bars_common_utils"
    
    paths_to_add = [str(functions_root)]
    if common_utils.exists():
        paths_to_add.append(str(common_utils))
    
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    os.environ["PYTHONPATH"] = ":".join(paths_to_add + [os.environ.get("PYTHONPATH", "")])


def ensure_pytest():
    """Ensure pytest is installed."""
    try:
        subprocess.run(
            [sys.executable, "-c", "import pytest"],
            capture_output=True,
            check=True,
            timeout=5
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        print("📦 Installing pytest...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", "pytest", "pytest-asyncio"]
        )


def discover_test_paths(test_type: str | None = None) -> list[str]:
    """Discover test paths based on test type.
    
    Args:
        test_type: 'unit', 'integration', or None for all
        
    Returns:
        List of test paths relative to lambda/functions directory
    """
    functions_dir = Path(__file__).parent.parent
    test_paths = []
    
    if not test_type or test_type == "unit":
        if (functions_dir / "tests" / "unit").exists():
            test_paths.append("tests/unit")
    
    if not test_type or test_type == "integration":
        if (functions_dir / "tests" / "integration").exists():
            test_paths.append("tests/integration")
    
    return test_paths


def run_tests(test_type: str | None = None) -> int:
    """Run Lambda tests.
    
    Args:
        test_type: 'unit', 'integration', or None for all
        
    Returns:
        Exit code (0 for success)
    """
    setup_test_environment()
    ensure_pytest()
    
    functions_dir = Path(__file__).parent.parent
    test_paths = discover_test_paths(test_type)
    
    if not test_paths:
        print("⚠️  No test files found")
        return 0
    
    print(f"🧪 Running lambda tests ({test_type or 'all'})...")
    cmd = [sys.executable, "-m", "pytest", "-v"] + test_paths
    result = subprocess.run(cmd, cwd=functions_dir, check=False)
    return result.returncode


if __name__ == "__main__":
    test_type = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(run_tests(test_type))
