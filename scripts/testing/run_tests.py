#!/usr/bin/env python3
"""Thin wrapper for project-specific test runners.

This module delegates to project-specific test runners rather than
containing project-specific logic. Each project manages its own test
configuration, discovery, and execution.

Project test runners:
- backend/tests/run_tests.py
- lambda/functions/tests/run_tests.py
- GoogleAppsScripts/tests/run_tests.sh
"""

import subprocess
import sys
from pathlib import Path

from scripts._shared.path_utils import PROJECT_ROOT


def run_backend_tests(test_type: str | None = None) -> int:
    """Run backend tests via project-specific runner."""
    runner = PROJECT_ROOT / "backend" / "tests" / "run_tests.py"
    cmd = [sys.executable, str(runner)]
    if test_type:
        cmd.append(test_type)
    return subprocess.run(cmd, check=False).returncode


def run_lambda_tests(test_type: str | None = None) -> int:
    """Run Lambda tests via project-specific runner."""
    runner = PROJECT_ROOT / "lambda" / "functions" / "tests" / "run_tests.py"
    cmd = [sys.executable, str(runner)]
    if test_type:
        cmd.append(test_type)
    return subprocess.run(cmd, check=False).returncode


def run_gas_tests() -> int:
    """Run GAS tests via project-specific runner."""
    runner = PROJECT_ROOT / "GoogleAppsScripts" / "tests" / "run_tests.sh"
    return subprocess.run(["bash", str(runner)], check=False).returncode


def run_all_tests() -> int:
    """Run all test suites."""
    exit_code = 0
    for suite_func in [run_backend_tests, run_lambda_tests, run_gas_tests]:
        result = suite_func()
        if result != 0:
            exit_code = result
    return exit_code


def run_tests_for_path(path: str) -> int:
    """Run tests for a specific path.

    Args:
        path: Path to test (e.g., "backend", "lambda/functions", "GoogleAppsScripts")

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    path_obj = Path(path).resolve()
    path_str = str(path_obj)

    if "backend" in path_str:
        return run_backend_tests()
    if "lambda" in path_str or "lambda-functions" in path_str:
        return run_lambda_tests()
    if "GoogleAppsScripts" in path_str or "gas" in path_str.lower():
        return run_gas_tests()

    print(f"⚠️  Unknown path: {path}")
    print("   Supported paths: backend, lambda/functions, GoogleAppsScripts")
    return 1


def main() -> int:
    """CLI entry point for testing module."""
    from scripts.compilation.compile_main import (
        compile_backend,
        compile_gas,
        compile_lambda,
    )

    if len(sys.argv) < 2:
        print("Usage: python -m scripts.testing <command>")
        print("Commands:")
        print("  compile-backend  - Compile backend code")
        print("  compile-lambda   - Compile Lambda functions")
        print("  compile-gas      - Compile Google Apps Scripts")
        print("  test-backend     - Run backend tests")
        print("  test-lambda      - Run Lambda tests")
        print("  test-gas         - Run GAS tests")
        return 1

    command = sys.argv[1]

    if command == "compile-backend":
        return compile_backend()
    if command == "compile-lambda":
        return compile_lambda()
    if command == "compile-gas":
        return compile_gas()
    if command == "test-backend":
        return run_backend_tests()
    if command == "test-lambda":
        return run_lambda_tests()
    if command == "test-gas":
        return run_gas_tests()

    print(f"❌ Unknown command: {command}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

