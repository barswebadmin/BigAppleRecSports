#!/usr/bin/env python3
"""Extract Python version from pyproject.toml."""
import re
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts._shared.path_utils import PROJECT_ROOT


def get_python_version() -> str:
    """Extract Python version from pyproject.toml."""
    pyproject = PROJECT_ROOT / "pyproject.toml"
    if not pyproject.exists():
        return "3.11"
    
    content = pyproject.read_text()
    match = re.search(r'requires-python\s*=\s*"([^"]+)"', content)
    if match:
        version_spec = match.group(1)
        # Parse ">=3.11,<3.12" -> "3.11"
        version_match = re.search(r'(\d+\.\d+)', version_spec)
        if version_match:
            return version_match.group(1)
    return "3.11"


if __name__ == "__main__":
    print(get_python_version())
