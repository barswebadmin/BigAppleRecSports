#!/usr/bin/env python3
"""Centralized test runner for all BARS test suites."""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from scripts._shared.path_utils import PROJECT_ROOT


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def find_python() -> str:
    """Find Python interpreter matching pyproject.toml requirements.
    
    Raises:
        RuntimeError: If pyproject.toml is missing, doesn't contain requires-python,
                      or the required Python interpreter is not found.
    """
    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    
    if not pyproject_path.exists():
        raise RuntimeError(f"pyproject.toml not found at {pyproject_path}")
    
    content = pyproject_path.read_text()
    match = re.search(r'requires-python\s*=\s*"([^"]+)"', content)
    if not match:
        raise RuntimeError("requires-python not found in pyproject.toml")
    
    required_version = match.group(1)
    
    # Extract minimum version from requires-python spec (e.g., ">=3.11,<3.12" -> "3.11")
    min_version_match = re.search(r'>=(\d+\.\d+)', required_version)
    if not min_version_match:
        raise RuntimeError(f"Could not parse minimum version from requires-python: {required_version}")
    
    target_version = min_version_match.group(1)
    python_cmd = f"python{target_version}"
    
    try:
        subprocess.run([python_cmd, "--version"], capture_output=True, check=True, timeout=5)
        return python_cmd
    except FileNotFoundError:
        raise RuntimeError(
            f"Python {target_version} not found. Install it with: make install "
            f"(requires-python={required_version})"
        )
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
        raise RuntimeError(f"Failed to verify Python {target_version}: {e}")


# ============================================================================
# INTERNAL HELPERS
# ============================================================================

def _discover_test_paths(test_dir: Path, test_type: Optional[str] = None, additional_paths: Optional[list[str]] = None) -> list[str]:
    """Discover test paths in a directory based on test type.
    
    Args:
        test_dir: Base directory to search for tests
        test_type: 'unit', 'integration', or None for both
        additional_paths: Optional list of additional relative paths to check (already discovered)
        
    Returns:
        List of relative test paths
    """
    test_paths = []
    
    if not test_type or test_type == "unit":
        unit_path = test_dir / "tests" / "unit"
        if unit_path.exists():
            test_paths.append("tests/unit")
        
        if additional_paths:
            test_paths.extend(additional_paths)
    
    if not test_type or test_type == "integration":
        integration_path = test_dir / "tests" / "integration"
        if integration_path.exists():
            test_paths.append("tests/integration")
    
    return test_paths


def _run_pytest_tests(python: str, test_dir: Path, test_paths: list[str], repo_name: str, test_type: Optional[str] = None) -> int:
    """Run pytest tests with common pattern.
    
    Args:
        python: Python interpreter path
        test_dir: Working directory for pytest
        test_paths: List of test paths to run
        repo_name: Name of repo (for logging)
        test_type: Test type (for logging)
        
    Returns:
        Exit code from pytest
    """
    if not test_paths:
        print("⚠️  No test files found")
        return 0
    
    print(f"🧪 Running {repo_name} tests ({test_type or 'all'})...")
    cmd = [python, "-m", "pytest", "-v"] + test_paths
    result = subprocess.run(cmd, cwd=test_dir, check=False)
    return result.returncode


# ============================================================================
# PUBLIC TEST FUNCTIONS
# ============================================================================

def run_backend_tests(test_type: Optional[str] = None) -> int:
    """Run backend tests."""
    python = find_python()
    backend_dir = Path("backend").resolve()
    
    os.environ.update({
        "SHOPIFY_URL_ADMIN_DOMAIN": "test-store.myshopify.com",
        "SHOPIFY_TOKEN": "test_token",
        "ENVIRONMENT": "test",
        "SLACK_REFUNDS_BOT_TOKEN": "test_slack_token",
    })
    
    # Discover additional test paths in services and routers (only for unit tests)
    additional_paths = []
    if not test_type or test_type == "unit":
        if (backend_dir / "services").exists():
            services_tests = [str(p.relative_to(backend_dir)) for p in (backend_dir / "services").rglob("tests") if p.is_dir()]
            additional_paths.extend(services_tests)
        if (backend_dir / "routers" / "tests").exists():
            additional_paths.append("routers/tests")
    
    test_paths = _discover_test_paths(backend_dir, test_type, additional_paths)
    return _run_pytest_tests(python, backend_dir, test_paths, "backend", test_type)


