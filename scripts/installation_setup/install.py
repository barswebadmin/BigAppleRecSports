#!/usr/bin/env python3
"""
Installation orchestrator for BARS components.

Orchestrates installation of:
- root: Monorepo-wide dev tools (ruff, pytest, mypy) in root .venv
- backend: Backend dependencies in backend/.venv
- cli: CLI tool via pipx
- google: Google Apps Scripts dependencies via pnpm
- lambda: Lambda function dependencies
- shared_utilities: Shared utilities in shared_utilities/.venv (for IDE/workspace)

When a target is specified, installs root dev tools first, then the target.
When no target is specified, runs all installations (root + all projects).
"""
import argparse
import sys
import time
from pathlib import Path

# Add installation_setup to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from install_backend import InstallResult, install_backend
from install_cli import install_cli
from install_google import install_google
from install_lambda import install_lambda
from install_root import install_root
from install_shared_utilities import install_shared_utilities


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Install dependencies for BARS components",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/installation_setup/install.py                    # Install all components (root + projects)
  python scripts/installation_setup/install.py root               # Install root dev tools only
  python scripts/installation_setup/install.py backend            # Install backend only (root first)
  python scripts/installation_setup/install.py cli               # Install CLI only (root first)
  python scripts/installation_setup/install.py google             # Install Google Apps Scripts only
  python scripts/installation_setup/install.py lambda             # Install Lambda functions only (root first)
  python scripts/installation_setup/install.py shared_utilities   # Install shared utilities only (root first)
        """
    )
    parser.add_argument(
        "target",
        nargs="?",
        choices=["root", "backend", "cli", "google", "lambda", "shared_utilities"],
        help="Component to install (default: all)"
    )
    args = parser.parse_args(argv)

    # Always install root dev tools first (unless installing root itself)
    if args.target != "root":
        print("🔧 Installing root monorepo dev tools first...")
        root_result = install_root()
        if not root_result.ok:
            print("  ⚠️  Root dev tools installation had issues, continuing...")
        print()

    targets = [args.target] if args.target else ["root", "shared_utilities", "backend", "cli", "google", "lambda"]

    print(f"📦 Installing dependencies: {', '.join(targets)}")
    print()

    # Map target names to installer functions
    installers = {
        "root": install_root,
        "backend": install_backend,
        "cli": install_cli,
        "google": install_google,
        "lambda": install_lambda,
        "shared_utilities": install_shared_utilities,
    }

    results: list[InstallResult] = []
    started = time.time()

    if args.target:
        # Single target: run sequentially (no optimization needed)
        results.append(installers[args.target]())
    else:
        # All targets: run sequentially with optimization
        # Track if shared_utilities was installed to avoid redundant installs
        shared_utilities_installed = False
        
        for target in targets:
            if target == "shared_utilities":
                results.append(installers[target]())
                shared_utilities_installed = True
            elif target in ["backend", "cli"] and shared_utilities_installed:
                # Skip redundant shared_utilities installation
                results.append(installers[target](skip_shared_utilities=True))
            else:
                results.append(installers[target]())

    # Sort results by target order
    results.sort(key=lambda r: targets.index(r.name))

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

    ok = all(r.ok for r in results)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
