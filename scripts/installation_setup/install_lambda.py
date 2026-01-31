#!/usr/bin/env python3
"""
Lambda functions installation script.

Installs lambda dependencies into lambda/.venv using UV.
"""
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Add shared utilities to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared_utilities"))
from paths import get_repo_root

REPO_ROOT = get_repo_root()


def _run(
    cmd: list[str],
    *,
    cwd: Optional[Path] = None,
    timeout: int = 1800,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=capture,
        check=check,
        timeout=timeout,
    )


@dataclass
class InstallResult:
    name: str
    ok: bool
    seconds: float
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def install_lambda() -> InstallResult:
    """Install Lambda function dependencies using UV."""
    started = time.time()
    lambda_dir = REPO_ROOT / "lambda"
    venv_dir = lambda_dir / ".venv"
    pyproject_toml = lambda_dir / "pyproject.toml"

    notes: list[str] = []
    warnings: list[str] = []

    if not pyproject_toml.exists():
        warnings.append("lambda/pyproject.toml not found; skipped")
        return InstallResult("lambda", True, time.time() - started, notes=notes, warnings=warnings)

    # Check if uv is installed
    try:
        _run(["uv", "--version"], capture=True, timeout=10, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        warnings.append("uv not installed; skipping lambda installation")
        warnings.append("install uv: https://docs.astral.sh/uv/getting-started/installation/")
        return InstallResult("lambda", False, time.time() - started, notes=notes, warnings=warnings)

    try:
        # Create venv if it doesn't exist
        if not venv_dir.exists():
            _run(["uv", "venv"], cwd=lambda_dir, timeout=300, check=True)
            notes.append(f"created {venv_dir.relative_to(REPO_ROOT)}")

        # Install dependencies using UV
        _run(["uv", "pip", "install", "-e", "."], cwd=lambda_dir, timeout=1800, check=True)
        notes.append("installed lambda dependencies")

        # Install dev dependencies
        _run(["uv", "pip", "install", "-e", ".[dev]"], cwd=lambda_dir, timeout=1800, check=True)
        notes.append("installed lambda dev dependencies")

    except subprocess.CalledProcessError as e:
        return InstallResult("lambda", False, time.time() - started, notes=notes, warnings=[str(e)])
    except subprocess.TimeoutExpired:
        return InstallResult("lambda", False, time.time() - started, notes=notes, warnings=["Installation timed out"])

    return InstallResult("lambda", True, time.time() - started, notes=notes, warnings=warnings)


if __name__ == "__main__":
    result = install_lambda()
    status = "✅" if result.ok else "❌"
    print(f"{status} {result.name} ({result.seconds:.1f}s)")
    for n in result.notes:
        print(f"  - {n}")
    for w in result.warnings:
        print(f"  - ⚠️  {w}")
    sys.exit(0 if result.ok else 1)
