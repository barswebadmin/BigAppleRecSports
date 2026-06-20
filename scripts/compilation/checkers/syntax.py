"""Syntax checking using ruff."""

import subprocess
import sys
from pathlib import Path

from ..repo_path_resolvers import get_relative_path
from ._checkers_common import create_error, parse_json_output, run_subprocess


def _run_ruff(file_path: Path, repo_root: Path, timeout: int = 30) -> tuple[subprocess.CompletedProcess | None, list[dict]]:
    """Run ruff check and return result or errors."""
    rel_path = get_relative_path(file_path, repo_root / "src")
    cmd = [sys.executable, "-m", "ruff", "check", str(file_path), "--output-format=json", "--quiet"]
    
    result, errors = run_subprocess(cmd, repo_root, rel_path, timeout=timeout)
    if errors:
        # Handle FileNotFoundError specifically for ruff
        if any("Command not found" in err.get("message", "") for err in errors):
            return None, [create_error(rel_path, "ERROR", "Syntax checker not found - install with: uv tool install ruff")]
        return None, errors
    return result, []


def _parse_ruff_output(output: str, rel_path: str) -> list[dict]:
    """Parse ruff JSON output into error dictionaries."""
    errors_data, parse_errors = parse_json_output(output, rel_path, "ERROR")
    if parse_errors:
        return parse_errors
    if errors_data is None:
        return [create_error(rel_path, "ERROR", "Failed to parse syntax check output")]
    
    # Ruff returns a list of error dictionaries
    if not isinstance(errors_data, list):
        return [create_error(rel_path, "ERROR", "Invalid syntax check output format")]
    
    syntax_errors = []
    for error in errors_data:
        if not isinstance(error, dict):
            continue
        code = error.get("code", "")
        if code in ["E999", "F821"] or code.startswith("E"):
            location = error.get("location", {})
            row = location.get("row", 0) if isinstance(location, dict) else 0
            syntax_errors.append(create_error(
                rel_path,
                code,
                error.get("message", ""),
                row
            ))
    
    return syntax_errors


def check_syntax(file_path: Path, repo_root: Path) -> tuple[bool, list[dict]]:
    """Check Python file syntax (uses ruff internally).
    
    Args:
        file_path: Path to Python file to check
        repo_root: Repository root directory
        
    Returns:
        tuple of (success, list_of_errors)
    """
    result, errors = _run_ruff(file_path, repo_root)
    if errors or result is None:
        return False, errors or []
    
    if not result.stdout:
        return True, []

    syntax_errors = _parse_ruff_output(result.stdout, get_relative_path(file_path, repo_root / "src"))
    return len(syntax_errors) == 0, syntax_errors
