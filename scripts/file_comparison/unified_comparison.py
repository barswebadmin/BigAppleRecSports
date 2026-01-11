#!/usr/bin/env python3
"""
Unified comparison engine for code comparison.
Language-agnostic file comparison with smart diff filtering and code block move detection.
"""

import difflib
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Handle both module and standalone execution
try:
    from .python_comparator import PythonComparator
    from .javascript_comparator import JavaScriptComparator
    from .file_helpers import (
        discover_files, normalize_extension, find_matching_files,
        get_files_only_in_path, read_file_lines
    )
    from .code_block_mover import CodeBlockMoveDetector, MovedBlock
except ImportError:
    # Standalone execution - add parent directory to path
    import sys
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    sys.path.insert(0, str(repo_root))
    
    from scripts.file_comparison.python_comparator import PythonComparator
    from scripts.file_comparison.javascript_comparator import JavaScriptComparator
    from scripts.file_comparison.file_helpers import (
        discover_files, normalize_extension, find_matching_files,
        get_files_only_in_path, read_file_lines
    )
    from scripts.file_comparison.code_block_mover import CodeBlockMoveDetector, MovedBlock


class ComparisonStatus(Enum):
    """Status of a file comparison."""
    IDENTICAL = "identical"
    DIFFERENT = "different"
    ONLY_LOCAL = "only_local"
    ONLY_REMOTE = "only_remote"
    MOVED = "moved"


@dataclass
class FileComparison:
    """Result of comparing a single file."""
    local_path: Optional[Path]
    remote_path: Optional[Path]
    status: ComparisonStatus
    diff_lines: List[str] = field(default_factory=list)
    similarity: float = 0.0
    moved_from: Optional[Path] = None


@dataclass
class ComparisonResult:
    """Result of comparing two directories."""
    local_path: Path
    remote_path: Path
    files: Dict[str, FileComparison] = field(default_factory=dict)
    identical_count: int = 0
    different_count: int = 0
    only_local_count: int = 0
    only_remote_count: int = 0
    moved_count: int = 0
    total_files: int = 0
    moved_blocks: List[MovedBlock] = field(default_factory=list)  # Code block moves


