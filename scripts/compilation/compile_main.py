#!/usr/bin/env python3
"""Main compilation orchestration for all BARS repos."""

import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from scripts._shared.path_utils import PROJECT_ROOT

from .repo_path_resolvers import (
    find_all_python_files,
    find_repo_root,
    get_relative_path,
)
from .checkers._checkers_common import (
    CheckError,
    ensure_path_in_sys_path,
    to_check_errors,
)
from .checkers.circular_imports import check_circular_imports
from .checkers.required_defaults import check_required_defaults
from .checkers.syntax import check_syntax
from .checkers.type_check import check_types as run_type_check
from .checkers.unused_imports import get_unused_imports
from .display.renderers import (
    DisplaySection,
    DisplaySummary,
    build_display_data,
    display,
)


# ============================================================================
# Data Models
# ============================================================================

class ModuleCheckResult:
    """Represents the result of checking a single module."""
    def __init__(
        self,
        syntax_errors: List[CheckError],
        import_errors: List[CheckError],
        unused_imports: List[CheckError],
        type_errors: List[CheckError],
        required_defaults: List[CheckError]
    ):
        self.syntax_errors = syntax_errors or []
        self.import_errors = import_errors or []
        self.unused_imports = unused_imports or []
        self.type_errors = type_errors or []
        self.required_defaults = required_defaults or []


class CompilationCheckResults:
    """Aggregated results from checking all files."""
    def __init__(
        self,
        syntax_errors: Dict[str, List[CheckError]],
        import_errors: Dict[str, List[CheckError]],
        unused_imports: Dict[str, List[CheckError]],
        type_errors: Dict[str, List[CheckError]],
        required_defaults: Dict[str, List[CheckError]],
        total_files: int,
        check_types: bool = False
    ):
        self.syntax_errors = syntax_errors
        self.import_errors = import_errors
        self.unused_imports = unused_imports
        self.type_errors = type_errors
        self.required_defaults = required_defaults
        self.total_files = total_files
        self.check_types = check_types
    
    def has_errors(self) -> bool:
        """Check if any errors were found."""
        return (
            len(self.syntax_errors) > 0 or
            len(self.import_errors) > 0 or
            len(self.unused_imports) > 0 or
            len(self.type_errors) > 0 or
            len(self.required_defaults) > 0
        )


# ============================================================================
# Path Setup
# ============================================================================

def ensure_cli_paths_setup() -> None:
    """Ensure repo root and Python directories are in sys.path for CLI execution."""
    repo_root = find_repo_root()
    ensure_path_in_sys_path(repo_root)
    
    for python_dir in ["backend", "aws/lambda/functions"]:
        python_path = repo_root / python_dir
        if python_path.exists():
            ensure_path_in_sys_path(python_path)


def get_src_root_for_file(file_path: Path, repo_root: Path) -> Path:
    """Determine the src_root (Python directory) for a given file.
    
    Args:
        file_path: Path to the Python file
        repo_root: Repository root directory
        
    Returns:
        Path to the source root directory (backend/ or aws/lambda/functions/)
    """
    abs_path = file_path.resolve() if not file_path.is_absolute() else file_path
    abs_repo_root = repo_root.resolve()
    
    try:
        rel_path = abs_path.relative_to(abs_repo_root)
        parts = rel_path.parts
    except ValueError:
        parts = abs_path.parts
    
    if "backend" in parts:
        return abs_repo_root / "backend"
    elif "lambda" in parts and "functions" in parts:
        return abs_repo_root / "lambda" / "functions"
    else:
        return abs_repo_root


# ============================================================================
# Module Checking
# ============================================================================

