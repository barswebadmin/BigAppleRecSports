#!/usr/bin/env python3
"""
All comparison logic organized by section.
Handles file comparison, code block detection, and move detection.
"""

import difflib
import hashlib
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Ensure the directory containing this file is on sys.path so sibling modules resolve
sys.path.insert(0, str(Path(__file__).parent))

from _file_helpers import (
    discover_files, normalize_extension, find_matching_files,
    get_files_only_in_path, read_file_lines
)
from _code_block_mover import CodeBlockMoveDetector, MovedBlock


# Data Classes

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
    moved_blocks: List[MovedBlock] = field(default_factory=list)


# AWS Comparison

def compare_aws_directories(
    local_path: Path,
    remote_path: Path,
    exclude_patterns: Optional[List[str]] = None
) -> ComparisonResult:
    """
    Compare Lambda function directories with AWS-specific logic.
    
    Args:
        local_path: Path to local Lambda function directory
        remote_path: Path to remote Lambda function directory
        exclude_patterns: Patterns to exclude from comparison
    
    Returns:
        ComparisonResult with all file comparisons
    """
    aws_exclude_patterns = exclude_patterns or []
    aws_exclude_patterns.extend([
        '__pycache__', '*.pyc', '*.pyo', '.git', 'node_modules',
        '.DS_Store', '*.egg-info', 'dist/', 'build/'
    ])
    comparator = UnifiedComparison(language="auto")
    return comparator.compare_directories(local_path, remote_path, exclude_patterns=aws_exclude_patterns)


# Google Comparison

def compare_google_directories(
    local_path: Path,
    remote_path: Path,
    exclude_patterns: Optional[List[str]] = None
) -> ComparisonResult:
    """
    Compare GAS project directories with Google-specific logic.
    
    Args:
        local_path: Path to local GAS project directory
        remote_path: Path to remote GAS project directory
        exclude_patterns: Patterns to exclude from comparison
    
    Returns:
        ComparisonResult with all file comparisons
    """
    gas_exclude_patterns = exclude_patterns or []
    gas_exclude_patterns.extend([
        '.clasp.json', '.clasp_*', 'node_modules', '.git',
        '.DS_Store', 'package-lock.json', 'package.json'
    ])
    comparator = UnifiedComparison(language="auto")
    return comparator.compare_directories(local_path, remote_path, exclude_patterns=gas_exclude_patterns)


# Unified Comparison Engine

def compare_directories(
    local_path: Path,
    remote_path: Path,
    remote_origin_type: str,
    exclude_patterns: Optional[List[str]] = None
) -> ComparisonResult:
    """
    Main comparison dispatcher.
    
    Args:
        local_path: Path to local directory
        remote_path: Path to remote directory
        remote_origin_type: "google" or "aws"
        exclude_patterns: Patterns to exclude from comparison
    
    Returns:
        ComparisonResult with all file comparisons
    
    Raises:
        ValueError: If remote_origin_type is unknown
    """
    if remote_origin_type == "aws":
        return compare_aws_directories(local_path, remote_path, exclude_patterns)
    elif remote_origin_type == "google":
        return compare_google_directories(local_path, remote_path, exclude_patterns)
    else:
        raise ValueError(f"Unknown remote origin type: {remote_origin_type}")


class PythonComparator:
    """Comparator for Python code files."""
    
    def __init__(self, ignore_whitespace: bool = True, ignore_comments: bool = False,
                 ignore_blank_lines: bool = False):
        self.ignore_whitespace = ignore_whitespace
        self.ignore_comments = ignore_comments
        self.ignore_blank_lines = ignore_blank_lines
    
    def normalize_code(self, code: str) -> str:
        """Normalize Python code for comparison."""
        lines = code.splitlines()
        normalized_lines = []
        
        for line in lines:
            if self.ignore_comments:
                if '#' in line:
                    comment_pos = line.find('#')
                    if comment_pos >= 0:
                        in_string = False
                        quote_char = None
                        for i, char in enumerate(line[:comment_pos]):
                            if char in ('"', "'") and (i == 0 or line[i-1] != '\\'):
                                if not in_string:
                                    in_string = True
                                    quote_char = char
                                elif char == quote_char:
                                    in_string = False
                                    quote_char = None
                        
                        if not in_string:
                            line = line[:comment_pos].rstrip()
            
            if self.ignore_whitespace:
                line = ' '.join(line.split())
            
            if self.ignore_blank_lines and not line.strip():
                continue
            
            normalized_lines.append(line)
        
        return '\n'.join(normalized_lines)
    
    def compare_files(self, local_path: Path, remote_path: Path) -> Tuple[bool, List[str], float]:
        """Compare two Python files."""
        try:
            local_content = local_path.read_text(errors='replace')
            remote_content = remote_path.read_text(errors='replace')
        except Exception as e:
            return False, [f"Error reading files: {e}"], 0.0
        
        local_normalized = self.normalize_code(local_content)
        remote_normalized = self.normalize_code(remote_content)
        
        identical = local_normalized == remote_normalized
        
        similarity = difflib.SequenceMatcher(
            None, remote_normalized, local_normalized
        ).ratio()
        
        if identical:
            diff_lines = []
        else:
            diff_lines = list(difflib.unified_diff(
                remote_content.splitlines(keepends=True),
                local_content.splitlines(keepends=True),
                fromfile=str(remote_path),
                tofile=str(local_path),
                lineterm=''
            ))
        
        return identical, diff_lines, similarity


