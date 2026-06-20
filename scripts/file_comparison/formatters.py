#!/usr/bin/env python3
"""
All formatting and display logic for comparison results.
Handles text and JSON output formatting.
"""

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent))

from comparison_logic import ComparisonResult, FileComparison, ComparisonStatus


def format_comparison_result(
    result: ComparisonResult,
    show_diffs: bool = False,
    max_diff_lines: int = 50,
    output_format: str = "text"
) -> str:
    """
    Format ComparisonResult as string.
    
    Args:
        result: ComparisonResult to format
        show_diffs: Whether to include diff content in output
        max_diff_lines: Maximum diff lines to show per file
        output_format: "text" or "json"
    
    Returns:
        Formatted string representation
    """
    if output_format == "json":
        return format_as_json(result)
    else:
        return format_as_text(result, show_diffs, max_diff_lines)


def format_as_text(
    result: ComparisonResult,
    show_diffs: bool = False,
    max_diff_lines: int = 50
) -> str:
    """
    Format as human-readable text.
    
    Args:
        result: ComparisonResult to format
        show_diffs: Whether to include diff content
        max_diff_lines: Maximum diff lines to show per file
    
    Returns:
        Formatted text string
    """
    lines = []
    lines.append("=" * 60)
    lines.append("📊 Comparison Results")
    lines.append("=" * 60)
    lines.append(f"Local:  {result.local_path}")
    lines.append(f"Remote: {result.remote_path}")
    lines.append("")
    
    lines.append("Summary:")
    lines.append(f"  Total files: {result.total_files}")
    lines.append(f"  Identical: {result.identical_count}")
    lines.append(f"  Different: {result.different_count}")
    lines.append(f"  Only in local: {result.only_local_count}")
    lines.append(f"  Only in remote: {result.only_remote_count}")
    lines.append(f"  Moved/renamed: {result.moved_count}")
    lines.append("")
    
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
    
    if result.only_local_count > 0:
        lines.append("Files only in local:")
        for rel_path, file_comp in result.files.items():
            if file_comp.status == ComparisonStatus.ONLY_LOCAL:
                lines.append(f"  - {rel_path}")
        lines.append("")
    
    if result.only_remote_count > 0:
        lines.append("Files only in remote:")
        for rel_path, file_comp in result.files.items():
            if file_comp.status == ComparisonStatus.ONLY_REMOTE:
                lines.append(f"  - {rel_path}")
        lines.append("")
    
    if result.moved_count > 0:
        lines.append("Moved files:")
        for rel_path, file_comp in result.files.items():
            if file_comp.status == ComparisonStatus.MOVED and file_comp.moved_from:
                lines.append(f"  - {rel_path} (moved from {file_comp.moved_from})")
        lines.append("")
    
    lines.append("=" * 60)
    
    return "\n".join(lines)


def format_as_json(result: ComparisonResult) -> str:
    """
    Format as JSON.
    
    Args:
        result: ComparisonResult to format
    
    Returns:
        JSON string representation
    """
    output = {
        'summary': {
            'total_files': result.total_files,
            'identical': result.identical_count,
            'different': result.different_count,
            'only_local': result.only_local_count,
            'only_remote': result.only_remote_count,
            'moved_files': result.moved_count,
            'moved_blocks': len(result.moved_blocks)
        },
        'files': {k: {
            'status': v.status.value,
            'similarity': v.similarity,
            'moved_from': str(v.moved_from) if v.moved_from else None
        } for k, v in result.files.items()},
        'moved_blocks': [
            {
                'source_file': str(move.source_file),
                'target_file': str(move.target_file),
                'source_lines': move.source_lines,
                'target_lines': move.target_lines,
                'similarity': move.similarity
            }
            for move in result.moved_blocks
        ]
    }
    return json.dumps(output, indent=2)


def display_comparison_result(
    result: ComparisonResult,
    show_diffs: bool = False,
    max_diff_lines: int = 50
) -> None:
    """
    Print formatted result to stdout.
    
    Args:
        result: ComparisonResult to display
        show_diffs: Whether to include diff content
        max_diff_lines: Maximum diff lines to show per file
    """
    output = format_comparison_result(result, show_diffs, max_diff_lines)
    print(output)
    
    # Print structured output for shell scripts
    if result.different_count > 0:
        print("\nDifferent files:")
        for rel_path, file_comp in result.files.items():
            if file_comp.status.value == "different":
                print(f"  - {rel_path}")
    
    if result.only_local_count > 0:
        print("\nFiles only in local:")
        for rel_path, file_comp in result.files.items():
            if file_comp.status.value == "only_local":
                print(f"  - {rel_path}")
    
    if result.only_remote_count > 0:
        print("\nFiles only in remote:")
        for rel_path, file_comp in result.files.items():
            if file_comp.status.value == "only_remote":
                print(f"  - {rel_path}")
