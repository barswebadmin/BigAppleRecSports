#!/usr/bin/env python3
"""Centralized test runner for all BARS test suites."""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional


def get_repo_for_path(path: str) -> str:
    """Determine which repo a path belongs to.
    
    Args:
        path: Path to check
        
    Returns:
        'backend', 'lambda', 'gas', or 'unknown'
    """
    path_obj = Path(path).resolve()
    path_str = str(path_obj)
    
    if "backend" in path_str:
        return "backend"
    elif "lambda" in path_str or "lambda-functions" in path_str:
        return "lambda"
    elif "GoogleAppsScripts" in path_str or "gas" in path_str.lower():
        return "gas"
    else:
        return "unknown"


def find_python() -> str:
    """Find Python interpreter matching pyproject.toml requirements."""
    project_root = Path(__file__).parent.parent.parent
    pyproject_path = project_root / "pyproject.toml"
    
    if not pyproject_path.exists():
        raise RuntimeError(f"pyproject.toml not found at {pyproject_path}")
    
    content = pyproject_path.read_text()
    match = re.search(r'requires-python\s*=\s*"([^"]+)"', content)
    if not match:
        raise RuntimeError("requires-python not found in pyproject.toml")
    
    required_version = match.group(1)
    
    candidates = [
        project_root / ".venv" / "bin" / "python",
        Path("python3"),
    ]
    
    for candidate in candidates:
        python_cmd = str(candidate) if candidate != Path("python3") else "python3"
        
        try:
            if candidate == Path("python3"):
                result = subprocess.run(
                    ["python3", "--version"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=5
                )
            elif candidate.exists():
                result = subprocess.run(
                    [str(candidate), "--version"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=5
                )
            else:
                continue
            
            version_str = result.stdout.strip()
            version_match = re.search(r"(\d+)\.(\d+)", version_str)
            if not version_match:
                continue
            
            major, minor = int(version_match.group(1)), int(version_match.group(2))
            
            if ">=" in required_version:
                min_version = required_version.split(">=")[1].split(",")[0].strip()
                min_match = re.search(r"(\d+)\.(\d+)", min_version)
                if min_match:
                    min_major, min_minor = int(min_match.group(1)), int(min_match.group(2))
                    if major < min_major or (major == min_major and minor < min_minor):
                        continue
            
            if "," in required_version and "<" in required_version:
                max_version = required_version.split("<")[1].strip()
                max_match = re.search(r"(\d+)\.(\d+)", max_version)
                if max_match:
                    max_major, max_minor = int(max_match.group(1)), int(max_match.group(2))
                    if major > max_major or (major == max_major and minor >= max_minor):
                        continue
            
            return python_cmd
        except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
            continue
    
    raise RuntimeError(
        f"No Python interpreter found matching requires-python={required_version} from pyproject.toml. "
        f"Checked: {[str(c) for c in candidates]}"
    )


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
    
    test_paths = []
    if not test_type or test_type == "unit":
        if (backend_dir / "tests" / "unit").exists():
            test_paths.append("tests/unit")
        if (backend_dir / "services").exists():
            test_paths.extend([str(p) for p in (backend_dir / "services").rglob("tests") if p.is_dir()])
        if (backend_dir / "routers" / "tests").exists():
            test_paths.append("routers/tests")
    
    if not test_type or test_type == "integration":
        if (backend_dir / "tests" / "integration").exists():
            test_paths.append("tests/integration")
    
    if not test_paths:
        print("⚠️  No test files found")
        return 0
    
    print(f"🧪 Running backend tests ({test_type or 'all'})...")
    cmd = [python, "-m", "pytest", "-v"] + test_paths
    result = subprocess.run(cmd, cwd=backend_dir, check=False)
    return result.returncode


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
    
    test_paths = []
    if not test_type or test_type == "unit":
        if (lambda_dir / "tests" / "unit").exists():
            test_paths.append("tests/unit")
    if not test_type or test_type == "integration":
        if (lambda_dir / "tests" / "integration").exists():
            test_paths.append("tests/integration")
    
    if not test_paths:
        print("⚠️  No test files found")
        return 0
    
    print(f"🧪 Running lambda tests ({test_type or 'all'})...")
    cmd = [python, "-m", "pytest", "-v"] + test_paths
    result = subprocess.run(cmd, cwd=lambda_dir, check=False)
    return result.returncode


def run_gas_tests() -> int:
    """Run GAS tests."""
    gas_dir = Path("GoogleAppsScripts").resolve()
    
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            print("❌ Node.js not found")
            return 0
        print(f"✅ Node.js found: {result.stdout.strip()}")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("❌ Node.js not found")
        return 0
    
    exit_code = 0
    
    test_scripts = []
    if (gas_dir / "tests").exists():
        test_scripts.extend((gas_dir / "tests").glob("*.sh"))
    if (gas_dir / "projects").exists():
        for project_dir in (gas_dir / "projects").iterdir():
            if project_dir.is_dir() and (project_dir / "tests").exists():
                test_scripts.extend((project_dir / "tests").glob("*.sh"))
                test_scripts.extend((project_dir / "tests").glob("*.js"))
    
    print(f"🧪 Running {len(test_scripts)} GAS test scripts...")
    
    for test_file in sorted(test_scripts):
        test_dir = test_file.parent
        
        if test_file.suffix == ".sh":
            os.chmod(test_file, 0o755)
            cmd = ["bash", str(test_file)]
            cwd = gas_dir
        else:
            if (test_dir / "package.json").exists():
                try:
                    subprocess.run(["npm", "--version"], capture_output=True, check=True, timeout=5)
                    print(f"📦 Installing dependencies in {test_dir.name}...")
                    subprocess.check_call(["npm", "install", "--silent"], cwd=test_dir, timeout=300)
                except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    pass
            cmd = ["node", str(test_file)]
            cwd = test_dir
        
        print(f"   Running: {test_file.relative_to(gas_dir)}")
        try:
            result = subprocess.run(cmd, cwd=cwd, check=False)
            if result.returncode != 0:
                exit_code = result.returncode
        except Exception as e:
            print(f"❌ Error: {e}")
            exit_code = 1
    
    return exit_code


def run_all_tests() -> int:
    """Run all test suites."""
    exit_code = 0
    for suite_func in [run_backend_tests, run_lambda_tests, run_gas_tests]:
        result = suite_func()
        if result != 0:
            exit_code = result
    return exit_code


def compile_backend() -> int:
    """Compile backend using compilation helpers."""
    import sys
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    from scripts.compilation_helpers.compilation_check_main import run_all_checks, ensure_cli_paths_setup
    
    ensure_cli_paths_setup()
    try:
        results = run_all_checks(check_types=False, target_path="backend")
        has_errors = (
            len(results.syntax_errors) > 0 or
            len(results.import_errors) > 0 or
            len(results.unused_imports) > 0 or
            len(results.type_errors) > 0 or
            len(results.required_defaults) > 0
        )
        return 0 if results.total_files > 0 and not has_errors else 1
    except Exception as e:
        print(f"❌ Compilation error: {e}")
        return 1


def compile_lambda() -> int:
    """Compile Lambda functions using compilation helpers."""
    import sys
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    from scripts.compilation_helpers.compilation_check_main import run_all_checks, ensure_cli_paths_setup
    
    ensure_cli_paths_setup()
    try:
        results = run_all_checks(check_types=False, target_path="lambda")
        has_errors = (
            len(results.syntax_errors) > 0 or
            len(results.import_errors) > 0 or
            len(results.unused_imports) > 0 or
            len(results.type_errors) > 0 or
            len(results.required_defaults) > 0
        )
        return 0 if results.total_files > 0 and not has_errors else 1
    except Exception as e:
        print(f"❌ Compilation error: {e}")
        return 1


def compile_gas() -> int:
    """Compile Google Apps Scripts."""
    return 0


def compile_all() -> int:
    """Compile all repos."""
    exit_code = 0
    for compile_func in [compile_backend, compile_lambda, compile_gas]:
        result = compile_func()
        if result != 0:
            exit_code = result
    return exit_code


def compile_for_path(path: str) -> int:
    """Compile for a specific path.
    
    Args:
        path: Path to compile (e.g., "backend", "lambda/functions", "GoogleAppsScripts")
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    repo = get_repo_for_path(path)
    
    if repo == "backend":
        return compile_backend()
    elif repo == "lambda":
        return compile_lambda()
    elif repo == "gas":
        return compile_gas()
    else:
        print(f"⚠️  Unknown path: {path}")
        print("   Supported paths: backend, lambda/functions, GoogleAppsScripts")
        return 1


def run_tests_for_path(path: str) -> int:
    """Run tests for a specific path.
    
    Args:
        path: Path to test (e.g., "backend", "lambda/functions", "GoogleAppsScripts")
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    repo = get_repo_for_path(path)
    
    if repo == "backend":
        return run_backend_tests()
    elif repo == "lambda":
        return run_lambda_tests()
    elif repo == "gas":
        return run_gas_tests()
    else:
        print(f"⚠️  Unknown path: {path}")
        print("   Supported paths: backend, lambda/functions, GoogleAppsScripts")
        return 1
