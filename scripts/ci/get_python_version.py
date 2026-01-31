#!/usr/bin/env python3
"""Extract Python version from pyproject.toml."""
import re
import sys
from pathlib import Path

import sys
from pathlib import Path

# Add shared utilities to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared_utilities"))
from paths import get_repo_root

project_root = get_repo_root()
sys.path.insert(0, str(project_root))

from scripts._shared.path_utils import PROJECT_ROOT


def get_python_version() -> str:
    """Extract Python version from pyproject.toml."""
    pyproject = PROJECT_ROOT / "pyproject.toml"
    content = pyproject.read_text()
    match = re.search(r'requires-python\s*=\s*"([^"]+)"', content)
    if not match:
        raise RuntimeError("requires-python not found in pyproject.toml")
    
    version_spec = match.group(1)
    version_match = re.search(r'(\d+\.\d+)', version_spec)
    if not version_match:
        raise RuntimeError(f"Could not parse version from requires-python: {version_spec}")
    
    return version_match.group(1)


if __name__ == "__main__":
    print(get_python_version())
