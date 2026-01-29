#!/usr/bin/env python3
"""
Backend installation script.

Installs backend dependencies into backend/.venv from backend/requirements.txt.
"""
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]


def _pip_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    env.setdefault("PIP_NO_INPUT", "1")
    env.setdefault("PIP_PROGRESS_BAR", "off")
    return env


def _norm_pkg_name(name: str) -> str:
    return re.sub(r"[-_]+", "-", name.strip().lower())


def _run(
    cmd: list[str],
    *,
    cwd: Optional[Path] = None,
    env: Optional[dict[str, str]] = None,
    timeout: int = 1800,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        capture_output=capture,
        check=check,
        timeout=timeout,
    )


def _parse_requirements(requirements_path: Path, _visited: Optional[set[Path]] = None) -> set[str]:
    visited = _visited or set()
    req_path = requirements_path.resolve()
    if req_path in visited:
        return set()
    visited.add(req_path)

    out: set[str] = set()
    if not req_path.exists():
        return out

    for raw in req_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-r "):
            rel = line.split(maxsplit=1)[1].strip()
            include_path = (req_path.parent / rel).resolve()
            out |= _parse_requirements(include_path, visited)
            continue
        if line.startswith("-"):
            continue
        name = re.split(r"[<>=!~\s;\[]", line, maxsplit=1)[0]
        if name:
            out.add(_norm_pkg_name(name))
    return out


def _pip_list_not_required(
    python: str,
    *,
    extra_args: Optional[list[str]] = None,
    timeout: int = 60,
) -> set[str]:
    args = [python, "-m", "pip", "list", "--format=json", "--not-required"]
    if extra_args:
        args.extend(extra_args)
    try:
        res = _run(args, cwd=REPO_ROOT, capture=True, timeout=timeout, check=True)
        pkgs = json.loads(res.stdout or "[]")
        return {_norm_pkg_name(p["name"]) for p in pkgs if p.get("name")}
    except Exception:
        return set()


def _pip_list_all(
    python: str,
    *,
    extra_args: Optional[list[str]] = None,
    timeout: int = 60,
) -> set[str]:
    args = [python, "-m", "pip", "list", "--format=json"]
    if extra_args:
        args.extend(extra_args)
    res = _run(args, cwd=REPO_ROOT, capture=True, timeout=timeout, check=True)
    pkgs = json.loads(res.stdout or "[]")
    return {_norm_pkg_name(p["name"]) for p in pkgs if p.get("name")}


def _python_venv_python(venv_dir: Path) -> str:
    return str(venv_dir / "bin" / "python")


@dataclass
class InstallResult:
    name: str
    ok: bool
    seconds: float
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def install_backend() -> InstallResult:
    """Install backend dependencies into backend/.venv."""
    started = time.time()
    backend_dir = REPO_ROOT / "backend"
    venv_dir = backend_dir / ".venv"
    requirements = backend_dir / "requirements.txt"
    requirements_dev = backend_dir / "requirements-dev.txt"
    pyproject_toml = REPO_ROOT / "pyproject.toml"

    notes: list[str] = []
    warnings: list[str] = []

    if not venv_dir.exists():
        _run([sys.executable, "-m", "venv", str(venv_dir)], cwd=REPO_ROOT, timeout=300, check=True)
        notes.append(f"created {venv_dir}")

    # Temporarily rename pyproject.toml to prevent pip from auto-discovering it
    pyproject_backup = None
    if pyproject_toml.exists():
        pyproject_backup = REPO_ROOT / "pyproject.toml.backup"
        pyproject_toml.rename(pyproject_backup)

    try:
        python = _python_venv_python(venv_dir)
        pip_env = _pip_env()
        _run([python, "-m", "pip", "install", "-q", "--upgrade", "pip"], cwd=backend_dir, env=pip_env, timeout=300, check=True)
        _run([python, "-m", "pip", "install", "-q", "--no-build-isolation", "-r", str(requirements)], cwd=backend_dir, env=pip_env, timeout=1800, check=True)
        if requirements_dev.exists() and requirements_dev.read_text().strip():
            _run([python, "-m", "pip", "install", "-q", "--no-build-isolation", "-r", str(requirements_dev)], cwd=backend_dir, env=pip_env, timeout=1800, check=True)
            notes.append(f"installed {requirements_dev.relative_to(REPO_ROOT)}")
    finally:
        # Restore pyproject.toml
        if pyproject_backup and pyproject_backup.exists():
            pyproject_backup.rename(pyproject_toml)

    expected = _parse_requirements(requirements) | _parse_requirements(requirements_dev)
    installed_all = _pip_list_all(python)
    installed_top = _pip_list_not_required(python)
    ignore = {"pip", "setuptools", "wheel", "bars-backend", "bars", "httptools", "uvloop", "watchfiles", "websockets"}
    extras = sorted((installed_top - ignore) - (expected - ignore))
    missing = sorted((expected - ignore) - (installed_all - ignore))

    if extras:
        warnings.append(f"unexpected top-level packages in backend/.venv: {', '.join(extras)}")
        warnings.append("recommendation: add to backend/requirements.txt or uninstall from backend/.venv")
    if missing:
        warnings.append(f"missing expected packages in backend/.venv: {', '.join(missing)}")

    return InstallResult("backend", True, time.time() - started, notes=notes, warnings=warnings)


if __name__ == "__main__":
    result = install_backend()
    status = "✅" if result.ok else "❌"
    print(f"{status} {result.name} ({result.seconds:.1f}s)")
    for n in result.notes:
        print(f"  - {n}")
    for w in result.warnings:
        print(f"  - ⚠️  {w}")
    sys.exit(0 if result.ok else 1)
