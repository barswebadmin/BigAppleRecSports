#!/usr/bin/env python3
"""
Install and manage pipx environment for bars CLI.

Handles:
- Installing the bars CLI package with smart failure handling
- Injecting dependencies from pyproject.toml
- Cleaning up unused packages (optional)
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path


def get_installed_packages(package_name: str) -> set[str]:
    """Get list of installed packages in pipx venv."""
    try:
        result = subprocess.run(
            ['pipx', 'runpip', package_name, 'list', '--format=freeze'],
            capture_output=True,
            text=True,
            check=True
        )
        installed = set()
        for line in result.stdout.splitlines():
            if '==' in line:
                pkg_name = re.split(r'[>=<!=]', line)[0].strip().lower()
                if pkg_name:
                    installed.add(pkg_name)
        return installed
    except subprocess.CalledProcessError:
        return set()


def get_pyproject_deps() -> set[str]:
    """Extract dependencies from pyproject.toml."""
    pyproject_path = Path('pyproject.toml')
    if not pyproject_path.exists():
        return set()
    
    content = pyproject_path.read_text()
    deps_match = re.search(
        r'\[project\]\s+dependencies\s*=\s*\[(.*?)\]',
        content,
        re.DOTALL
    )
    
    if not deps_match:
        return set()
    
    deps = set()
    for line in deps_match.group(1).split('\n'):
        line = line.strip().strip(',').strip('"').strip("'")
        if line and not line.startswith('#'):
            pkg = re.split(r'[>=<!=]', line)[0].strip().lower()
            if pkg:
                deps.add(pkg)
    return deps


def parse_requirements(filepath: str) -> set[str]:
    """Parse requirements.txt, handling -r includes."""
    deps = set()
    req_path = Path(filepath)
    
    if not req_path.exists():
        return deps
    
    for line in req_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        if line.startswith('-r'):
            include_path = line.split()[1]
            deps.update(parse_requirements(include_path))
        else:
            pkg = re.split(r'[>=<!=]', line)[0].strip().lower()
            if pkg:
                deps.add(pkg)
    
    return deps


def _get_pyproject_deps_with_versions() -> list[str]:
    """Extract dependencies from pyproject.toml with version specifiers preserved."""
    pyproject_path = Path('pyproject.toml')
    if not pyproject_path.exists():
        return []
    
    content = pyproject_path.read_text()
    deps_match = re.search(
        r'\[project\]\s+dependencies\s*=\s*\[(.*?)\]',
        content,
        re.DOTALL
    )
    
    if not deps_match:
        return []
    
    deps = []
    for line in deps_match.group(1).split('\n'):
        line = line.strip().rstrip(',').strip()
        if line.startswith('"') and line.endswith('"'):
            line = line[1:-1]
        elif line.startswith("'") and line.endswith("'"):
            line = line[1:-1]
        
        if line and not line.startswith('#'):
            deps.append(line)
    
    return deps


def install_package() -> bool:
    """Install the bars CLI package with smart failure handling."""
    package_name = 'bars'
    
    while True:
        print("  Installing bars CLI package...")
        result = subprocess.run(
            ['pipx', 'install', '-e', '.', '--force'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("    ✅ Installed bars CLI package")
            return True
        
        print("    ❌ Failed to install bars CLI package")
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
        
        while True:
            print("    What would you like to do?")
            print("      (c) Continue with reinstall (uninstall + fresh install)")
            print("      (r) Retry install")
            print("      (e) Exit")
            print("")
            choice = input("    Choice [c/r/e]: ").strip().lower()
            
            if choice in ('c', 'continue'):
                print("    🔄 Reinstalling bars CLI package (clean install)...")
                reinstall_result = subprocess.run(
                    ['pipx', 'reinstall', package_name, '--editable'],
                    capture_output=True,
                    text=True
                )
                if reinstall_result.returncode == 0:
                    print("    ✅ Reinstalled bars CLI package")
                    return True
                
                print("    ⚠️  pipx reinstall failed, trying uninstall + install...")
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


def inject_requirements() -> bool:
    """Inject dependencies from pyproject.toml into pipx venv."""
    print("  Installing dependencies from pyproject.toml...")
    
    pyproject_deps = _get_pyproject_deps_with_versions()
    if not pyproject_deps:
        print("    ⚠️  No dependencies found in pyproject.toml")
        return True
    
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
        req_path = Path(tmp.name)
        for dep_line in sorted(pyproject_deps):
            tmp.write(f"{dep_line}\n")
    
    try:
        result = subprocess.run(
            ['pipx', 'inject', 'bars', '-r', str(req_path), '--force'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("    ✅ Installed dependencies from pyproject.toml")
            return True
        else:
            print("    ⚠️  Some dependencies may already be installed")
            if result.stderr:
                print(f"    Note: {result.stderr}")
            return True
    finally:
        req_path.unlink()


def remove_unused_packages(package_name: str, to_remove: set[str]) -> None:
    """Remove packages from pipx venv using pipx uninject."""
    for pkg in sorted(to_remove):
        try:
            subprocess.run(
                ['pipx', 'uninject', package_name, pkg],
                capture_output=True,
                text=True,
                check=False
            )
            print(f"    ✅ Removed {pkg}")
        except Exception as e:
            print(f"    ⚠️  Could not remove {pkg}: {e}")


def cleanup_unused_packages(cleanup: bool) -> bool:
    """Remove unused packages from pipx venv."""
    if not cleanup:
        return True
    
    package_name = 'bars'
    print("  Cleaning up unused packages...")
    
    installed = get_installed_packages(package_name)
    if not installed:
        print("    ⚠️  Could not get installed packages list")
        return True
    
    pyproject_deps = get_pyproject_deps()
    req_deps = parse_requirements('requirements.txt')
    
    required = pyproject_deps | req_deps | {
        'bars', 'pip', 'setuptools', 'wheel', 'python-dotenv'
    }
    
    to_remove = installed - required
    
    if to_remove:
        print(f"    🗑️  Removing {len(to_remove)} unused packages...")
        remove_unused_packages(package_name, to_remove)
        print("    ✅ Cleanup complete")
    else:
        print("    ✅ No unused packages to remove")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Install and manage pipx environment for bars CLI'
    )
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Remove unused packages after installation'
    )
    parser.add_argument(
        '--cleanup-only',
        action='store_true',
        help='Only cleanup unused packages, do not install'
    )
    args = parser.parse_args()
    
    if args.cleanup_only:
        if not cleanup_unused_packages(cleanup=True):
            sys.exit(1)
        return
    
    if not install_package():
        sys.exit(1)
    
    if not inject_requirements():
        sys.exit(1)
    
    if not cleanup_unused_packages(cleanup=args.cleanup):
        sys.exit(1)


if __name__ == '__main__':
    main()