class JavaScriptComparator:
    """Comparator for JavaScript code files."""
    
    def __init__(self, ignore_whitespace: bool = True, ignore_comments: bool = False,
                 ignore_blank_lines: bool = False):
        self.ignore_whitespace = ignore_whitespace
        self.ignore_comments = ignore_comments
        self.ignore_blank_lines = ignore_blank_lines
    
    def normalize_code(self, code: str) -> str:
        """Normalize JavaScript code for comparison."""
        lines = code.splitlines()
        normalized_lines = []
        
        for line in lines:
            if self.ignore_comments:
                if '//' in line:
                    in_string = False
                    quote_char = None
                    comment_pos = line.find('//')
                    
                    for i, char in enumerate(line[:comment_pos]):
                        if char in ('"', "'", '`') and (i == 0 or line[i-1] != '\\'):
                            if not in_string:
                                in_string = True
                                quote_char = char
                            elif char == quote_char:
                                in_string = False
                                quote_char = None
                    
                    if not in_string:
                        line = line[:comment_pos].rstrip()
                
                line = re.sub(r'/\*.*?\*/', '', line, flags=re.DOTALL)
            
            if self.ignore_whitespace:
                line = re.sub(r'\s+', ' ', line).strip()
            
            if self.ignore_blank_lines and not line.strip():
                continue
            
            normalized_lines.append(line)
        
        return '\n'.join(normalized_lines)
    
    def compare_files(self, local_path: Path, remote_path: Path) -> Tuple[bool, List[str], float]:
        """Compare two JavaScript files."""
        try:
            local_content = local_path.read_text(errors='replace')
            remote_content = remote_path.read_text(errors='replace')
        except Exception as e:
            return False, [f"Error reading files: {e}"], 0.0
        
        local_normalized = self.normalize_code(local_content)
        remote_normalized = self.normalize_code(remote_content)
        
        identical = local_normalized == remote_normalized
        
        similarity = difflib.SequenceMatcher(
            None, remote_normalized, local_normalized
        ).ratio()
        
        if identical:
            diff_lines = []
        else:
            diff_lines = list(difflib.unified_diff(
                remote_content.splitlines(keepends=True),
                local_content.splitlines(keepends=True),
                fromfile=str(remote_path),
                tofile=str(local_path),
                lineterm=''
            ))
        
        return identical, diff_lines, similarity


class UnifiedComparison:
    """Unified comparison engine for code files."""
    
    def __init__(self, language: str = "auto", ignore_whitespace: bool = True, 
                 ignore_comments: bool = False, ignore_blank_lines: bool = False,
                 detect_code_block_moves: bool = True, min_block_size: int = 3):
        self.language = language
        self.ignore_whitespace = ignore_whitespace
        self.ignore_comments = ignore_comments
        self.ignore_blank_lines = ignore_blank_lines
        self.detect_code_block_moves = detect_code_block_moves
        self.min_block_size = min_block_size
        
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
        """Discover all files in a directory."""
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
        """Compare two files."""
        if not local_path.exists() and not remote_path.exists():
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
        
        language = self.language
        if language == "auto":
            language = self.detect_language(local_path)
        
        if language == "python":
            comparator = self.python_comparator
        elif language == "javascript":
            comparator = self.javascript_comparator
        else:
            comparator = None
        
        if comparator:
            identical, diff_lines, similarity = comparator.compare_files(local_path, remote_path)
        else:
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
        """Detect files that were moved/renamed by comparing content hashes."""
        moved = {}
        
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
        
        for file_hash, local_rel in local_hashes.items():
            if file_hash in remote_hashes:
                remote_rel = remote_hashes[file_hash]
                if local_rel != remote_rel:
                    if local_rel not in remote_files and remote_rel not in local_files:
                        moved[local_rel] = remote_rel
        
        return moved
    
    def compare_directories(self, local_path: Path, remote_path: Path,
                           exclude_patterns: Optional[List[str]] = None) -> ComparisonResult:
        """Compare two directories with optional code block move detection."""
        exclude_patterns = exclude_patterns or [
            '__pycache__', '*.pyc', '*.pyo', '.git', 'node_modules',
            '.clasp.json', '.clasp_*', 'build/', '.DS_Store'
        ]
        
        local_files = self.discover_files(local_path, exclude_patterns)
        remote_files = self.discover_files(remote_path, exclude_patterns)
        
        local_files_normalized = {self.normalize_extension(f): f for f in local_files}
        remote_files_normalized = {self.normalize_extension(f): f for f in remote_files}
        
        moved = self.detect_moved_files(
            set(local_files_normalized.keys()),
            set(remote_files_normalized.keys()),
            local_path,
            remote_path
        )
        
        matching_file_pairs = find_matching_files(local_path, remote_path, exclude_patterns)
        files_only_local = get_files_only_in_path(local_path, remote_path, exclude_patterns)
        files_only_remote = get_files_only_in_path(remote_path, local_path, exclude_patterns)
        
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
        
        result = ComparisonResult(local_path=local_path, remote_path=remote_path)
        all_files = set(local_files_normalized.keys()) | set(remote_files_normalized.keys())
        
        for normalized_path in sorted(all_files):
            local_rel = local_files_normalized.get(normalized_path)
            remote_rel = remote_files_normalized.get(normalized_path)
            
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
