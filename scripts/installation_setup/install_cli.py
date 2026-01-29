#!/usr/bin/env python3
"""
CLI installation script.

Installs bars CLI via pipx with dependencies from pyproject.toml.
Also sets up shell completion.
"""
import json
import re
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


def _norm_pkg_name(name: str) -> str:
    return re.sub(r"[-_]+", "-", name.strip().lower())


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


def get_python_version_from_pyproject() -> Optional[str]:
    """Extract Python version from pyproject.toml requires-python field."""
    pyproject_path = REPO_ROOT / "pyproject.toml"
    if not pyproject_path.exists():
        return None

    content = pyproject_path.read_text()
    match = re.search(r'requires-python\s*=\s*"([^"]+)"', content)
    if not match:
        return None

    required_version = match.group(1)
    min_version_match = re.search(r'>=(\d+\.\d+)', required_version)
    if not min_version_match:
        return None

    return min_version_match.group(1)


def find_python_interpreter(version: str) -> Optional[str]:
    """Find Python interpreter for the given version."""
    python_cmd = f"python{version}"

    try:
        result = subprocess.run(
            [python_cmd, "--version"],
            capture_output=True,
            check=True,
            timeout=5
        )
        return python_cmd
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def _is_pipx_installed(package_name: str) -> bool:
    try:
        res = _run(["pipx", "list", "--json"], cwd=REPO_ROOT, capture=True, timeout=15, check=True)
        data = json.loads(res.stdout or "{}")
        return package_name in (data.get("venvs", {}) or {})
    except Exception:
        return False


