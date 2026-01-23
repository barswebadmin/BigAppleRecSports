"""Common utilities shared by all checker modules."""

import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# Error Model (shared by all checkers)
# ============================================================================

class CheckError:
    """Represents a compilation check error.
    
    Attributes:
        file: Relative path to the file
        line: Line number (default: 0)
        code: Error code (e.g., "F821", "E402")
        message: Error message
        import_path: Optional import path (for circular imports)
    """
    def __init__(
        self,
        file: str,
        code: str,
        message: str,
        line: int = 0,
        import_path: Optional[str] = None
    ):
        self.file = file
        self.line = line
        self.code = code
        self.message = message
        self.import_path = import_path


def to_check_errors(error_dicts: List[dict[str, Any]]) -> List[CheckError]:
    """Convert error dictionaries to CheckError model instances.
    
    Safety mechanisms:
    1. Direct dict access for required fields raises KeyError on typos (fails fast)
    2. Runtime validation ensures correct structure
    
    Args:
        error_dicts: List of error dicts with required keys: file, code, message
                    Optional keys: line (defaults to 0), import_path
        
    Returns:
        List of CheckError instances
        
    Raises:
        KeyError: If required keys (file, code, message) are missing - catches typos immediately
    """
    return [
        CheckError(
            file=err["file"],
            code=err["code"],
            message=err["message"],
            line=err.get("line", 0),  # Optional, defaults to 0
            import_path=err.get("import_path")  # Optional
        )
        for err in error_dicts
    ]


# ============================================================================
# Common Utilities
# ============================================================================


def create_error(file: str, code: str, message: str, line: int = 0, import_path: Optional[str] = None) -> dict:
    """Create a standardized error dictionary.
    
    Args:
        file: Relative path to the file
        code: Error code (e.g., "CIRCULAR", "F401", "E999")
        message: Error message
        line: Line number (default: 0)
        import_path: Optional import path for circular imports
        
        Returns:
        Error dictionary with keys: file, code, message, line (optional), import_path (optional)
    """
    error: dict = {"file": file, "code": code, "message": message, "line": line}
    if import_path:
        error["import_path"] = import_path
    return error


def parse_file_ast(file_path: Path) -> Optional[ast.AST]:
    """Parse a Python file and return its AST.
    
    Args:
        file_path: Path to Python file
        
    Returns:
        AST node or None if parsing fails
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return ast.parse(f.read(), filename=str(file_path))
    except Exception:
        return None


def run_subprocess(
    cmd: List[str],
    cwd: Path,
    rel_path: str,
    timeout: int = 30,
    text: bool = True
) -> Tuple[subprocess.CompletedProcess | None, List[dict]]:
    """Run a subprocess command with timeout and error handling.
    
    Args:
        cmd: Command to run
        cwd: Working directory for the command
        rel_path: Relative path for error messages
        timeout: Timeout in seconds (default: 30)
        text: If True, capture output as text (default: True)
        
    Returns:
        Tuple of (result, errors) where result is None if error occurred
    """
    try:
        result = subprocess.run(cmd, capture_output=True, text=text, cwd=str(cwd), timeout=timeout)
        return result, []
    except subprocess.TimeoutExpired:
        return None, [create_error(rel_path, "TIMEOUT", f"Command timed out: {' '.join(cmd)}")]
    except FileNotFoundError:
        return None, [create_error(rel_path, "ERROR", f"Command not found: {cmd[0]}")]
    except Exception as e:
        return None, [create_error(rel_path, "ERROR", f"Error running command: {e}")]


def parse_json_output(output: str, rel_path: str, error_code: str = "ERROR") -> Tuple[Optional[Dict[str, Any]], List[dict]]:
    """Parse JSON output with error handling.
    
    Args:
        output: JSON string to parse
        rel_path: Relative path for error messages
        error_code: Error code to use if parsing fails (default: "ERROR")
        
    Returns:
        Tuple of (parsed_data, errors) where parsed_data is None if parsing fails
    """
    try:
        return json.loads(output), []
    except json.JSONDecodeError:
        return None, [create_error(rel_path, error_code, "Failed to parse JSON output")]


def ensure_path_in_sys_path(path: Path) -> None:
    """Ensure a path is in sys.path for imports.
    
    Args:
        path: Path to add to sys.path
    """
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def ensure_src_in_path(src_root: Path) -> None:
    """Ensure src_root is in sys.path for imports.
    
    Args:
        src_root: Root of src/ directory
    """
    ensure_path_in_sys_path(src_root)
