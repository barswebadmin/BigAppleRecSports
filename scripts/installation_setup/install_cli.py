#!/usr/bin/env python3
"""
Install CLI tool using UV.

Creates bars_cli/.venv and installs the CLI package in editable mode.
The CLI entry point (bars) will be available via symlink in ~/.local/bin.
"""
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class InstallResult:
    """Result of an installation operation."""
    name: str
    ok: bool
    seconds: float
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def install_cli(skip_shared_utilities: bool = False) -> InstallResult:
    """Install CLI using UV.
    
    Args:
        skip_shared_utilities: If True, skip installing shared_utilities (assumes already installed)
    """
    started = time.time()
    notes = []
    warnings = []
    
    repo_root = Path(__file__).parent.parent.parent
    cli_dir = repo_root / "bars_cli"
    venv_dir = cli_dir / ".venv"
    shared_utilities_dir = repo_root / "shared_utilities"
    
    if not cli_dir.exists():
        return InstallResult(
            "cli",
            False,
            time.time() - started,
            warnings=["bars_cli directory not found"]
        )
    
    print("📦 Installing CLI...")
    
    # Create venv if it doesn't exist
    if not venv_dir.exists():
        print("  Creating virtual environment...")
        result = subprocess.run(
            ["uv", "venv"],
            cwd=cli_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return InstallResult(
                "cli",
                False,
                time.time() - started,
                warnings=[f"Failed to create venv: {result.stderr}"]
            )
        notes.append("Created .venv")
    
    # Install shared_utilities first (editable mode) unless already installed
    if not skip_shared_utilities and shared_utilities_dir.exists():
        print("  Installing shared_utilities...")
        result = subprocess.run(
            ["uv", "pip", "install", "-e", str(shared_utilities_dir)],
            cwd=cli_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            warnings.append(f"Failed to install shared_utilities: {result.stderr}")
        else:
            notes.append("Installed shared_utilities (editable)")
    elif skip_shared_utilities:
        notes.append("Skipped shared_utilities (already installed)")
    
    # Install package in editable mode
    print("  Installing CLI package...")
    result = subprocess.run(
        ["uv", "pip", "install", "-e", "."],
        cwd=cli_dir,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        return InstallResult(
            "cli",
            False,
            time.time() - started,
            warnings=[f"Failed to install CLI: {result.stderr}"]
        )
    
    notes.append("Installed CLI in editable mode")
    
    # Create symlink in ~/.local/bin for easy access
    local_bin = Path.home() / ".local" / "bin"
    bars_symlink = local_bin / "bars"
    bars_executable = venv_dir / "bin" / "bars"
    
    if bars_executable.exists():
        local_bin.mkdir(parents=True, exist_ok=True)
        
        # Remove old symlink if it exists
        if bars_symlink.exists() or bars_symlink.is_symlink():
            bars_symlink.unlink()
        
        # Create new symlink
        bars_symlink.symlink_to(bars_executable)
        notes.append(f"Created symlink: ~/.local/bin/bars -> {bars_executable}")
        notes.append("Ensure ~/.local/bin is in your PATH")
    else:
        warnings.append("bars executable not found after installation")
    
    return InstallResult(
        "cli",
        True,
        time.time() - started,
        notes=notes,
        warnings=warnings
    )


def main() -> int:
    """Run CLI installation."""
    result = install_cli()
    
    status = "✅" if result.ok else "❌"
    print(f"\n{status} {result.name} ({result.seconds:.1f}s)")
    
    for note in result.notes:
        print(f"  - {note}")
    for warning in result.warnings:
        print(f"  - ⚠️  {warning}")
    
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
