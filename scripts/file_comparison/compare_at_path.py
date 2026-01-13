#!/usr/bin/env python3
"""
Compare two directory paths and detect moved code blocks.
Compares two directory paths and detects moved code blocks.
"""

import argparse
from pathlib import Path

from .comparison_logic import UnifiedComparison, ComparisonResult, MovedBlock
from .formatters import format_comparison_result


def format_output(result: ComparisonResult, output_format: str = 'text') -> str:
    """Format comparison result with code block moves."""
    if output_format == 'json':
        import json
        from dataclasses import asdict
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
                'similarity': v.similarity
            } for k, v in result.files.items()},
            'moved_blocks': [asdict(move) for move in result.moved_blocks]
        }
        return json.dumps(output, indent=2)
    
    lines = []
    lines.append("=" * 80)
    lines.append("📊 File Comparison Summary")
    lines.append("=" * 80)
    lines.append(f"Local:  {result.local_path}")
    lines.append(f"Remote: {result.remote_path}")
    lines.append("")
    
    lines.append("Summary:")
    lines.append(f"  Total files: {result.total_files}")
    lines.append(f"  ✅ Identical: {result.identical_count}")
    if result.different_count > 0:
        lines.append(f"  ❌ Different: {result.different_count}")
    else:
        lines.append(f"  ✅ Different: {result.different_count}")
    
    if result.only_local_count > 0:
        lines.append(f"  ⚠️  Only in local: {result.only_local_count}")
    else:
        lines.append(f"  ✅ Only in local: {result.only_local_count}")
    
    if result.only_remote_count > 0:
        lines.append(f"  ⚠️  Only in remote: {result.only_remote_count}")
    else:
        lines.append(f"  ✅ Only in remote: {result.only_remote_count}")
    
    if result.moved_count > 0:
        lines.append(f"  📦 Moved files: {result.moved_count}")
    else:
        lines.append(f"  ✅ Moved files: {result.moved_count}")
    
    if result.moved_blocks:
        lines.append(f"  🔍 Moved code blocks: {len(result.moved_blocks)}")
    else:
        lines.append(f"  ✅ Moved code blocks: 0")
    
    lines.append("")
    
    if result.different_count > 0:
        lines.append("❌ Different files:")
        for rel_path, file_comp in result.files.items():
            if file_comp.status.value == 'different':
                lines.append(f"  • {rel_path} (similarity: {file_comp.similarity:.2%})")
        lines.append("")
    
    if result.only_local_count > 0:
        lines.append("⚠️  Files only in local:")
        for rel_path, file_comp in result.files.items():
            if file_comp.status.value == 'only_local':
                lines.append(f"  • {rel_path}")
        lines.append("")
    
    if result.only_remote_count > 0:
        lines.append("⚠️  Files only in remote:")
        for rel_path, file_comp in result.files.items():
            if file_comp.status.value == 'only_remote':
                lines.append(f"  • {rel_path}")
        lines.append("")
    
    if result.moved_count > 0:
        lines.append("📦 Moved files:")
        for rel_path, file_comp in result.files.items():
            if file_comp.status.value == 'moved' and file_comp.moved_from:
                lines.append(f"  • {rel_path} (moved from {file_comp.moved_from})")
        lines.append("")
    
    if result.moved_blocks:
        lines.append("🔍 Moved code blocks:")
        for i, move in enumerate(result.moved_blocks, 1):
            lines.append(f"  Move #{i}:")
            lines.append(f"    From: {move.source_file}:{move.source_line}")
            lines.append(f"    To:   {move.target_file}:{move.target_line}")
            code_preview = move.code.split('\n')[:5]
            if len(move.code.split('\n')) > 5:
                code_preview.append(f"... ({len(move.code.split('\n')) - 5} more lines)")
            lines.append(f"    Code: {code_preview[0]}")
            for line in code_preview[1:]:
                lines.append(f"           {line}")
            lines.append("")
    else:
        lines.append("✅ No moved code blocks detected.")
        lines.append("")
    
    lines.append("=" * 80)
    
    return "\n".join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Compare two directory paths and detect moved code blocks'
    )
    parser.add_argument('path1', type=Path, help='First path to compare')
    parser.add_argument('path2', type=Path, help='Second path to compare')
    parser.add_argument('--min-block-size', type=int, default=3,
                       help='Minimum lines in a block to consider (default: 3)')
    parser.add_argument('--filter-same-file', action='store_true',
                       help='Filter out moves within the same file')
    parser.add_argument('--output-format', choices=['text', 'json'],
                       default='text', help='Output format (default: text)')
    parser.add_argument('--no-code-block-moves', action='store_true',
                       help='Disable code block move detection')
    
    args = parser.parse_args()
    
    if not args.path1.exists():
        print(f"❌ Path 1 does not exist: {args.path1}")
        exit(1)
    
    if not args.path2.exists():
        print(f"❌ Path 2 does not exist: {args.path2}")
        exit(1)
    
    comparator = UnifiedComparison(
        language="auto",
        ignore_whitespace=True,
        ignore_comments=True,
        ignore_blank_lines=False,
        detect_code_block_moves=not args.no_code_block_moves,
        min_block_size=args.min_block_size
    )
    
    result = comparator.compare_directories(args.path1, args.path2)
    
    moves = result.moved_blocks
    if args.filter_same_file:
        moves = [
            move for move in moves
            if Path(move.source_file).resolve() != Path(move.target_file).resolve()
        ]
        result.moved_blocks = moves
    
    output = format_output(result, args.output_format)
    print(output)
