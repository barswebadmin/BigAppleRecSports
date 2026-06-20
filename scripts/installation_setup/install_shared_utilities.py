#!/usr/bin/env python3
"""
Install shared_utilities package in development mode.

This is primarily for IDE/workspace setup where shared_utilities
needs its own .venv for proper import resolution.

In production, shared_utilities is installed as a dependency of
backend via `uv sync`.
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


def install_shared_utilities() -> InstallResult:
    """Install shared_utilities in development mode."""
    started = time.time()
    notes = []
    warnings = []
    
    repo_root = Path(__file__).parent.parent.parent
    shared_utils_dir = repo_root / "shared_utilities"
    venv_dir = shared_utils_dir / ".venv"
    
    if not shared_utils_dir.exists():
        return InstallResult(
            "shared_utilities",
            False,
            time.time() - started,
            warnings=["shared_utilities directory not found"]
        )
    
    print("📦 Installing shared_utilities...")
    
    # Create venv if it doesn't exist
    if not venv_dir.exists():
        print("  Creating virtual environment...")
        result = subprocess.run(
            ["uv", "venv"],
            cwd=shared_utils_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return InstallResult(
                "shared_utilities",
                False,
                time.time() - started,
                warnings=[f"Failed to create venv: {result.stderr}"]
            )
        notes.append("Created .venv")
    
    # Install package in editable mode
    print("  Installing package...")
    result = subprocess.run(
        ["uv", "sync"],
        cwd=shared_utils_dir,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        return InstallResult(
            "shared_utilities",
            False,
            time.time() - started,
            warnings=[f"Failed to install: {result.stderr}"]
        )
    
    notes.append("Installed in editable mode")
    
    return InstallResult(
        "shared_utilities",
        True,
        time.time() - started,
        notes=notes,
        warnings=warnings
    )


def main() -> int:
    """Run shared_utilities installation."""
    result = install_shared_utilities()
    
    status = "✅" if result.ok else "❌"
    print(f"\n{status} {result.name} ({result.seconds:.1f}s)")
    
    for note in result.notes:
        print(f"  - {note}")
    for warning in result.warnings:
        print(f"  - ⚠️  {warning}")
    
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
