#!/usr/bin/env python3
"""
Local dependency installer for BARS.

Targets:
- cli:    pipx install -e . (dependencies from pyproject.toml)
- backend: install backend/requirements.txt into backend/.venv
- backend dev: also install backend/requirements-dev.txt if present
- google: pnpm install in GoogleAppsScripts/
- aws:    for each lambda/functions/*/requirements.txt, install into a temp dir (packaging-style)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]

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


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _parse_pyproject_deps(pyproject_path: Path) -> set[str]:
    import tomllib

    data = tomllib.loads(pyproject_path.read_text())
    deps = data.get("project", {}).get("dependencies", []) or []
    out: set[str] = set()
    for dep in deps:
        dep = str(dep).strip()
        if not dep:
            continue
        name = re.split(r"[<>=!~\s;\[]", dep, maxsplit=1)[0]
        if name:
            out.add(_norm_pkg_name(name))
    return out


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


def _pipx_python(package_name: str) -> Optional[str]:
    try:
        res = _run(["pipx", "list", "--json"], cwd=REPO_ROOT, capture=True, timeout=30, check=True)
        data = json.loads(res.stdout)
        meta = data.get("venvs", {}).get(package_name, {}).get("metadata", {}) or {}
        interp = meta.get("source_interpreter", {})
        if isinstance(interp, dict):
            p = interp.get("__Path__")
            return str(p) if p else None
        return None
    except Exception:
        return None


def _pipx_runpip_list_json(package_name: str, args: list[str], *, timeout: int = 60) -> list[dict]:
    res = _run(["pipx", "runpip", package_name, "list", "--format=json", *args], cwd=REPO_ROOT, capture=True, timeout=timeout, check=True)
    return json.loads(res.stdout or "[]")


def _pipx_list_all(package_name: str) -> set[str]:
    pkgs = _pipx_runpip_list_json(package_name, [])
    return {_norm_pkg_name(p["name"]) for p in pkgs if isinstance(p, dict) and p.get("name")}


def _pipx_list_not_required(package_name: str) -> set[str]:
    try:
        pkgs = _pipx_runpip_list_json(package_name, ["--not-required"])
        return {_norm_pkg_name(p["name"]) for p in pkgs if isinstance(p, dict) and p.get("name")}
    except Exception:
        return set()


def _python_venv_python(venv_dir: Path) -> str:
    return str(venv_dir / "bin" / "python")


@dataclass
class InstallResult:
    name: str
    ok: bool
    seconds: float
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _recommendations(
    *,
    installed_top: set[str],
    expected_top: set[str],
    ignore: set[str],
) -> tuple[list[str], list[str]]:
    installed = installed_top - ignore
    expected = expected_top - ignore
    extras = sorted(installed - expected)
    missing = sorted(expected - installed)
    return extras, missing


def install_backend() -> InstallResult:
    started = time.time()
    backend_dir = REPO_ROOT / "backend"
    venv_dir = backend_dir / ".venv"
    requirements = backend_dir / "requirements.txt"
    requirements_dev = backend_dir / "requirements-dev.txt"

    notes: list[str] = []
    warnings: list[str] = []

    if not venv_dir.exists():
        _run([sys.executable, "-m", "venv", str(venv_dir)], cwd=REPO_ROOT, timeout=300, check=True)
        notes.append(f"created {venv_dir}")

    python = _python_venv_python(venv_dir)
    pip_env = _pip_env()
    _run([python, "-m", "pip", "install", "-q", "--upgrade", "pip"], cwd=REPO_ROOT, env=pip_env, timeout=300, check=True)
    _run([python, "-m", "pip", "install", "-q", "-r", str(requirements)], cwd=REPO_ROOT, env=pip_env, timeout=1800, check=True)
    if requirements_dev.exists() and requirements_dev.read_text().strip():
        _run([python, "-m", "pip", "install", "-q", "-r", str(requirements_dev)], cwd=REPO_ROOT, env=pip_env, timeout=1800, check=True)
        notes.append(f"installed {requirements_dev.relative_to(REPO_ROOT)}")

    expected = _parse_requirements(requirements) | _parse_requirements(requirements_dev)
    installed_all = _pip_list_all(python)
    installed_top = _pip_list_not_required(python)
    # Note: uvicorn[standard] installs optional runtime extras that may show as not-required.
    ignore = {"pip", "setuptools", "wheel", "bars-backend", "httptools", "uvloop", "watchfiles", "websockets"}
    extras = sorted((installed_top - ignore) - (expected - ignore))
    missing = sorted((expected - ignore) - (installed_all - ignore))

    if extras:
        warnings.append(f"unexpected top-level packages in backend/.venv: {', '.join(extras)}")
        warnings.append("recommendation: add to backend/requirements.txt or uninstall from backend/.venv")
    if missing:
        warnings.append(f"missing expected packages in backend/.venv: {', '.join(missing)}")

    return InstallResult("backend", True, time.time() - started, notes=notes, warnings=warnings)


def install_cli() -> InstallResult:
    started = time.time()
    notes: list[str] = []
    warnings: list[str] = []

    _run([sys.executable, "scripts/sync_pyproject_dependencies.py"], cwd=REPO_ROOT, timeout=300, check=True)
    _run([sys.executable, "scripts/install_pipx_environment.py"], cwd=REPO_ROOT, timeout=1800, check=True)

    pyproject = REPO_ROOT / "pyproject.toml"
    expected = _parse_pyproject_deps(pyproject)

    try:
        installed_all = _pipx_list_all("bars")
        installed_top = _pipx_list_not_required("bars")
    except Exception as e:
        return InstallResult("cli", False, time.time() - started, warnings=[f"could not query pipx venv for 'bars': {e}"])
    ignore = {"pip", "setuptools", "wheel", "bars"}
    extras = sorted((installed_top - ignore) - (expected - ignore))
    missing = sorted((expected - ignore) - (installed_all - ignore))

    if extras:
        warnings.append(f"unexpected top-level packages in pipx venv: {', '.join(extras)}")
        warnings.append("recommendation: add to pyproject.toml dependencies or uninject/uninstall from pipx venv")
    if missing:
        warnings.append(f"missing expected packages in pipx venv: {', '.join(missing)}")

    pipx_py = _pipx_python("bars")
    if pipx_py:
        notes.append(f"pipx python: {pipx_py}")
    return InstallResult("cli", True, time.time() - started, notes=notes, warnings=warnings)


def install_google() -> InstallResult:
    started = time.time()
    notes: list[str] = []
    warnings: list[str] = []

    gas_dir = REPO_ROOT / "GoogleAppsScripts"
    pkg_json = gas_dir / "package.json"
    expected = set()
    try:
        data = _read_json(pkg_json)
        for group in ("dependencies", "devDependencies"):
            for k in (data.get(group, {}) or {}).keys():
                expected.add(k)
    except Exception as e:
        return InstallResult("google", False, time.time() - started, warnings=[f"failed reading {pkg_json}: {e}"])

    try:
        _run(["pnpm", "install"], cwd=gas_dir, timeout=1800, check=True)
    except Exception as e:
        return InstallResult("google", False, time.time() - started, warnings=[f"pnpm install failed: {e}"])

    installed: set[str] = set()
    try:
        res = _run(["pnpm", "list", "--depth", "0", "--json"], cwd=gas_dir, timeout=120, capture=True, check=True)
        parsed = json.loads(res.stdout or "[]")
        if isinstance(parsed, list) and parsed:
            deps = (parsed[0].get("dependencies") or {}).keys()
            installed |= set(deps)
    except Exception:
        notes.append("pnpm list unavailable; skipped installed-vs-declared check")

    extras = sorted(installed - expected) if installed else []
    missing = sorted(expected - installed) if installed else []
    if extras:
        warnings.append(f"unexpected direct packages in pnpm list: {', '.join(extras)}")
        warnings.append("recommendation: add to GoogleAppsScripts/package.json or remove")
    if missing:
        warnings.append(f"declared packages not present in pnpm list: {', '.join(missing)}")

    return InstallResult("google", True, time.time() - started, notes=notes, warnings=warnings)


def _lambda_requirements_files() -> list[Path]:
    root = REPO_ROOT / "lambda" / "functions"
    if not root.exists():
        return []
    reqs: list[Path] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        req = child / "requirements.txt"
        if req.exists():
            content = req.read_text().strip()
            if content:
                reqs.append(req)
    return reqs


def _install_lambda_requirements(req_path: Path) -> tuple[str, bool, list[str]]:
    fn = req_path.parent.name
    expected = _parse_requirements(req_path)
    with tempfile.TemporaryDirectory(prefix=f"bars_lambda_deps_{fn}_") as td:
        target = Path(td)
        try:
            _run(
                [sys.executable, "-m", "pip", "install", "-q", "-r", str(req_path), "-t", str(target)],
                cwd=REPO_ROOT,
                env=_pip_env(),
                timeout=1800,
                check=True,
            )
            warnings: list[str] = []
            try:
                installed_all = _pip_list_all(sys.executable, extra_args=["--path", str(target)])
                installed_top = _pip_list_not_required(sys.executable, extra_args=["--path", str(target)])
                ignore = {"pip", "setuptools", "wheel"}
                extras = sorted((installed_top - ignore) - (expected - ignore))
                missing = sorted((expected - ignore) - (installed_all - ignore))
                if extras:
                    warnings.append(f"{fn}: unexpected top-level packages vs requirements.txt: {', '.join(extras)}")
                    warnings.append(f"{fn}: recommendation: add to requirements.txt or remove")
                if missing:
                    warnings.append(f"{fn}: missing expected packages vs requirements.txt: {', '.join(missing)}")
            except Exception:
                pass
            return fn, True, warnings
        except Exception as e:
            return fn, False, [str(e)]


def install_aws() -> InstallResult:
    started = time.time()
    notes: list[str] = []
    warnings: list[str] = []

    reqs = _lambda_requirements_files()
    if not reqs:
        notes.append("no lambda/functions/*/requirements.txt found; skipped")
        return InstallResult("aws", True, time.time() - started, notes=notes, warnings=warnings)

    max_workers = min(8, max(1, (os.cpu_count() or 4)))
    failures: list[str] = []
    mismatch_warnings: list[str] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(_install_lambda_requirements, r) for r in reqs]
        for fut in as_completed(futs):
            fn, ok, warn_list = fut.result()
            if not ok:
                failures.append(f"{fn}: {warn_list[0] if warn_list else 'install failed'}")
            else:
                mismatch_warnings.extend(warn_list)

    if failures:
        return InstallResult("aws", False, time.time() - started, notes=notes, warnings=failures + mismatch_warnings)

    warnings.extend(mismatch_warnings)
    notes.append(f"installed lambda requirements for {len(reqs)} function(s) (packaging-style)")
    return InstallResult("aws", True, time.time() - started, notes=notes, warnings=warnings)


INSTALLERS = {
    "backend": install_backend,
    "cli": install_cli,
    "google": install_google,
    "aws": install_aws,
}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Install dependencies for BARS components")
    parser.add_argument("target", nargs="?", choices=sorted(INSTALLERS.keys()), help="cli | backend | google | aws")
    args = parser.parse_args(argv)

    targets = [args.target] if args.target else ["cli", "backend", "google", "aws"]

    print(f"📦 Installing dependencies: {', '.join(targets)}")

    results: list[InstallResult] = []
    started = time.time()

    if args.target:
        results.append(INSTALLERS[args.target]())
    else:
        # Run in parallel; each installer handles its own sequencing.
        with ThreadPoolExecutor(max_workers=min(4, len(targets))) as ex:
            fut_map = {ex.submit(INSTALLERS[t]): t for t in targets}
            for fut in as_completed(fut_map):
                results.append(fut.result())

    results.sort(key=lambda r: targets.index(r.name))
    ok = all(r.ok for r in results)

    print("\nResults:")
    for r in results:
        status = "✅" if r.ok else "❌"
        print(f"- {status} {r.name} ({r.seconds:.1f}s)")
        for n in r.notes:
            print(f"  - {n}")
        for w in r.warnings:
            print(f"  - ⚠️  {w}")

    if not args.target:
        print(f"\nTotal: {time.time() - started:.1f}s")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