def check_module(
    module_path: Path,
    repo_root: Path,
    src_root: Path,
    debug_messages: Optional[List[str]] = None,
    debug_lock: Optional[threading.Lock] = None,
    check_types: bool = False
) -> Tuple[str, ModuleCheckResult]:
    """Check a single module for syntax, import, and unused import errors."""
    module_name = get_relative_path(module_path, src_root)
    
    try:
        _, syntax_error_dicts = check_syntax(module_path, repo_root)
        syntax_errors = to_check_errors(syntax_error_dicts)
        
        import_success, import_error_dicts = check_circular_imports(module_path, src_root, debug_messages, debug_lock)
        import_errors = to_check_errors(import_error_dicts)
        
        unused_imports = []
        required_defaults = []
        if import_success:
            unused_import_dicts = get_unused_imports(module_path, src_root)
            unused_imports = to_check_errors(unused_import_dicts)
        
            required_default_dicts = check_required_defaults(module_path, src_root)
            required_defaults = to_check_errors(required_default_dicts)
        
        type_errors = []
        if check_types:
            _, type_error_dicts = run_type_check(module_path, repo_root)
            type_errors = to_check_errors(type_error_dicts)
        
        return module_name, ModuleCheckResult(
            syntax_errors=syntax_errors,
            import_errors=import_errors,
            unused_imports=unused_imports,
            type_errors=type_errors,
            required_defaults=required_defaults
        )
    except SystemExit as e:
        # If sys.exit() is called during checking, treat as import error
        from .checkers._checkers_common import create_error
        exit_code = e.code if hasattr(e, 'code') and e.code is not None else 1
        import_error = create_error(module_name, "IMPORT", f"Module called sys.exit({exit_code}) during check", import_path="")
        return module_name, ModuleCheckResult(
            syntax_errors=[],
            import_errors=to_check_errors([import_error]),
            unused_imports=[],
            type_errors=[],
            required_defaults=[]
        )


def _aggregate_result(
    result: ModuleCheckResult,
    all_syntax_errors: Dict[str, List[CheckError]],
    all_import_errors: Dict[str, List[CheckError]],
    all_unused_imports: Dict[str, List[CheckError]],
    all_type_errors: Dict[str, List[CheckError]],
    all_required_defaults: Dict[str, List[CheckError]],
    module_name: str
) -> None:
    """Aggregate a single module's check results into the overall results."""
    error_mappings = [
        (result.syntax_errors, all_syntax_errors),
        (result.import_errors, all_import_errors),
        (result.unused_imports, all_unused_imports),
        (result.type_errors, all_type_errors),
        (result.required_defaults, all_required_defaults),
    ]
    
    for errors, target_dict in error_mappings:
        if errors:
            target_dict[module_name] = errors


