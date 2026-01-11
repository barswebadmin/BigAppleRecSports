#!/usr/bin/env python3
"""
Python-specific code comparator.
Handles Python code normalization and comparison.
"""

import ast
import difflib
from pathlib import Path
from typing import List, Tuple


class PythonComparator:
    """Comparator for Python code files."""
    
    def __init__(self, ignore_whitespace: bool = True, ignore_comments: bool = False,
                 ignore_blank_lines: bool = False):
        """
        Initialize Python comparator.
        
        Args:
            ignore_whitespace: Ignore whitespace differences
            ignore_comments: Ignore comment differences
            ignore_blank_lines: Ignore blank line differences
        """
        self.ignore_whitespace = ignore_whitespace
        self.ignore_comments = ignore_comments
        self.ignore_blank_lines = ignore_blank_lines
    
    def normalize_code(self, code: str) -> str:
        """
        Normalize Python code for comparison.
        
        Args:
            code: Python source code
        
        Returns:
            Normalized code string
        """
        lines = code.splitlines()
        normalized_lines = []
        
        for line in lines:
            # Remove comments if requested
            if self.ignore_comments:
                # Remove inline comments (but preserve strings)
                if '#' in line:
                    # Simple approach: split on # and take first part
                    # This doesn't handle # in strings, but is good enough
                    comment_pos = line.find('#')
                    if comment_pos >= 0:
                        # Check if # is in a string
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
            
            # Normalize whitespace if requested
            if self.ignore_whitespace:
                line = ' '.join(line.split())
            
            # Skip blank lines if requested
            if self.ignore_blank_lines and not line.strip():
                continue
            
            normalized_lines.append(line)
        
        return '\n'.join(normalized_lines)
    
    def compare_files(self, local_path: Path, remote_path: Path) -> Tuple[bool, List[str], float]:
        """
        Compare two Python files.
        
        Args:
            local_path: Path to local file
            remote_path: Path to remote file
        
        Returns:
            Tuple of (identical, diff_lines, similarity)
        """
        try:
            local_content = local_path.read_text(errors='replace')
            remote_content = remote_path.read_text(errors='replace')
        except Exception as e:
            # If we can't read, fall back to simple comparison
            return False, [f"Error reading files: {e}"], 0.0
        
        # Normalize both files
        local_normalized = self.normalize_code(local_content)
        remote_normalized = self.normalize_code(remote_content)
        
        # Check if identical
        identical = local_normalized == remote_normalized
        
        # Calculate similarity
        similarity = difflib.SequenceMatcher(
            None, remote_normalized, local_normalized
        ).ratio()
        
        # Generate diff
        if identical:
            diff_lines = []
        else:
            # Use original content for diff (not normalized) for readability
            diff_lines = list(difflib.unified_diff(
                remote_content.splitlines(keepends=True),
                local_content.splitlines(keepends=True),
                fromfile=str(remote_path),
                tofile=str(local_path),
                lineterm=''
            ))
        
        return identical, diff_lines, similarity
