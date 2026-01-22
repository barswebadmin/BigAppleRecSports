#!/usr/bin/env python3
"""
Install and manage pipx environment for bars CLI.

Handles:
- Installing the bars CLI package with smart failure handling
- Dependencies are automatically installed from pyproject.toml during package installation
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
    """Extract dependencies from pyproject.toml.
    
    Note: pyproject.toml dependencies are synced from backend/requirements.txt
    via scripts/sync_pyproject_dependencies.py, so this reads the synced version.
    """
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


def parse_production_dependencies() -> set[str]:
    """Parse PRODUCTION section from backend/requirements.txt."""
    deps = set()
    req_path = Path('backend/requirements.txt')
    
    if not req_path.exists():
        return deps
    
    in_production_section = False
    for line in req_path.read_text().splitlines():
        line = line.strip()
        
        # Check if we've hit the PRODUCTION section
        if re.search(r'^#+\s*PRODUCTION\s+DEPENDENCIES', line, re.IGNORECASE):
            in_production_section = True
            continue
        
        # Stop when we hit SERVER or TESTING section
        if re.search(r'^#+\s*(SERVER|TESTING)\s+DEPENDENCIES', line, re.IGNORECASE):
            break
        
        # Only parse lines in PRODUCTION section
        if in_production_section:
            if not line or line.startswith('#'):
                continue
            
            if line.startswith('-r'):
                include_path = line.split()[1]
                deps.update(parse_production_dependencies())
            else:
                pkg = re.split(r'[>=<!=]', line)[0].strip().lower()
                if pkg:
                    deps.add(pkg)
    
    return deps


def install_package() -> bool:
    """Install the bars CLI package with smart failure handling."""
    package_name = 'bars'
    
    while True:
        print("  Installing bars CLI package...")
        print("    📦 Running: pipx install -e . --force")
        print("    ⏳ This may take a moment (installing package and dependencies from pyproject.toml)...")
        result = subprocess.run(
            ['pipx', 'install', '-e', '.', '--force'],
            capture_output=False,  # Show output in real-time
            text=True
        )
        
        if result.returncode == 0:
            print("    ✅ Installed bars CLI package and dependencies")
            return True
        
        # Installation failed - re-run with capture to show error details
        print("    ❌ Installation failed, capturing error details...")
        error_result = subprocess.run(
            ['pipx', 'install', '-e', '.', '--force'],
            capture_output=True,
            text=True
        )
        print("")
        print("    Error details:")
        if error_result.stdout:
            for line in error_result.stdout.strip().split('\n'):
                if line.strip():
                    print(f"      {line}")
        if error_result.stderr:
            for line in error_result.stderr.strip().split('\n'):
                if line.strip():
                    print(f"      {line}")
        print("")
        
        # Prompt user for action
        while True:
            print("    What would you like to do?")
            print("      (c) Continue with reinstall (uninstall + fresh install)")
            print("      (r) Retry install")
            print("      (e) Exit")
            print("")
            choice = input("    Choice [c/r/e]: ").strip().lower()
            
            if choice in ('c', 'continue'):
                print("    🔄 Reinstalling bars CLI package (clean install)...")
                print("    ⏳ Running: pipx reinstall bars --editable")
                reinstall_result = subprocess.run(
                    ['pipx', 'reinstall', package_name, '--editable'],
                    capture_output=False,  # Show output in real-time
                    text=True
                )
                if reinstall_result.returncode == 0:
                    print("    ✅ Reinstalled bars CLI package and dependencies")
                    return True
                
                # Reinstall failed, try uninstall + install
                print("    ⚠️  pipx reinstall failed, trying uninstall + install...")
                print("    🗑️  Uninstalling existing package...")
                subprocess.run(
                    ['pipx', 'uninstall', package_name],
                    capture_output=False,
                    text=True
                )
                # Fall through to retry install in outer loop
                break
            
            elif choice in ('r', 'retry'):
                print("    🔄 Retrying install...")
                # Break inner loop to retry install in outer loop
                break
            
            elif choice in ('e', 'exit'):
                print("    🛑 Installation aborted by user")
                return False
            
            else:
                print("    ⚠️  Invalid choice. Please enter 'c', 'r', or 'e'")
                continue
        
        # Continue outer loop to retry install


def inject_requirements() -> bool:
    """Inject dependencies from pyproject.toml into pipx venv.
    
    Note: pyproject.toml dependencies are synced from backend/requirements.txt
    via scripts/sync_pyproject_dependencies.py, so this reads the synced version.
    """
    print("  Installing dependencies from pyproject.toml...")
    
    # Get dependencies from pyproject.toml (already synced from requirements.txt)
    pyproject_deps = _get_pyproject_deps_with_versions()
    if not pyproject_deps:
        print("    ⚠️  No dependencies found in pyproject.toml")
        return True
    
    # Create temporary requirements file for pipx inject
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


def _get_pyproject_deps_with_versions() -> list[str]:
    """Extract dependencies from pyproject.toml with version specifiers preserved.
    
    Note: pyproject.toml dependencies are synced from backend/requirements.txt
    via scripts/sync_pyproject_dependencies.py, so this reads the synced version.
    """
    pyproject_path = Path('pyproject.toml')
    if not pyproject_path.exists():
        return []
    
    content = pyproject_path.read_text()
    # Match dependencies array - handle multi-line with proper TOML format
    deps_match = re.search(
        r'dependencies\s*=\s*\[(.*?)\]',
        content,
        re.DOTALL
    )
    
    if not deps_match:
        return []
    
    deps = []
    for line in deps_match.group(1).split('\n'):
        # Remove leading/trailing whitespace, commas, and quotes
        line = line.strip().rstrip(',').strip()
        # Remove surrounding quotes if present
        if line.startswith('"') and line.endswith('"'):
            line = line[1:-1]
        elif line.startswith("'") and line.endswith("'"):
            line = line[1:-1]
        
        if line and not line.startswith('#'):
            deps.append(line)
    
    return deps




def remove_unused_packages(package_name: str, to_remove: set[str]) -> None:
    """Remove packages from pipx venv using pipx uninject."""
    for pkg in sorted(to_remove):
        try:
            subprocess.run(
                ['pipx', 'uninject', package_name, pkg],
                capture_output=True,
                check=False
            )
            print(f"    ✅ Removed {pkg}")
        except Exception as e:
            print(f"    ⚠️  Could not remove {pkg}: {e}")


def sync_dependencies() -> bool:
    """Remove unused packages from pipx venv.
    
    NOTE: This function is currently disabled because it was too aggressive
    and removed transitive dependencies. pipx already manages dependencies
    correctly, so manual cleanup is not needed.
    """
    # NOTE: sync_dependencies() removed - it was too aggressive and removed
    # transitive dependencies that are actually needed (e.g., click, rich, sgqlc).
    # pipx already manages dependencies correctly, so manual cleanup is not needed.
    return True


def main():
    parser = argparse.ArgumentParser(description='Install and manage pipx environment for bars CLI')
    args = parser.parse_args()
    
    if not install_package():
        sys.exit(1)
    
    # NOTE: inject_requirements() removed - pipx install -e . already installs
    # all dependencies from pyproject.toml automatically, so explicit injection
    # is redundant. The install_package() step handles everything.
    
    # NOTE: sync_dependencies() removed - it was too aggressive and removed
    # transitive dependencies that are actually needed (e.g., click, rich, sgqlc).
    # pipx already manages dependencies correctly, so manual cleanup is not needed.
    # sync_dependencies()


if __name__ == '__main__':
    main()
