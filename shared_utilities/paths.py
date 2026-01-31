"""
Centralized path utilities for the BARS project.

Provides consistent access to repository root from anywhere in the codebase.
"""

import os
from pathlib import Path


def get_repo_root() -> Path:
    """
    Get the repository root directory.
    
    First tries to get REPO_ROOT from environment variable.
    If not found, falls back to finding it relative to this file.
    
    Returns:
        Path to repository root
    """
    # Try environment variable first
    repo_root_str = os.getenv('REPO_ROOT')
    if repo_root_str:
        return Path(repo_root_str).resolve()
    
    # Fallback: detect environment and calculate accordingly
    current_file = Path(__file__).resolve()
    
    # Check if we're in a monorepo structure (local dev)
    potential_repo_root = current_file.parent.parent
    if (potential_repo_root / 'pyproject.toml').exists():
        # Monorepo structure: shared_utilities/paths.py -> ../../
        return potential_repo_root
    
    # Deployment structure: shared_utilities is copied into backend/
    # Navigate up from backend/shared_utilities/paths.py to backend/
    return current_file.parent.parent


# Convenience constant for immediate use in imports
REPO_ROOT = get_repo_root()
