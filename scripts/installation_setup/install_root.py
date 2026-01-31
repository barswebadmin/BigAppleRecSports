#!/usr/bin/env python3
"""
Install root-level monorepo development tools.

This installs shared development dependencies (ruff, pytest, mypy, etc.)
in a root-level .venv that can be used for monorepo-wide operations like:
- Running tests across all projects
- Linting the entire codebase
- Generating combined coverage reports
- Pre-commit hooks

Individual projects still have their own .venvs for deployment isolation.
"""
import subprocess
import sys
import time
from pathlib import Path


class InstallResult:
    """Result of an installation operation."""
    def __init__(self, name: str, ok: bool, seconds: float, notes: list[str] = None, warnings: list[str] = None):
        self.name = name
        self.ok = ok
        self.seconds = seconds
        self.notes = notes or []
        self.warnings = warnings or []


def install_root() -> InstallResult:
    """Install root-level monorepo development tools."""
    started = time.time()
    notes = []
    warnings = []
    
    repo_root = Path(__file__).parent.parent.parent
    venv_dir = repo_root / ".venv"
    pyproject_file = repo_root / "pyproject.toml"
    
    if not pyproject_file.exists():
        return InstallResult(
            "root",
            False,
            time.time() - started,
            warnings=["pyproject.toml not found at repo root"]
        )
    
    print("📦 Installing root monorepo development tools...")
    
    # Create venv if it doesn't exist
    if not venv_dir.exists():
        print("  Creating virtual environment...")
        result = subprocess.run(
            ["uv", "venv"],
            cwd=repo_root,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return InstallResult(
                "root",
                False,
                time.time() - started,
                warnings=[f"Failed to create venv: {result.stderr}"]
            )
        notes.append("Created .venv")
    
    # Install dev dependencies
    print("  Installing dev dependencies (ruff, pytest, mypy, etc.)...")
    result = subprocess.run(
        ["uv", "pip", "install", "-e", ".[dev]"],
        cwd=repo_root,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        return InstallResult(
            "root",
            False,
            time.time() - started,
            warnings=[f"Failed to install dev dependencies: {result.stderr}"]
        )
    
    notes.append("Installed dev dependencies")
    notes.append("Tools available: ruff, pytest, mypy, pre-commit")
    
    # Verify key tools are installed
    tools_to_verify = ["ruff", "pytest", "mypy"]
    python_bin = venv_dir / "bin" / "python"
    
    for tool in tools_to_verify:
        result = subprocess.run(
            [str(python_bin), "-m", tool, "--version"],
            cwd=repo_root,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            warnings.append(f"{tool} verification failed")
    
    return InstallResult(
        "root",
        True,
        time.time() - started,
        notes=notes,
        warnings=warnings
    )


def main() -> int:
    """Run root installation."""
    result = install_root()
    
    status = "✅" if result.ok else "❌"
    print(f"\n{status} {result.name} ({result.seconds:.1f}s)")
    
    for note in result.notes:
        print(f"  - {note}")
    for warning in result.warnings:
        print(f"  - ⚠️  {warning}")
    
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
