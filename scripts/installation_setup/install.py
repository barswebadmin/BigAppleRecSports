#!/usr/bin/env python3
"""
Installation orchestrator for BARS components.

Orchestrates installation of:
- backend: Backend dependencies in backend/.venv
- cli: CLI tool via pipx
- google: Google Apps Scripts dependencies via pnpm
- lambda: Lambda function dependencies

When a target is specified, runs local development setup first, then the target.
When no target is specified, runs all installations.
"""
import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Add installation_setup to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from install_backend import install_backend, InstallResult
from install_cli import install_cli
from install_google import install_google
from install_lambda import install_lambda
from install_local_dev import install_local_dev


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Install dependencies for BARS components",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/installation_setup/install.py          # Install all components
  python scripts/installation_setup/install.py backend  # Install backend only
  python scripts/installation_setup/install.py cli     # Install CLI only
  python scripts/installation_setup/install.py google   # Install Google Apps Scripts only
  python scripts/installation_setup/install.py lambda   # Install Lambda functions only
        """
    )
    parser.add_argument(
        "target",
        nargs="?",
        choices=["backend", "cli", "google", "lambda"],
        help="Component to install (default: all)"
    )
    args = parser.parse_args(argv)

    targets = [args.target] if args.target else ["backend", "cli", "google", "lambda"]

    print(f"📦 Installing dependencies: {', '.join(targets)}")
    print()

    # Run local development setup first if a target is specified
    # (for local dev, we want direnv/IDE setup before project-specific installs)
    if args.target:
        print("🔧 Setting up local development environment...")
        if not install_local_dev():
            print("  ⚠️  Local development setup had issues, continuing...")
        print()

    # Map target names to installer functions
    INSTALLERS = {
        "backend": install_backend,
        "cli": install_cli,
        "google": install_google,
        "lambda": install_lambda,
    }

    results: list[InstallResult] = []
    started = time.time()

    if args.target:
        # Single target: run sequentially
        results.append(INSTALLERS[args.target]())
    else:
        # All targets: run sequentially to avoid race conditions with pyproject.toml
        for target in targets:
            results.append(INSTALLERS[target]())

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
