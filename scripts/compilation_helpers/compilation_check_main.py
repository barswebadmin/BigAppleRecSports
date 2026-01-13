#!/usr/bin/env python3
"""Module checking orchestration - coordinates all checkers."""

import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from scripts.compilation_helpers.repo_path_resolvers import (
    find_all_python_files,
    find_repo_root,
    get_relative_path,
)
# Import common utilities from checkers (including error model) - must be before ModuleCheckResult
from scripts.compilation_helpers.checkers._checkers_common import (  # noqa: E402
    CheckError,
    create_error,
    ensure_path_in_sys_path,
    ensure_src_in_path,
    to_check_errors,
)

# Display models (renderers owns these)
from scripts.compilation_helpers.display.renderers import (
    DisplaySection,
    DisplaySummary,
    build_display_data,
    display,
)


# ============================================================================
# Data Models (owned by orchestration)
# ============================================================================

class ModuleCheckResult:
    """Represents the result of checking a single module.
    
    Attributes:
        syntax_errors: List of syntax errors
        import_errors: List of import errors (circular imports, missing modules, etc.)
        unused_imports: List of unused import warnings
        type_errors: List of type checking errors (optional, only if --types flag used)
        required_defaults: List of required field/parameter default violations
    """
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




def ensure_cli_paths_setup() -> None:
    """Ensure repo root and Python directories are in sys.path for CLI execution.
    
    This is called when running as a script to ensure imports work correctly.
    This is CLI-specific setup and should not be moved to _checkers_common
    because checkers receive paths as parameters and don't need to discover them.
    """
    repo_root = find_repo_root()
    ensure_path_in_sys_path(repo_root)
    
    # Add backend/, lambda/functions/, and bars_cli/ to sys.path
    for python_dir in ["backend", "lambda/functions", "bars_cli"]:
        python_path = repo_root / python_dir
        if python_path.exists():
            ensure_path_in_sys_path(python_path)




# Import checkers (create_error is now in _checkers_common)
from scripts.compilation_helpers.checkers.circular_imports import check_circular_imports  # noqa: E402
from scripts.compilation_helpers.checkers.required_defaults import check_required_defaults  # noqa: E402
from scripts.compilation_helpers.checkers.syntax import check_syntax  # noqa: E402
from scripts.compilation_helpers.checkers.type_check import check_types as run_type_check  # noqa: E402
from scripts.compilation_helpers.checkers.unused_imports import get_unused_imports  # noqa: E402


# ============================================================================
# Result Aggregation
# ============================================================================

def _aggregate_result(
    result: ModuleCheckResult,
    all_syntax_errors: Dict[str, List[CheckError]],
    all_import_errors: Dict[str, List[CheckError]],
    all_unused_imports: Dict[str, List[CheckError]],
    all_type_errors: Dict[str, List[CheckError]],
    all_required_defaults: Dict[str, List[CheckError]],
    module_name: str
) -> None:
    """Aggregate a single module's check results into the overall results.
    
    Args:
        result: ModuleCheckResult from checking a single file
        all_syntax_errors: Dictionary to accumulate syntax errors
        all_import_errors: Dictionary to accumulate import errors
        all_unused_imports: Dictionary to accumulate unused imports
        all_type_errors: Dictionary to accumulate type errors
        all_required_defaults: Dictionary to accumulate required defaults
        module_name: Name of the module being checked
    """
    # Map result attributes to their corresponding aggregation dictionaries
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
    """Check a single module for syntax, import, and unused import errors.
    
    Args:
        module_path: Path to Python file to check
        repo_root: Repository root directory
        src_root: Root of Python directory (backend/, lambda/functions/, or bars_cli/)
        debug_messages: Optional list to append debug messages to
        debug_lock: Optional lock for thread-safe access to debug_messages
        check_types: If True, also run type checking (default: False)
        
    Returns:
        Tuple of (module_name, ModuleCheckResult)
    """
    module_name = get_relative_path(module_path, src_root)
    
    # Run syntax check (always runs)
    _, syntax_error_dicts = check_syntax(module_path, repo_root)
    syntax_errors = to_check_errors(syntax_error_dicts)
    
    # Run import check (always runs, determines if module can be imported)
    import_success, import_error_dicts = check_circular_imports(module_path, src_root, debug_messages, debug_lock)
    import_errors = to_check_errors(import_error_dicts)
    
    # Run checks that require successful import
    unused_imports = []
    required_defaults = []
    if import_success:
        unused_import_dicts = get_unused_imports(module_path, src_root)
        unused_imports = to_check_errors(unused_import_dicts)
    
        required_default_dicts = check_required_defaults(module_path, src_root)
        required_defaults = to_check_errors(required_default_dicts)
    
    # Run type check (optional, can be slow)
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
    


