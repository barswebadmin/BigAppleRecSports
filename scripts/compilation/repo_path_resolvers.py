"""Repository path resolution utilities for compilation checks."""

import sys
from pathlib import Path
from typing import List

import sys
from pathlib import Path

# Add shared utilities to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared_utilities"))
from paths import get_repo_root


def find_repo_root() -> Path:
    """Find the repository root directory by looking for .git."""
    return get_repo_root()


def find_all_python_files(repo_root: Path) -> List[Path]:
    """Find all Python files in backend/ and aws/lambda/functions/.

    Args:
        repo_root: Repository root directory

    Returns:
        List of Python file paths
    """
    python_files: List[Path] = []

    for subpath in ("backend", "aws/lambda/functions"):
        candidate = repo_root / subpath
        if candidate.exists():
            python_files.extend(candidate.rglob("*.py"))
    
    # Filter out __pycache__ and test files if needed
    filtered = [
        f for f in python_files
        if "__pycache__" not in str(f)
        and not f.name.startswith(".")
    ]
    
    return sorted(filtered)


def get_relative_path(file_path: Path, base_path: Path) -> str:
    """Get relative path from base_path to file_path as a string.
    
    Args:
        file_path: Absolute or relative file path
        base_path: Base directory to compute relative path from
        
    Returns:
        Relative path string (e.g., "backend/modules/auth.py")
    """
    try:
        return str(file_path.relative_to(base_path))
    except ValueError:
        # If file_path is not relative to base_path, return the file name
        return file_path.name


def path_to_module(file_path: Path, src_root: Path) -> str:
    """Convert a file path to a Python module name.
    
    Args:
        file_path: Path to Python file
        src_root: Root directory (backend/ or aws/lambda/functions/)

    Returns:
        Module name (e.g., "backend.modules.auth" or "ShopifyProductUpdates.main")
    """
    try:
        rel_path = file_path.relative_to(src_root)
        # Remove .py extension and convert / to .
        module_name = str(rel_path.with_suffix("")).replace("/", ".")
        # Remove __init__ suffix if present
        if module_name.endswith(".__init__"):
            module_name = module_name[:-9]
        elif module_name == "__init__":
            # For __init__.py at root, use the directory name
            parent = src_root.name
            module_name = parent
        return module_name
    except ValueError:
        # If not relative to src_root, try to infer from path
        parts = file_path.parts
        if "backend" in parts:
            idx = parts.index("backend")
            module_parts = parts[idx + 1:]
        elif "lambda" in parts and "functions" in parts:
            idx = parts.index("lambda")
            module_parts = parts[idx:]
        else:
            return file_path.stem
        
        module_name = ".".join(p.stem if p.suffix == ".py" else p.name for p in [Path(p) for p in module_parts])
        if module_name.endswith(".__init__"):
            module_name = module_name[:-9]
        return module_name
