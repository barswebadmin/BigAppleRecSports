#!/usr/bin/env python3
"""
Code block move detection.
Detects moved code blocks within and across files.
"""

from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Set

try:
    from .file_helpers import read_file_lines, normalize_extension
except ImportError:
    import sys
    from pathlib import Path as PathType
    script_dir = PathType(__file__).parent
    repo_root = script_dir.parent.parent
    sys.path.insert(0, str(repo_root))
    from scripts.file_comparison.file_helpers import read_file_lines, normalize_extension


@dataclass
class CodeBlock:
    """Represents a code block that was deleted or added."""
    file_path: str
    start_line: int
    end_line: int
    code: str
    normalized_code: str


@dataclass
class MovedBlock:
    """Represents a detected moved code block."""
    code: str
    source_file: str
    source_line: int
    target_file: str
    target_line: int
    move_type: str = 'moved'
    similarity: float = 1.0


class CodeBlockMoveDetector:
    """Detect moved code blocks using file-level tracking."""
    
    def __init__(self, min_block_size: int = 3, filter_same_file: bool = False):
        """
        Initialize move detector.
        
        Args:
            min_block_size: Minimum lines in a block to consider (default: 3)
            filter_same_file: If True, filter out moves within the same file (default: False)
        """
        self.min_block_size = min_block_size
        self.filter_same_file = filter_same_file
        
        self.deletions: Dict[str, List[CodeBlock]] = {}
        self.additions: Dict[str, List[CodeBlock]] = {}
        self.path1: Optional[Path] = None
        self.path2: Optional[Path] = None
    
    def _normalize_code(self, lines: List[str]) -> str:
        """Normalize code for matching (strip comments, whitespace)."""
        normalized = []
        for line in lines:
            stripped = line.rstrip()
            if not stripped:
                continue
            stripped_line = stripped.lstrip()
            # Skip comments
            if stripped_line.startswith('#') or stripped_line.startswith('//'):
                continue
            normalized.append(stripped)
        return '\n'.join(normalized)
    
    def _create_code_block(self, file_path: Path, lines: List[str], 
                          start_line: int, end_line: int) -> Optional[CodeBlock]:
        """Create a CodeBlock if the content meets minimum size and normalization requirements."""
        if len(lines) < self.min_block_size:
            return None
        
        normalized = self._normalize_code(lines)
        if not normalized:
            return None
        
        return CodeBlock(
            file_path=str(file_path),
            start_line=start_line,
            end_line=end_line,
            code=''.join(lines),
            normalized_code=normalized
        )
    
    def _track_file_changes(self, file1_path: Path, file2_path: Path) -> None:
        """Track deletions and additions between two file versions."""
        lines1 = read_file_lines(file1_path)
        lines2 = read_file_lines(file2_path)
        
        if lines1 is None or lines2 is None:
            return
        
        matcher = SequenceMatcher(None, lines1, lines2, autojunk=False)
        opcodes = matcher.get_opcodes()
        
        file1_str = str(file1_path)
        file2_str = str(file2_path)
        
        if file1_str not in self.deletions:
            self.deletions[file1_str] = []
        if file2_str not in self.additions:
            self.additions[file2_str] = []
        
        for tag, i1, i2, j1, j2 in opcodes:
            if tag == 'delete':
                block = self._create_code_block(file1_path, lines1[i1:i2], i1 + 1, i2)
                if block:
                    self.deletions[file1_str].append(block)
            
            elif tag == 'insert':
                block = self._create_code_block(file2_path, lines2[j1:j2], j1 + 1, j2)
                if block:
                    self.additions[file2_str].append(block)
    
    def _track_orphaned_file(self, file_path: Path, blocks_dict: Dict[str, List[CodeBlock]]) -> None:
        """Track a file that only exists in one path."""
        lines = read_file_lines(file_path)
        if lines:
            block = self._create_code_block(file_path, lines, 1, len(lines))
            if block:
                blocks_dict[str(file_path)] = [block]
    
    def _is_same_relative_file(self, file1: str, file2: str) -> bool:
        """Check if two files have the same relative path structure."""
        if not self.path1 or not self.path2:
            return False
        
        try:
            file1_path = Path(file1).resolve()
            file2_path = Path(file2).resolve()
            
            try:
                rel1 = file1_path.relative_to(self.path1)
            except ValueError:
                try:
                    rel1 = file1_path.relative_to(self.path2)
                except ValueError:
                    return False
            
            try:
                rel2 = file2_path.relative_to(self.path1)
            except ValueError:
                try:
                    rel2 = file2_path.relative_to(self.path2)
                except ValueError:
                    return False
            
            return str(normalize_extension(rel1)) == str(normalize_extension(rel2))
        except Exception:
            return False
    
    def _match_moves(self) -> List[MovedBlock]:
        """Match additions to deletions to identify moves."""
        moves = []
        matched_additions: Set[tuple[str, int]] = set()
        
        for add_file, add_blocks in self.additions.items():
            for add_idx, add_block in enumerate(add_blocks):
                if (add_file, add_idx) in matched_additions:
                    continue
                
                for del_file, del_blocks in self.deletions.items():
                    for del_idx, del_block in enumerate(del_blocks):
                        if add_block.normalized_code == del_block.normalized_code:
                            if self.filter_same_file:
                                if self._is_same_relative_file(del_file, add_file):
                                    continue
                            
                            moves.append(MovedBlock(
                                code=add_block.code.strip(),
                                source_file=del_file,
                                source_line=del_block.start_line,
                                target_file=add_file,
                                target_line=add_block.start_line,
                                move_type='moved',
                                similarity=1.0
                            ))
                            
                            matched_additions.add((add_file, add_idx))
                            break
                    
                    if (add_file, add_idx) in matched_additions:
                        break
        
        return moves
    
    def detect_moves(self, matching_files: List[tuple[Path, Path]], 
                    path1: Path, path2: Path,
                    files_only_local: List[Path], files_only_remote: List[Path]) -> List[MovedBlock]:
        """
        Detect moved blocks between two paths.
        
        Args:
            matching_files: List of (file1_path, file2_path) tuples for files in both paths
            path1: First path (for relative path calculation)
            path2: Second path (for relative path calculation)
            files_only_local: Files only in path1
            files_only_remote: Files only in path2
            
        Returns:
            List of MovedBlock objects
        """
        self.path1 = path1
        self.path2 = path2
        
        # Track changes in matching files
        for file1_path, file2_path in matching_files:
            self._track_file_changes(file1_path, file2_path)
        
        # Track orphaned files
        for file_path in files_only_local:
            self._track_orphaned_file(file_path, self.deletions)
        
        for file_path in files_only_remote:
            self._track_orphaned_file(file_path, self.additions)
        
        return self._match_moves()