def run_all_checks(
    check_types: bool = False,
    max_workers: int = 8,
    target_path: str = "all"
) -> CompilationCheckResults:
    """Run all compilation checks on Python files in backend/ or aws/lambda/functions/."""
    console = Console()
    repo_root = find_repo_root()
    
    python_dirs = []
    if target_path == "all":
        for dir_name in ["backend", "aws/lambda/functions"]:
            dir_path = repo_root / dir_name
            if dir_path.exists():
                python_dirs.append(dir_path)
    elif target_path == "backend":
        python_dirs = [repo_root / "backend"] if (repo_root / "backend").exists() else []
    elif target_path == "lambda":
        python_dirs = [repo_root / "lambda" / "functions"] if (repo_root / "lambda" / "functions").exists() else []
    else:
        raise RuntimeError(f"Unknown target_path: {target_path}. Must be 'backend', 'lambda', or 'all'")
    
    if not python_dirs:
        raise RuntimeError(f"No Python directories found for target_path={target_path}")
    
    files = find_all_python_files(repo_root)
    if not files:
        return CompilationCheckResults({}, {}, {}, {}, {}, 0, check_types)
    
    if target_path != "all":
        filtered_files = []
        for file_path in files:
            if target_path == "backend" and "backend" in file_path.parts:
                filtered_files.append(file_path)
            elif target_path == "lambda" and "lambda" in file_path.parts and "functions" in file_path.parts:
                filtered_files.append(file_path)
        files = filtered_files
    
    if not files:
        return CompilationCheckResults({}, {}, {}, {}, {}, 0, check_types)
    
    total_files = len(files)
    
    all_syntax_errors: Dict[str, List[CheckError]] = {}
    all_import_errors: Dict[str, List[CheckError]] = {}
    all_unused_imports: Dict[str, List[CheckError]] = {}
    all_type_errors: Dict[str, List[CheckError]] = {}
    all_required_defaults: Dict[str, List[CheckError]] = {}
    debug_messages: List[str] = []
    debug_lock = threading.Lock()
    
    with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Checking files...", total=total_files)
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(
                        check_module,
                        file_path,
                        repo_root,
                        get_src_root_for_file(file_path, repo_root),
                        debug_messages,
                        debug_lock,
                        check_types=check_types
                    ): file_path
                    for file_path in files
                }
                
                for future in as_completed(future_to_file):
                    try:
                        module_name, result = future.result()
                        _aggregate_result(
                            result,
                            all_syntax_errors,
                            all_import_errors,
                            all_unused_imports,
                            all_type_errors,
                            all_required_defaults,
                            module_name
                        )
                    except SystemExit as e:
                        # sys.exit() called during module check - treat as import error
                        file_path = future_to_file[future]
                        src_root = get_src_root_for_file(file_path, repo_root)
                        module_name = get_relative_path(file_path, src_root)
                        exit_code = e.code if hasattr(e, 'code') and e.code is not None else 1
                        from .checkers._checkers_common import create_error, to_check_errors
                        import_error = to_check_errors([create_error(module_name, "IMPORT", f"Module called sys.exit({exit_code}) during check", import_path="")])[0]
                        all_import_errors[module_name] = [import_error]
                        console.print(f"[yellow]Warning: {module_name} called sys.exit() during check - treating as import error[/yellow]")
                    except Exception as e:
                        file_path = future_to_file[future]
                        src_root = get_src_root_for_file(file_path, repo_root)
                        module_name = get_relative_path(file_path, src_root)
                        console.print(f"[red]Error checking {module_name}: {e}[/red]")
                    finally:
                        progress.update(task, advance=1)  # type: ignore[arg-type]
    
    return CompilationCheckResults(
        syntax_errors=all_syntax_errors,
        import_errors=all_import_errors,
        unused_imports=all_unused_imports,
        type_errors=all_type_errors,
        required_defaults=all_required_defaults,
        total_files=total_files,
        check_types=check_types
    )


# ============================================================================
# Compilation Functions (Public API)
# ============================================================================