class UnifiedComparison:
    """Unified comparison engine for code files."""
    
    def __init__(self, language: str = "auto", ignore_whitespace: bool = True, 
                 ignore_comments: bool = False, ignore_blank_lines: bool = False,
                 detect_code_block_moves: bool = True, min_block_size: int = 3):
        """
        Initialize comparison engine.
        
        Args:
            language: "python", "javascript", or "auto" (detect from files)
            ignore_whitespace: Ignore whitespace differences
            ignore_comments: Ignore comment differences
            ignore_blank_lines: Ignore blank line differences
            detect_code_block_moves: Whether to detect moved code blocks (default: True)
            min_block_size: Minimum lines in a code block to consider for moves (default: 3)
        """
        self.language = language
        self.ignore_whitespace = ignore_whitespace
        self.ignore_comments = ignore_comments
        self.ignore_blank_lines = ignore_blank_lines
        self.detect_code_block_moves = detect_code_block_moves
        self.min_block_size = min_block_size
        
        # Initialize language-specific comparators
        self.python_comparator = PythonComparator(
            ignore_whitespace=ignore_whitespace,
            ignore_comments=ignore_comments,
            ignore_blank_lines=ignore_blank_lines
        )
        self.javascript_comparator = JavaScriptComparator(
            ignore_whitespace=ignore_whitespace,
            ignore_comments=ignore_comments,
            ignore_blank_lines=ignore_blank_lines
        )
    
    def detect_language(self, file_path: Path) -> str:
        """Detect language from file extension."""
        ext = file_path.suffix.lower()
        if ext in ('.py', '.pyi'):
            return "python"
        elif ext in ('.js', '.gs', '.mjs'):
            return "javascript"
        elif ext in ('.json', '.yaml', '.yml', '.toml'):
            return "text"
        return "text"
    
    def normalize_extension(self, file_path: Path) -> Path:
        """Normalize file extensions for comparison (.gs -> .js)."""
        return normalize_extension(file_path)
    
    def get_file_hash(self, file_path: Path) -> str:
        """Get hash of file contents."""
        if not file_path.exists():
            return ""
        try:
            content = file_path.read_bytes()
            return hashlib.md5(content).hexdigest()
        except Exception:
            return ""
    
    def discover_files(self, directory: Path, exclude_patterns: Optional[List[str]] = None) -> Set[Path]:
        """
        Discover all files in a directory (using shared helper).
        
        Args:
            directory: Directory to search
            exclude_patterns: Patterns to exclude (e.g., ['__pycache__', '*.pyc'])
        
        Returns:
            Set of file paths relative to directory
        """
        if not directory.exists():
            return set()
        
        exclude_patterns = exclude_patterns or []
        files = set()
        
        for file_path in discover_files(directory, exclude_patterns, follow_symlinks=True):
            try:
                rel_path = file_path.relative_to(directory)
                files.add(rel_path)
            except ValueError:
                continue
        
        return files
    
    def compare_files(self, local_path: Path, remote_path: Path, 
                     relative_path: Path) -> FileComparison:
        """
        Compare two files.
        
        Args:
            local_path: Full path to local file
            remote_path: Full path to remote file
            relative_path: Relative path for display
        
        Returns:
            FileComparison result
        """
        if not local_path.exists() and not remote_path.exists():
            # Both missing (shouldn't happen)
            return FileComparison(
                local_path=None,
                remote_path=None,
                status=ComparisonStatus.IDENTICAL
            )
        
        if not local_path.exists():
            return FileComparison(
                local_path=None,
                remote_path=remote_path,
                status=ComparisonStatus.ONLY_REMOTE
            )
        
        if not remote_path.exists():
            return FileComparison(
                local_path=local_path,
                remote_path=None,
                status=ComparisonStatus.ONLY_LOCAL
            )
        
        # Detect language
        language = self.language
        if language == "auto":
            language = self.detect_language(local_path)
        
        # Get comparator
        if language == "python":
            comparator = self.python_comparator
        elif language == "javascript":
            comparator = self.javascript_comparator
        else:
            comparator = None
        
        # Compare files
        if comparator:
            identical, diff_lines, similarity = comparator.compare_files(local_path, remote_path)
        else:
            # Simple text comparison
            local_content = local_path.read_text(errors='replace')
            remote_content = remote_path.read_text(errors='replace')
            
            if self.ignore_whitespace:
                local_content = ' '.join(local_content.split())
                remote_content = ' '.join(remote_content.split())
            
            identical = local_content == remote_content
            
            if identical:
                diff_lines = []
                similarity = 1.0
            else:
                diff_lines = list(difflib.unified_diff(
                    remote_content.splitlines(keepends=True),
                    local_content.splitlines(keepends=True),
                    fromfile=str(remote_path),
                    tofile=str(local_path),
                    lineterm=''
                ))
                similarity = difflib.SequenceMatcher(
                    None, remote_content, local_content
                ).ratio()
        
        status = ComparisonStatus.IDENTICAL if identical else ComparisonStatus.DIFFERENT
        
        return FileComparison(
            local_path=local_path,
            remote_path=remote_path,
            status=status,
            diff_lines=diff_lines,
            similarity=similarity
        )
    
    def detect_moved_files(self, local_files: Set[Path], remote_files: Set[Path],
                     local_dir: Path, remote_dir: Path) -> Dict[Path, Path]:
        """
        Detect files that were moved/renamed by comparing content hashes.
        
        Returns:
            Dict mapping local_path -> remote_path for moved files
        """
        moved = {}
        
        # Build hash maps
        local_hashes: Dict[str, Path] = {}
        remote_hashes: Dict[str, Path] = {}
        
        for rel_path in local_files:
            full_path = local_dir / rel_path
            file_hash = self.get_file_hash(full_path)
            if file_hash:
                local_hashes[file_hash] = rel_path
        
        for rel_path in remote_files:
            full_path = remote_dir / rel_path
            file_hash = self.get_file_hash(full_path)
            if file_hash:
                remote_hashes[file_hash] = rel_path
        
        # Find moved files (same hash, different path)
        for file_hash, local_rel in local_hashes.items():
            if file_hash in remote_hashes:
                remote_rel = remote_hashes[file_hash]
                if local_rel != remote_rel:
                    # Check if this file is only in one location
                    if local_rel not in remote_files and remote_rel not in local_files:
                        moved[local_rel] = remote_rel
        
        return moved
    
    def compare_directories(self, local_path: Path, remote_path: Path,
                           exclude_patterns: Optional[List[str]] = None) -> ComparisonResult:
        """
        Compare two directories with optional code block move detection.
        
        Args:
            local_path: Path to local directory
            remote_path: Path to remote directory
            exclude_patterns: Patterns to exclude from comparison
        
        Returns:
            ComparisonResult with all file comparisons and moved code blocks
        """
        exclude_patterns = exclude_patterns or [
            '__pycache__', '*.pyc', '*.pyo', '.git', 'node_modules',
            '.clasp.json', '.clasp_*', 'build/', '.DS_Store'
        ]
        
        # Discover files using shared helper
        local_files = self.discover_files(local_path, exclude_patterns)
        remote_files = self.discover_files(remote_path, exclude_patterns)
        
        # Normalize extensions for matching
        local_files_normalized = {self.normalize_extension(f): f for f in local_files}
        remote_files_normalized = {self.normalize_extension(f): f for f in remote_files}
        
        # Detect moved files (whole file moves)
        moved = self.detect_moved_files(
            set(local_files_normalized.keys()),
            set(remote_files_normalized.keys()),
            local_path,
            remote_path
        )
        
        # Get matching files and files only in each path (for code block detection)
        matching_file_pairs = find_matching_files(local_path, remote_path, exclude_patterns)
        files_only_local = get_files_only_in_path(local_path, remote_path, exclude_patterns)
        files_only_remote = get_files_only_in_path(remote_path, local_path, exclude_patterns)
        
        # Detect code block moves if enabled
        moved_blocks: List[MovedBlock] = []
        if self.detect_code_block_moves:
            detector = CodeBlockMoveDetector(
                min_block_size=self.min_block_size,
                filter_same_file=False
            )
            moved_blocks = detector.detect_moves(
                matching_file_pairs, local_path, remote_path,
                files_only_local, files_only_remote
            )
        
        # Compare all files
        result = ComparisonResult(local_path=local_path, remote_path=remote_path)
        all_files = set(local_files_normalized.keys()) | set(remote_files_normalized.keys())
        
        for normalized_path in sorted(all_files):
            local_rel = local_files_normalized.get(normalized_path)
            remote_rel = remote_files_normalized.get(normalized_path)
            
            # Check if moved
            if normalized_path in moved:
                remote_rel = remote_files_normalized.get(moved[normalized_path])
                file_comp = FileComparison(
                    local_path=local_path / local_rel if local_rel else None,
                    remote_path=remote_path / remote_rel if remote_rel else None,
                    status=ComparisonStatus.MOVED,
                    moved_from=remote_rel
                )
                result.moved_count += 1
            else:
                local_full = local_path / local_rel if local_rel else None
                remote_full = remote_path / remote_rel if remote_rel else None
                
                if local_full and remote_full:
                    file_comp = self.compare_files(local_full, remote_full, normalized_path)
                elif local_rel:
                    file_comp = FileComparison(
                        local_path=local_path / local_rel,
                        remote_path=None,
                        status=ComparisonStatus.ONLY_LOCAL
                    )
                else:
                    file_comp = FileComparison(
                        local_path=None,
                        remote_path=remote_path / remote_rel if remote_rel else None,
                        status=ComparisonStatus.ONLY_REMOTE
                    )
            
            result.files[str(normalized_path)] = file_comp
            
            # Update counts
            if file_comp.status == ComparisonStatus.IDENTICAL:
                result.identical_count += 1
            elif file_comp.status == ComparisonStatus.DIFFERENT:
                result.different_count += 1
            elif file_comp.status == ComparisonStatus.ONLY_LOCAL:
                result.only_local_count += 1
            elif file_comp.status == ComparisonStatus.ONLY_REMOTE:
                result.only_remote_count += 1
        
        result.total_files = len(result.files)
        result.moved_blocks = moved_blocks
        return result
    
    def format_output(self, result: ComparisonResult, show_diffs: bool = False,
                     max_diff_lines: int = 50) -> str:
        """
        Format comparison result as human-readable output.
        
        Args:
            result: ComparisonResult to format
            show_diffs: Whether to show diff content
            max_diff_lines: Maximum diff lines to show per file
        
        Returns:
            Formatted string
        """
        lines = []
        lines.append("=" * 60)
        lines.append("📊 Comparison Results")
        lines.append("=" * 60)
        lines.append(f"Local:  {result.local_path}")
        lines.append(f"Remote: {result.remote_path}")
        lines.append("")
        
        # Summary
        lines.append("Summary:")
        lines.append(f"  Total files: {result.total_files}")
        lines.append(f"  Identical: {result.identical_count}")
        lines.append(f"  Different: {result.different_count}")
        lines.append(f"  Only in local: {result.only_local_count}")
        lines.append(f"  Only in remote: {result.only_remote_count}")
        lines.append(f"  Moved/renamed: {result.moved_count}")
        lines.append("")
        
        # Different files
        if result.different_count > 0:
            lines.append("Different files:")
            for rel_path, file_comp in result.files.items():
                if file_comp.status == ComparisonStatus.DIFFERENT:
                    lines.append(f"  - {rel_path} (similarity: {file_comp.similarity:.2%})")
                    if show_diffs and file_comp.diff_lines:
                        diff_preview = file_comp.diff_lines[:max_diff_lines]
                        lines.extend([f"    {line.rstrip()}" for line in diff_preview])
                        if len(file_comp.diff_lines) > max_diff_lines:
                            lines.append(f"    ... ({len(file_comp.diff_lines) - max_diff_lines} more lines)")
            lines.append("")
        
        # Files only in local
        if result.only_local_count > 0:
            lines.append("Files only in local:")
            for rel_path, file_comp in result.files.items():
                if file_comp.status == ComparisonStatus.ONLY_LOCAL:
                    lines.append(f"  - {rel_path}")
            lines.append("")
        
        # Files only in remote
        if result.only_remote_count > 0:
            lines.append("Files only in remote:")
            for rel_path, file_comp in result.files.items():
                if file_comp.status == ComparisonStatus.ONLY_REMOTE:
                    lines.append(f"  - {rel_path}")
            lines.append("")
        
        # Moved files
        if result.moved_count > 0:
            lines.append("Moved files:")
            for rel_path, file_comp in result.files.items():
                if file_comp.status == ComparisonStatus.MOVED and file_comp.moved_from:
                    lines.append(f"  - {rel_path} (moved from {file_comp.moved_from})")
            lines.append("")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
