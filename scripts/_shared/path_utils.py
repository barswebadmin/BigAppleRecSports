"""Shared path resolution utilities."""
from pathlib import Path


def get_project_root() -> Path:
    """Get project root directory (where .git/ exists)."""
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / '.git').exists():
            return current
        current = current.parent
    return Path.cwd().resolve()


PROJECT_ROOT = get_project_root()