def install_package() -> bool:
    """Install the bars CLI package with smart failure handling."""
    package_name = 'bars'

    python_version = get_python_version_from_pyproject()
    python_cmd = None
    if python_version:
        python_cmd = find_python_interpreter(python_version)
        if python_cmd:
            print(f"  Detected Python requirement: {python_version} (found {python_cmd})")
        else:
            print(f"  ⚠️  Python {python_version} not found, pipx will use default Python")

    while True:
        installed = _is_pipx_installed(package_name)
        print("  Installing bars CLI package...")
        if python_cmd and installed:
            pipx_cmd = ["pipx", "reinstall", package_name, "--python", python_cmd]
            print(f"    📦 Running: pipx reinstall {package_name} --python {python_cmd}")
        elif python_cmd and not installed:
            pipx_cmd = ["pipx", "install", "-e", ".", "--python", python_cmd]
            print(f"    📦 Running: pipx install -e . --python {python_cmd}")
        elif installed:
            pipx_cmd = ["pipx", "install", "-e", ".", "--force"]
            print("    📦 Running: pipx install -e . --force")
        else:
            pipx_cmd = ["pipx", "install", "-e", "."]
            print("    📦 Running: pipx install -e .")
        print("    ⏳ This may take a moment (installing package and dependencies from pyproject.toml)...")
        result = subprocess.run(
            pipx_cmd,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("    ✅ Installed bars CLI package and dependencies")
            return True

        print("")
        print("    Error details:")
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    print(f"      {line}")
        if result.stderr:
            for line in result.stderr.strip().split('\n'):
                if line.strip():
                    print(f"      {line}")
        print("")

        if not sys.stdin.isatty():
            print("    ❌ Non-interactive terminal; aborting.")
            return False

        while True:
            print("    What would you like to do?")
            print("      (c) Continue with reinstall (uninstall + fresh install)")
            print("      (r) Retry install")
            print("      (e) Exit")
            print("")
            choice = input("    Choice [c/r/e]: ").strip().lower()

            if choice in ('c', 'continue'):
                print("    🔄 Reinstalling bars CLI package (clean install)...")
                reinstall_cmd = ['pipx', 'reinstall', package_name]
                if python_cmd:
                    reinstall_cmd.extend(['--python', python_cmd])
                print(f"    ⏳ Running: {' '.join(reinstall_cmd)}")
                reinstall_result = subprocess.run(
                    reinstall_cmd,
                    capture_output=True,
                    text=True
                )
                if reinstall_result.returncode == 0:
                    print("    ✅ Reinstalled bars CLI package and dependencies")
                    return True
                if reinstall_result.stdout:
                    for line in reinstall_result.stdout.strip().split("\n"):
                        if line.strip():
                            print(f"      {line}")
                if reinstall_result.stderr:
                    for line in reinstall_result.stderr.strip().split("\n"):
                        if line.strip():
                            print(f"      {line}")

                print("    ⚠️  pipx reinstall failed, trying uninstall + install...")
                print("    🗑️  Uninstalling existing package...")
                subprocess.run(
                    ['pipx', 'uninstall', package_name],
                    capture_output=True,
                    text=True
                )
                break

            elif choice in ('r', 'retry'):
                print("    🔄 Retrying install...")
                break

            elif choice in ('e', 'exit'):
                print("    🛑 Installation aborted by user")
                return False

            else:
                print("    ⚠️  Invalid choice. Please enter 'c', 'r', or 'e'")
                continue


def setup_shell_completion() -> bool:
    """Add shell completion setup to .zshrc if not already present."""
    zshrc_path = Path.home() / '.zshrc'
    completion_line = 'eval "$(_BARS_COMPLETE=zsh_source bars | /usr/bin/sed \'s/env /\\/usr\\/bin\\/env /g\')"'

    print("  Setting up shell completion in .zshrc...")

    if not zshrc_path.exists():
        try:
            zshrc_path.touch()
            print(f"    ℹ️  Created {zshrc_path}")
        except Exception as e:
            print(f"    ⚠️  Could not create {zshrc_path}: {e}")
            return False

    try:
        zshrc_content = zshrc_path.read_text()

        if '_BARS_COMPLETE=zsh_source bars' in zshrc_content:
            print("    ℹ️  Shell completion already configured in .zshrc")
            return True

        with zshrc_path.open('a') as f:
            f.write('\n')
            f.write('# bars CLI shell completion\n')
            f.write(f'{completion_line}\n')

        print(f"    ✅ Added shell completion to {zshrc_path}")
        print("    ℹ️  Run 'source ~/.zshrc' or restart your terminal to activate completion")
        return True

    except Exception as e:
        print(f"    ⚠️  Could not update {zshrc_path}: {e}")
        return False


@dataclass
class InstallResult:
    name: str
    ok: bool
    seconds: float
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def sync_pyproject_dependencies() -> None:
    """Sync dependencies from backend/requirements.txt to pyproject.toml.
    
    Reads PRODUCTION dependencies from backend/requirements.txt and updates
    pyproject.toml's dependencies section, preserving CLI-specific dependencies.
    """
    pyproject_path = REPO_ROOT / "pyproject.toml"
    requirements_path = REPO_ROOT / "backend" / "requirements.txt"
    
    if not requirements_path.exists() or not pyproject_path.exists():
        return
    
    # Get CLI-specific dependencies from pyproject.toml (preserve existing)
    cli_deps: list[str] = []
    if pyproject_path.exists():
        content = pyproject_path.read_text()
        deps_match = re.search(r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if deps_match:
            for line in deps_match.group(1).split('\n'):
                line = line.strip().rstrip(',').strip()
                if line.startswith('"') and line.endswith('"'):
                    line = line[1:-1]
                elif line.startswith("'") and line.endswith("'"):
                    line = line[1:-1]
                if line and not line.startswith('#') and '>=' in line and '==' not in line:
                    cli_deps.append(line)
    
    # Parse PRODUCTION dependencies from requirements.txt
    production_deps: list[str] = []
    in_production_section = False
    for line in requirements_path.read_text().splitlines():
        original_line = line
        line = line.strip()
        
        if re.search(r'^#+\s*PRODUCTION\s+DEPENDENCIES', line, re.IGNORECASE):
            in_production_section = True
            continue
        
        if re.search(r'^#+\s*(SERVER|TESTING)\s+DEPENDENCIES', line, re.IGNORECASE):
            break
        
        if in_production_section:
            if not line or line.startswith('#'):
                continue
            if not line.startswith('-r'):
                production_deps.append(original_line.strip())
    
    if not production_deps:
        return
    
    # Combine and deduplicate
    all_deps = cli_deps + production_deps
    seen = set()
    unique_deps = []
    for dep in all_deps:
        pkg = re.split(r'[>=<!=]', dep.strip())[0].strip().lower()
        if pkg not in seen:
            seen.add(pkg)
            unique_deps.append(dep)
    
    # Sort (CLI deps first, then alphabetical)
    cli_pkgs = {re.split(r'[>=<!=]', d.strip())[0].strip().lower() for d in cli_deps}
    sorted_deps = sorted(
        unique_deps,
        key=lambda d: (
            0 if re.split(r'[>=<!=]', d.strip())[0].strip().lower() in cli_pkgs else 1,
            re.split(r'[>=<!=]', d.strip())[0].strip().lower()
        )
    )
    
    # Update pyproject.toml
    deps_lines = [f'    "{dep}",' for dep in sorted_deps]
    deps_block = 'dependencies = [\n' + '\n'.join(deps_lines) + '\n]'
    
    content = pyproject_path.read_text()
    pattern = r'dependencies\s*=\s*\[.*?\]'
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, deps_block, content, flags=re.DOTALL)
    else:
        content = re.sub(
            r'(requires-python\s*=\s*"[^"]+")\s*\n',
            r'\1\n' + deps_block + '\n',
            content
        )
    
    pyproject_path.write_text(content)


def install_cli() -> InstallResult:
    """Install CLI via pipx."""
    started = time.time()
    notes: list[str] = []
    warnings: list[str] = []

    print("  Syncing dependencies from backend/requirements.txt to pyproject.toml...")
    sync_pyproject_dependencies()
    
    if not install_package():
        return InstallResult("cli", False, time.time() - started, warnings=["pipx installation failed"])

    setup_shell_completion()

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


if __name__ == "__main__":
    result = install_cli()
    status = "✅" if result.ok else "❌"
    print(f"{status} {result.name} ({result.seconds:.1f}s)")
    for n in result.notes:
        print(f"  - {n}")
    for w in result.warnings:
        print(f"  - ⚠️  {w}")
    sys.exit(0 if result.ok else 1)
