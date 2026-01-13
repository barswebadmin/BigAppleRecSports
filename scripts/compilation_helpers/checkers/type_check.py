"""Type checking using pyright."""

import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

from scripts.compilation_helpers.repo_path_resolvers import get_relative_path
from scripts.compilation_helpers.checkers._checkers_common import create_error, parse_json_output, run_subprocess


def _check_tool_available(cmd: List[str], timeout: int = 5) -> bool:
    """Check if a tool is available."""
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=timeout)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _run_pyright(cmd: List[str], repo_root: Path, rel_path: str, timeout: int = 60) -> Tuple[subprocess.CompletedProcess | None, List[dict]]:
    """Run pyright and return result or errors."""
    return run_subprocess(cmd, repo_root, rel_path, timeout=timeout)


def _parse_pyright_output(output: str, rel_path: str) -> List[dict]:
    """Parse pyright JSON output."""
    data, parse_errors = parse_json_output(output, rel_path, "ERROR")
    if parse_errors:
        return parse_errors
    if data is None:
        return [create_error(rel_path, "ERROR", "Failed to parse type check output")]
    
    type_errors = []
    for diag in data.get("generalDiagnostics", []):
        severity = diag.get("severity", "").lower()
        rule = diag.get("rule", "")
        
        if rule == "reportMissingImports" or severity != "error":
            continue
        
        line_num = diag.get("range", {}).get("start", {}).get("line", 0) + 1
        type_errors.append(create_error(rel_path, rule, diag.get("message", ""), line_num))
    
    return type_errors


def _find_pyright_command() -> str | None:
    """Find available pyright command."""
    for cmd in ["pyright", "pyright-langserver"]:
        if _check_tool_available([cmd, "--version"]):
            return cmd
    return None


def check_types(file_path: Path, repo_root: Path) -> Tuple[bool, List[dict]]:
    """Check types using pyright.
    
    Args:
        file_path: Path to Python file to check
        repo_root: Repository root directory
        
    Returns:
        Tuple of (success, list_of_errors)
    """
    rel_path = get_relative_path(file_path, repo_root / "src")
    
    pyright_cmd = _find_pyright_command()
    if not pyright_cmd:
        return True, []
    
    cmd = [pyright_cmd, str(file_path), "--outputjson", "--pythonpath", str(repo_root / "src")]
    result, errors = _run_pyright(cmd, repo_root, rel_path)
    
    if result is None:
        return False, errors
    if not result.stdout:
        return True, []
    
    type_errors = _parse_pyright_output(result.stdout, rel_path)
    return len(type_errors) == 0, type_errors
