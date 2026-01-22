#!/usr/bin/env python3
"""
Sync dependencies from backend/requirements.txt to pyproject.toml.

Reads PRODUCTION dependencies from backend/requirements.txt and updates
pyproject.toml's dependencies section, excluding SERVER and TESTING dependencies.
"""
import re
from pathlib import Path
from typing import List, Set


def parse_production_dependencies() -> List[str]:
    """Parse PRODUCTION section from backend/requirements.txt, preserving versions."""
    deps = []
    req_path = Path('backend/requirements.txt')
    
    if not req_path.exists():
        return deps
    
    in_production_section = False
    for line in req_path.read_text().splitlines():
        original_line = line
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
                # Handle includes (not expected in PRODUCTION section, but handle gracefully)
                include_path = line.split()[1]
                deps.extend(parse_production_dependencies())
            else:
                # Preserve the full line with version specifiers
                deps.append(original_line.strip())
    
    return deps


def get_cli_specific_dependencies() -> List[str]:
    """Get CLI-specific dependencies from pyproject.toml.
    
    These are dependencies that use >= version specifiers (CLI deps)
    vs == specifiers (production deps from requirements.txt).
    """
    pyproject_path = Path('pyproject.toml')
    if not pyproject_path.exists():
        # Fallback if pyproject.toml doesn't exist yet
        return [
            "click>=8.1.7",
            "rich>=13.7.0",
            "questionary>=2.0.0",
            "sgqlc>=17.0",
        ]
    
    content = pyproject_path.read_text()
    deps_match = re.search(
        r'dependencies\s*=\s*\[(.*?)\]',
        content,
        re.DOTALL
    )
    
    if not deps_match:
        return []
    
    cli_deps = []
    for line in deps_match.group(1).split('\n'):
        line = line.strip().rstrip(',').strip()
        # Remove surrounding quotes if present
        if line.startswith('"') and line.endswith('"'):
            line = line[1:-1]
        elif line.startswith("'") and line.endswith("'"):
            line = line[1:-1]
        
        # Only include dependencies with >= (CLI-specific) not == (production)
        if line and not line.startswith('#') and '>=' in line and '==' not in line:
            cli_deps.append(line)
    
    return cli_deps


def normalize_dependency(dep: str) -> str:
    """Normalize dependency string for comparison (extract package name)."""
    # Remove version specifiers and whitespace
    pkg = re.split(r'[>=<!=]', dep.strip())[0].strip().lower()
    return pkg


def update_pyproject_toml(production_deps: List[str], cli_deps: List[str]) -> None:
    """Update pyproject.toml dependencies section."""
    pyproject_path = Path('pyproject.toml')
    
    if not pyproject_path.exists():
        raise FileNotFoundError("pyproject.toml not found")
    
    content = pyproject_path.read_text()
    
    # Combine all dependencies
    all_deps = cli_deps + production_deps
    
    # Remove duplicates (by package name, keeping first occurrence)
    seen = set()
    unique_deps = []
    for dep in all_deps:
        pkg = normalize_dependency(dep)
        if pkg not in seen:
            seen.add(pkg)
            unique_deps.append(dep)
    
    # Sort dependencies (CLI-specific first, then alphabetical)
    cli_pkgs = {normalize_dependency(d) for d in cli_deps}
    sorted_deps = sorted(
        unique_deps,
        key=lambda d: (
            0 if normalize_dependency(d) in cli_pkgs else 1,  # CLI deps first
            normalize_dependency(d)  # Then alphabetical
        )
    )
    
    # Format as TOML array
    deps_lines = [f'    "{dep}",' for dep in sorted_deps]
    deps_block = 'dependencies = [\n' + '\n'.join(deps_lines) + '\n]'
    
    # Replace dependencies section
    pattern = r'dependencies\s*=\s*\[.*?\]'
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, deps_block, content, flags=re.DOTALL)
    else:
        # If no dependencies section exists, add it after requires-python
        content = re.sub(
            r'(requires-python\s*=\s*"[^"]+")\s*\n',
            r'\1\n' + deps_block + '\n',
            content
        )
    
    pyproject_path.write_text(content)


def main():
    """Main entry point."""
    print("🔄 Syncing dependencies from backend/requirements.txt to pyproject.toml...")
    
    # Get CLI-specific dependencies from pyproject.toml (preserve existing)
    cli_deps = get_cli_specific_dependencies()
    print(f"  📦 Preserving {len(cli_deps)} CLI-specific dependencies from pyproject.toml")
    
    # Get production dependencies from requirements.txt
    production_deps = parse_production_dependencies()
    if not production_deps:
        print("  ⚠️  No PRODUCTION dependencies found in backend/requirements.txt")
        if not cli_deps:
            print("  ⚠️  No dependencies to sync")
        return
    
    print(f"  📦 Found {len(production_deps)} PRODUCTION dependencies from requirements.txt")
    
    # Update pyproject.toml (preserves CLI deps, updates production deps)
    update_pyproject_toml(production_deps, cli_deps)
    
    # Count final dependencies
    final_deps = cli_deps + production_deps
    # Remove duplicates for count
    unique_count = len(set(normalize_dependency(d) for d in final_deps))
    
    print("  ✅ Updated pyproject.toml dependencies")
    print(f"  📋 Total dependencies: {unique_count} ({len(cli_deps)} CLI + {len(production_deps)} production)")


if __name__ == '__main__':
    main()