def _compile_python_code(target_path: str) -> int:
    """Shared logic for compiling Python code (backend/lambda).
    
    Args:
        target_path: Target path to check - "backend" or "lambda"
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    sys.path.insert(0, str(PROJECT_ROOT))
    ensure_cli_paths_setup()
    
    try:
        results = run_all_checks(check_types=False, target_path=target_path)
        
        # Display results
        console = Console()
        console.print("\n")
        
        sections, summary = build_display_data(
            syntax_errors=results.syntax_errors,  # type: ignore[arg-type]
            import_errors=results.import_errors,  # type: ignore[arg-type]
            unused_imports=results.unused_imports,  # type: ignore[arg-type]
            type_errors=results.type_errors,  # type: ignore[arg-type]
            required_defaults=results.required_defaults,  # type: ignore[arg-type]
            total_files=results.total_files,
            check_types=results.check_types
        )
        display(sections, summary)
        
        # Return 0 if files were checked and no errors, 1 otherwise
        if results.total_files == 0:
            console.print(f"[yellow]⚠️  No files found to check for {target_path}[/yellow]")
            return 1
        
        return 0 if not results.has_errors() else 1
    except Exception as e:
        console = Console()
        console.print(f"[red]❌ Compilation error: {e}[/red]")
        return 1


def compile_backend() -> int:
    """Compile backend code (syntax, types, imports, etc.)."""
    return _compile_python_code("backend")


def compile_lambda() -> int:
    """Compile Lambda function code (syntax, types, imports, etc.)."""
    return _compile_python_code("lambda")


def _validate_gas_project_json(project_dir: Path, project_name: str, errors: List[str]) -> None:
    """Validate appsscript.json for a GAS project."""
    appsscript_json = project_dir / "appsscript.json"
    
    if not appsscript_json.exists():
        errors.append(f"{project_name}: Missing appsscript.json")
        return
    
    try:
        with open(appsscript_json, 'r', encoding='utf-8') as f:
            json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"{project_name}: Invalid appsscript.json - {e}")
    except Exception as e:
        errors.append(f"{project_name}: Error reading appsscript.json - {e}")


def _build_gas_project(
    project_dir: Path,
    project_name: str,
    build_script: Path,
    gas_root: Path,
    errors: List[str]
) -> None:
    """Build a single GAS project using esbuild."""
    if not (project_dir / "esbuild.config.js").exists():
        print(f"  ⏭️  {project_name}: No esbuild.config.js (skipping)")
        return
    
    print(f"  🔨 {project_name}: Building...")
    
    try:
        result = subprocess.run(
            ['node', str(build_script), str(project_dir)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(gas_root)
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip()
            errors.append(f"{project_name}: Build failed\n{error_msg}")
            print(f"    ❌ Build failed")
        else:
            print(f"    ✅ Build successful")
            
    except subprocess.TimeoutExpired:
        errors.append(f"{project_name}: Build timed out after 60 seconds")
        print(f"    ❌ Build timed out")
    except Exception as e:
        errors.append(f"{project_name}: Error running build - {e}")
        print(f"    ❌ Build error: {e}")


def _print_gas_errors(errors: List[str], phase: str) -> None:
    """Print GAS compilation errors."""
    if errors:
        print(f"\n❌ GAS compilation errors ({phase}):")
        for error in errors:
            print(f"  - {error}")


def compile_gas() -> int:
    """Compile Google Apps Scripts by running esbuild (catches syntax errors)."""
    gas_root = PROJECT_ROOT / "google-apps-scripts"
    projects_dir = gas_root / "projects"
    build_script = PROJECT_ROOT / "scripts" / "deployment" / "google" / "build.js"
    
    if not projects_dir.exists():
        print(f"❌ GAS projects directory not found: {projects_dir}")
        return 1
    
    if not build_script.exists():
        print(f"❌ Build script not found: {build_script}")
        return 1
    
    projects = sorted([d for d in projects_dir.iterdir() if d.is_dir() and not d.name.startswith('.')])
    
    if not projects:
        print("⚠️  No GAS projects found")
        return 1
    
    print(f"🔍 Compiling {len(projects)} GAS projects with esbuild...")
    
    errors: List[str] = []
    
    for project_dir in projects:
        project_name = project_dir.name
        _validate_gas_project_json(project_dir, project_name, errors)
    
    if errors:
        _print_gas_errors(errors, "before build")
        return 1
    
    for project_dir in projects:
        project_name = project_dir.name
        _build_gas_project(project_dir, project_name, build_script, gas_root, errors)
    
    if errors:
        _print_gas_errors(errors, "")
        return 1
    
    print("✅ All GAS projects compiled successfully")
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
        path: Path to compile (e.g., "backend", "aws/lambda/functions", "google-apps-scripts")
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    if "backend" in path.lower():
        return compile_backend()
    elif "lambda" in path.lower():
        return compile_lambda()
    elif "gas" in path.lower() or "google" in path.lower():
        return compile_gas()
    else:
        print(f"⚠️  Unknown path: {path}")
        print("   Supported paths: backend, aws/lambda/functions, google-apps-scripts")
        return 1


# ============================================================================
# Entry Point (for direct script execution)
# ============================================================================

if __name__ == "__main__":
    ensure_cli_paths_setup()
    
    check_types = "--types" in sys.argv
    
    target_path = "all"
    if "--backend" in sys.argv:
        target_path = "backend"
    elif "--lambda" in sys.argv:
        target_path = "lambda"
    
    try:
        results = run_all_checks(check_types=check_types, target_path=target_path)
    except RuntimeError as e:
        Console().print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    
    Console().print("\n")
    
    sections, summary = build_display_data(
        syntax_errors=results.syntax_errors,  # type: ignore[arg-type]
        import_errors=results.import_errors,  # type: ignore[arg-type]
        unused_imports=results.unused_imports,  # type: ignore[arg-type]
        type_errors=results.type_errors,  # type: ignore[arg-type]
        required_defaults=results.required_defaults,  # type: ignore[arg-type]
        total_files=results.total_files,
        check_types=results.check_types
    )
    display(sections, summary)
    
    sys.exit(0 if summary.total_errors == 0 else 1)
