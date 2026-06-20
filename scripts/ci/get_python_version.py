#!/usr/bin/env python3
"""Extract Python version from pyproject.toml."""
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def get_python_version() -> str:
    """Extract Python version from pyproject.toml."""
    pyproject = _REPO_ROOT / "pyproject.toml"
    content = pyproject.read_text()
    match = re.search(r'requires-python\s*=\s*"([^"]+)"', content)
    if not match:
        raise RuntimeError("requires-python not found in pyproject.toml")

    version_spec = match.group(1)
    version_match = re.search(r"(\d+\.\d+)", version_spec)
    if not version_match:
        raise RuntimeError(f"Could not parse version from requires-python: {version_spec}")

    return version_match.group(1)


if __name__ == "__main__":
    print(get_python_version())