def run_all_checks(
    check_types: bool = False,
    max_workers: int = 8,
    target_path: str = "all"
) -> CompilationCheckResults:
    """Run all compilation checks on Python files in backend/, lambda/functions/, or bars_cli/.
    
    Args:
        check_types: If True, also run type checking with pyright (default: False)
        max_workers: Maximum number of concurrent workers (default: 8)
        target_path: Target path to check - "backend", "lambda", "bars_cli", or "all" (default: "all")
        
    Returns:
        CompilationCheckResults with aggregated error dictionaries
        
    Raises:
        RuntimeError: If no Python directories found
    """
    console = Console()
    repo_root = find_repo_root()
    
    # Determine which directories to check
    python_dirs = []
    if target_path == "all":
        for dir_name in ["backend", "lambda/functions", "bars_cli"]:
            dir_path = repo_root / dir_name
            if dir_path.exists():
                python_dirs.append(dir_path)
    elif target_path == "backend":
        python_dirs = [repo_root / "backend"] if (repo_root / "backend").exists() else []
    elif target_path == "lambda":
        python_dirs = [repo_root / "lambda" / "functions"] if (repo_root / "lambda" / "functions").exists() else []
    elif target_path == "bars_cli":
        python_dirs = [repo_root / "bars_cli"] if (repo_root / "bars_cli").exists() else []
    else:
        raise RuntimeError(f"Unknown target_path: {target_path}. Must be 'backend', 'lambda', 'bars_cli', or 'all'")
    
    if not python_dirs:
        raise RuntimeError(f"No Python directories found for target_path={target_path}")
    
    files = find_all_python_files(repo_root)
    if not files:
        return CompilationCheckResults({}, {}, {}, {}, {}, 0, check_types)
    
    # Filter files based on target_path
    if target_path != "all":
        filtered_files = []
        for file_path in files:
            if target_path == "backend" and "backend" in file_path.parts:
                filtered_files.append(file_path)
            elif target_path == "lambda" and "lambda" in file_path.parts and "functions" in file_path.parts:
                filtered_files.append(file_path)
            elif target_path == "bars_cli" and "bars_cli" in file_path.parts:
                filtered_files.append(file_path)
        files = filtered_files
    
    if not files:
        return CompilationCheckResults({}, {}, {}, {}, {}, 0, check_types)
    
    total_files = len(files)
    
    # Initialize aggregated results
    all_syntax_errors: Dict[str, List[CheckError]] = {}
    all_import_errors: Dict[str, List[CheckError]] = {}
    all_unused_imports: Dict[str, List[CheckError]] = {}
    all_type_errors: Dict[str, List[CheckError]] = {}
    all_required_defaults: Dict[str, List[CheckError]] = {}
    debug_messages: List[str] = []
    debug_lock = threading.Lock()
    
    def get_src_root_for_file(file_path: Path) -> Path:
        """Determine the src_root (Python directory) for a given file."""
        # Resolve to absolute path first
        abs_path = file_path.resolve() if not file_path.is_absolute() else file_path
        abs_repo_root = repo_root.resolve()
        
        try:
            rel_path = abs_path.relative_to(abs_repo_root)
            parts = rel_path.parts
        except ValueError:
            # If not relative to repo_root, try to find the Python directory in the path
            parts = abs_path.parts
        
        if "backend" in parts:
            idx = parts.index("backend")
            return abs_repo_root / "backend"
        elif "lambda" in parts and "functions" in parts:
            return abs_repo_root / "lambda" / "functions"
        elif "bars_cli" in parts:
            return abs_repo_root / "bars_cli"
        else:
            return abs_repo_root
    
    # Run checks with progress
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
                        get_src_root_for_file(file_path),
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
                    except Exception as e:
                        file_path = future_to_file[future]
                        src_root = get_src_root_for_file(file_path)
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
# Entry Point
# ============================================================================

if __name__ == "__main__":
    # Ensure paths are set up for imports
    ensure_cli_paths_setup()
    
    # Simple argument parsing for make/git hooks (no argparse needed)
    check_types = "--types" in sys.argv
    
    # Determine target_path from args
    target_path = "all"
    if "--backend" in sys.argv:
        target_path = "backend"
    elif "--lambda" in sys.argv:
        target_path = "lambda"
    elif "--bars-cli" in sys.argv or "--bars_cli" in sys.argv:
        target_path = "bars_cli"
    
    # Run checks
    try:
        results = run_all_checks(check_types=check_types, target_path=target_path)
    except RuntimeError as e:
        Console().print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    
    Console().print("\n")
    
    # Build display data and render (display logic is in renderers)
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
