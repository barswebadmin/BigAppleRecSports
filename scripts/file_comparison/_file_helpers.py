#!/usr/bin/env python3
"""
Shared file handling utilities for comparison.
Extracted to reduce duplication and complexity.
"""

import os
from pathlib import Path
from typing import Iterator, List, Optional, Set

# Supported file extensions for comparison
SUPPORTED_EXTENSIONS = ['.py', '.js', '.gs', '.pyi', '.mjs']


def normalize_extension(path: Path) -> Path:
    """
    Normalize file extensions for comparison (.gs -> .js for GAS).
    
    Args:
        path: Path to normalize
        
    Returns:
        Path with normalized extension
    """
    if path.suffix.lower() == '.gs':
        return path.with_suffix('.js')
    return path


def read_file_lines(file_path: Path) -> Optional[List[str]]:
    """
    Read file lines with error handling.
    
    Args:
        file_path: Path to file
        
    Returns:
        List of lines or None if error
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.readlines()
    except Exception:
        return None


def discover_files(path: Path, exclude_patterns: Optional[List[str]] = None, 
                   follow_symlinks: bool = True) -> Iterator[Path]:
    """
    Discover all relevant files in a path, optionally following symlinks.
    
    Args:
        path: Directory to search
        exclude_patterns: Patterns to exclude (e.g., ['__pycache__', '*.pyc'])
        follow_symlinks: Whether to follow symlinks
        
    Yields:
        File paths relative to base path
    """
    exclude_patterns = exclude_patterns or []
    
    def should_exclude(file_path: Path) -> bool:
        """Check if file should be excluded."""
        file_str = str(file_path)
        for pattern in exclude_patterns:
            if pattern in file_str or file_path.match(pattern):
                return True
        if '__pycache__' in file_str:
            return True
        return False
    
    def walk_directory(root: Path, base: Path, current_rel: Path = Path('.')) -> Iterator[Path]:
        """Walk directory tree, optionally following symlinks."""
        try:
            for entry in os.scandir(root):
                entry_name = entry.name
                entry_path = Path(entry.path)
                rel_path = current_rel / entry_name
                
                if entry.is_symlink() and follow_symlinks:
                    # Resolve symlink and recurse into it
                    try:
                        resolved = entry_path.resolve()
                        if resolved.is_dir():
                            yield from walk_directory(resolved, base, rel_path)
                        elif resolved.is_file() and resolved.suffix in SUPPORTED_EXTENSIONS:
                            if not should_exclude(resolved):
                                yield base / rel_path
                    except (OSError, RuntimeError):
                        continue
                elif entry.is_dir():
                    # Regular directory, recurse
                    yield from walk_directory(entry_path, base, rel_path)
                elif entry.is_file() and entry_path.suffix in SUPPORTED_EXTENSIONS:
                    # Regular file
                    if not should_exclude(entry_path):
                        yield base / rel_path
        except (OSError, PermissionError):
            pass
    
    resolved_base = path.resolve()
    yield from walk_directory(resolved_base, path)


def find_matching_files(path1: Path, path2: Path, 
                       exclude_patterns: Optional[List[str]] = None) -> List[tuple[Path, Path]]:
    """
    Find files that exist in both paths (by relative path, normalizing extensions).
    
    Args:
        path1: First path to compare
        path2: Second path to compare
        exclude_patterns: Patterns to exclude
        
    Returns:
        List of (file1_path, file2_path) tuples
    """
    matching = []
    
    # Build a map of normalized paths to actual paths for path2
    path2_map = {}
    for file2_path in discover_files(path2, exclude_patterns):
        rel_path = file2_path.relative_to(path2)
        normalized_rel = normalize_extension(rel_path)
        path2_map[normalized_rel] = file2_path
    
    # Find matches in path1
    for file1_path in discover_files(path1, exclude_patterns):
        rel_path = file1_path.relative_to(path1)
        normalized_rel = normalize_extension(rel_path)
        
        if normalized_rel in path2_map:
            matching.append((file1_path, path2_map[normalized_rel]))
    
    return matching


def get_files_only_in_path(source_path: Path, target_path: Path,
                           exclude_patterns: Optional[List[str]] = None) -> List[Path]:
    """
    Find files that exist in source_path but not in target_path (normalizing extensions).
    
    Args:
        source_path: Path to search
        target_path: Path to compare against
        exclude_patterns: Patterns to exclude
        
    Returns:
        List of file paths only in source_path
    """
    # Get all files discovered in target_path, normalized by extension
    target_files_normalized = {}
    for f in discover_files(target_path, exclude_patterns):
        rel_path = f.relative_to(target_path)
        normalized_rel = normalize_extension(rel_path)
        target_files_normalized[normalized_rel] = f
    
    files_only_in_source = []
    for file_path in discover_files(source_path, exclude_patterns):
        rel_path = file_path.relative_to(source_path)
        normalized_rel = normalize_extension(rel_path)
        
        # Check if file exists in target using normalized extension comparison
        if normalized_rel not in target_files_normalized:
            files_only_in_source.append(file_path)
    
    return files_only_in_source
