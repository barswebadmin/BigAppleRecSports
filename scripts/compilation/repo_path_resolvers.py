"""Repository path resolution utilities for compilation checks."""

from pathlib import Path
from typing import List


def find_repo_root() -> Path:
    """Find the repository root directory by looking for .git."""
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    raise RuntimeError("Could not find repository root (.git)")


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

    filtered = [
        f
        for f in python_files
        if "__pycache__" not in str(f) and not f.name.startswith(".")
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
        return file_path.name


def path_to_module(file_path: Path, src_root: Path) -> str:
    """Convert a file path to a Python module name.

    Args:
        file_path: Path to Python file
        src_root: Root directory (backend/ or aws/lambda/functions/)

    Returns:
        Module name (e.g., "backend.modules.auth" or "AwsRouter.main")
    """
    try:
        rel_path = file_path.relative_to(src_root)
        module_name = str(rel_path.with_suffix("")).replace("/", ".")
        if module_name.endswith(".__init__"):
            module_name = module_name[:-9]
        elif module_name == "__init__":
            parent = src_root.name
            module_name = parent
        return module_name
    except ValueError:
        parts = file_path.parts
        if "backend" in parts:
            idx = parts.index("backend")
            module_parts = parts[idx + 1 :]
        elif "aws" in parts and "lambda" in parts and "functions" in parts:
            idx = parts.index("functions")
            module_parts = parts[idx + 1 :]
        else:
            return file_path.stem

        module_name = ".".join(p.stem if p.suffix == ".py" else p.name for p in [Path(p) for p in module_parts])
        if module_name.endswith(".__init__"):
            module_name = module_name[:-9]
        return module_name
