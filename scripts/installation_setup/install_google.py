#!/usr/bin/env python3
"""
Google Apps Scripts installation script.

Installs npm dependencies via pnpm in GoogleAppsScripts/.
"""
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]


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


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


@dataclass
class InstallResult:
    name: str
    ok: bool
    seconds: float
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def install_google() -> InstallResult:
    """Install Google Apps Scripts dependencies via pnpm."""
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


if __name__ == "__main__":
    result = install_google()
    status = "✅" if result.ok else "❌"
    print(f"{status} {result.name} ({result.seconds:.1f}s)")
    for n in result.notes:
        print(f"  - {n}")
    for w in result.warnings:
        print(f"  - ⚠️  {w}")
    sys.exit(0 if result.ok else 1)