def run_lambda_tests(test_type: Optional[str] = None) -> int:
    """Run Lambda tests."""
    python = find_python()
    lambda_dir = Path("lambda/functions").resolve()
    
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    
    project_root = lambda_dir.parent.parent
    lambda_functions_root = project_root / "lambda" / "functions"
    bars_common_path = project_root / "lambda" / "layers" / "bars_common_utils"
    
    if str(lambda_functions_root) not in sys.path:
        sys.path.insert(0, str(lambda_functions_root))
    if bars_common_path.exists() and str(bars_common_path) not in sys.path:
        sys.path.insert(0, str(bars_common_path))
    
    os.environ["PYTHONPATH"] = ":".join([
        str(lambda_functions_root),
        str(bars_common_path) if bars_common_path.exists() else "",
        os.environ.get("PYTHONPATH", "")
    ])
    
    try:
        subprocess.run([python, "-c", "import pytest"], capture_output=True, check=True, timeout=5)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        print("📦 Installing pytest...")
        subprocess.check_call([python, "-m", "pip", "install", "--quiet", "pytest", "pytest-asyncio"])
    
    test_paths = _discover_test_paths(lambda_dir, test_type)
    return _run_pytest_tests(python, lambda_dir, test_paths, "lambda", test_type)


def run_gas_tests() -> int:
    """Run GAS tests - verify projects build successfully."""
    gas_root = PROJECT_ROOT / "GoogleAppsScripts"
    projects_dir = gas_root / "projects"
    build_script = PROJECT_ROOT / "scripts" / "deployment" / "google" / "build.js"
    
    if not projects_dir.exists():
        print(f"❌ GAS projects directory not found: {projects_dir}")
        return 1
    
    if not build_script.exists():
        print(f"❌ Build script not found: {build_script}")
        return 1
    
    # Check Node.js
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            print("❌ Node.js not found")
            return 1
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("❌ Node.js not found")
        return 1
    
    # Discover all GAS projects
    projects = sorted([d for d in projects_dir.iterdir() if d.is_dir() and not d.name.startswith('.')])
    
    if not projects:
        print("⚠️  No GAS projects found")
        return 1
    
    print(f"🧪 Testing {len(projects)} GAS projects (verifying builds)...")
    
    exit_code = 0
    
    for project_dir in projects:
        project_name = project_dir.name
        
        # Skip projects without esbuild.config.js (they don't use build system)
        if not (project_dir / "esbuild.config.js").exists():
            print(f"  ⏭️  {project_name}: No esbuild.config.js (skipping)")
            continue
        
        print(f"  🔨 {project_name}: Building...")
        
        # Build local project
        try:
            result = subprocess.run(
                ['node', str(build_script), str(project_dir)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(gas_root)
            )
            
            if result.returncode != 0:
                print(f"    ❌ Build failed")
                if result.stderr:
                    print(f"    {result.stderr}")
                exit_code = 1
            else:
                print(f"    ✅ Build successful")
                
        except subprocess.TimeoutExpired:
            print(f"    ❌ Build timed out")
            exit_code = 1
        except Exception as e:
            print(f"    ❌ Build error: {e}")
            exit_code = 1
    
    if exit_code == 0:
        print("✅ All GAS projects built successfully")
    else:
        print("❌ Some GAS project builds failed")
    
    return exit_code


# ============================================================================
# PUBLIC CONVENIENCE FUNCTIONS
# ============================================================================

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
    elif "lambda" in path_str or "lambda-functions" in path_str:
        return run_lambda_tests()
    elif "GoogleAppsScripts" in path_str or "gas" in path_str.lower():
        return run_gas_tests()
    else:
        print(f"⚠️  Unknown path: {path}")
        print("   Supported paths: backend, lambda/functions, GoogleAppsScripts")
        return 1


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

def main() -> int:
    """CLI entry point for testing module.
    
    Only runs when invoked directly (python -m scripts.testing or python scripts/testing/run_tests.py).
    Does NOT run when imported by other modules (e.g., CI workflows via run_script.py).
    """
    import sys
    
    # Import compilation functions only when CLI is invoked (lazy import to avoid dependency issues)
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
    elif command == "compile-lambda":
        return compile_lambda()
    elif command == "compile-gas":
        return compile_gas()
    elif command == "test-backend":
        return run_backend_tests()
    elif command == "test-lambda":
        return run_lambda_tests()
    elif command == "test-gas":
        return run_gas_tests()
    else:
        print(f"❌ Unknown command: {command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
