#!/usr/bin/env python3
"""
Main entry point for comparing local project code with remote code.
Takes remote_origin_type (google/aws) and project_name as parameters.
"""

import argparse
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional

from .fetchers import fetch_from_remote, check_credentials
from .comparison_logic import compare_directories, ComparisonResult
from .formatters import display_comparison_result


def compare_project_remote_with_local(
    remote_origin_type: str,
    project_name: str,
    local_path: Optional[Path] = None,
    show_diffs: bool = False,
    keep_temp: bool = False,
    max_diff_lines: int = 50,
    output_format: str = "text",
    **kwargs
) -> ComparisonResult:
    """
    Compare local project code with remote code.
    
    Args:
        remote_origin_type: "google" or "aws"
        project_name: Name of the project/function
        local_path: Path to local project directory (auto-detected if None)
        show_diffs: Whether to include diff content in output
        keep_temp: Whether to keep temporary directory after comparison
        max_diff_lines: Maximum diff lines to show per file
        output_format: Output format ("text" or "json")
        **kwargs: Additional arguments (region, project_root, etc.)
    
    Returns:
        ComparisonResult with all file comparisons
    
    Raises:
        ValueError: If remote_origin_type is unknown or local_path is invalid
        RuntimeError: If fetch or comparison fails
    """
    if remote_origin_type not in ("google", "aws"):
        raise ValueError(f"remote_origin_type must be 'google' or 'aws', got: {remote_origin_type}")
    
    # Auto-detect local_path if not provided
    if local_path is None:
        script_dir = Path(__file__).parent
        repo_root = script_dir.parent.parent
        
        if remote_origin_type == "aws":
            local_path = repo_root / "lambda" / "functions" / project_name
        else:  # google
            local_path = repo_root / "GoogleAppsScripts" / "projects" / project_name
    
    if not local_path.exists():
        raise ValueError(f"Local path does not exist: {local_path}")
    
    if not local_path.is_dir():
        raise ValueError(f"Local path is not a directory: {local_path}")
    
    # Check credentials
    if not check_credentials(remote_origin_type):
        if remote_origin_type == "aws":
            raise RuntimeError("AWS credentials not configured. Run: aws configure (or aws sso login / assume bars)")
        else:
            raise RuntimeError("clasp not installed or not authenticated. Run: clasp login")
    
    # Create temp directory for remote code
    temp_dir = Path(tempfile.mkdtemp(prefix=f'{remote_origin_type}_compare_'))
    
    try:
        # Fetch remote code
        remote_path = fetch_from_remote(
            remote_origin_type=remote_origin_type,
            project_name=project_name,
            temp_dir=temp_dir,
            **kwargs
        )
        
        # Determine local compare path (handle build/ directories for GAS)
        local_compare_path = local_path
        if remote_origin_type == "google":
            build_dir = local_path / "build"
            if build_dir.exists():
                local_compare_path = build_dir
        
        # Compare directories
        result = compare_directories(
            local_path=local_compare_path,
            remote_path=remote_path,
            remote_origin_type=remote_origin_type
        )
        
        # Display results (unless JSON output requested)
        if output_format != 'json':
            display_comparison_result(
                result,
                show_diffs=show_diffs,
                max_diff_lines=max_diff_lines
            )
        
        return result
    
    finally:
        # Cleanup temp directory
        if not keep_temp and temp_dir.exists():
            shutil.rmtree(temp_dir)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Compare local project code with remote code',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Lambda function
  %(prog)s --remote-origin-type aws --project-name MoveInventoryLambda
  
  # GAS project
  %(prog)s --remote-origin-type google --project-name waitlist-script-comprehensive
  
  # With explicit local path
  %(prog)s --remote-origin-type aws --project-name MoveInventoryLambda --local-path lambda/functions/MoveInventoryLambda
        """
    )
    
    parser.add_argument('--remote-origin-type', choices=['google', 'aws'], required=True,
                       help='Remote origin type: google or aws')
    parser.add_argument('--project-name', type=str, required=True,
                       help='Name of the project/function')
    parser.add_argument('--local-path', type=Path,
                       help='Path to local project directory (auto-detected if not provided)')
    parser.add_argument('--show-diffs', action='store_true',
                       help='Show diff content for different files')
    parser.add_argument('--max-diff-lines', type=int, default=50,
                       help='Maximum diff lines to show per file (default: 50)')
    parser.add_argument('--keep-temp', action='store_true',
                       help='Keep temporary directory after comparison')
    parser.add_argument('--region', type=str, default='us-east-1',
                       help='AWS region (default: us-east-1, only for aws)')
    parser.add_argument('--project-root', type=Path,
                       help='Root directory of GAS projects (default: auto-detect, only for google)')
    parser.add_argument('--output-format', choices=['text', 'json'], default='text',
                       help='Output format: text (human-readable) or json (structured data)')
    
    args = parser.parse_args()
    
    try:
        kwargs = {}
        if args.remote_origin_type == "aws":
            kwargs["region"] = args.region
        else:  # google
            if args.project_root:
                kwargs["project_root"] = args.project_root
        
        result = compare_project_remote_with_local(
            remote_origin_type=args.remote_origin_type,
            project_name=args.project_name,
            local_path=args.local_path,
            show_diffs=args.show_diffs,
            keep_temp=args.keep_temp,
            max_diff_lines=args.max_diff_lines,
            output_format=args.output_format,
            **kwargs
        )
        
        # Output JSON if requested
        if args.output_format == 'json':
            import json
            from dataclasses import asdict
            json_output = {
                'different_count': result.different_count,
                'only_local_count': result.only_local_count,
                'only_remote_count': result.only_remote_count,
                'identical_count': result.identical_count,
                'total_files': result.total_files,
                'remote_ahead': result.only_remote_count > 0,
                'local_ahead': result.only_local_count > 0,
                'has_changes': (
                    result.different_count > 0 or
                    result.only_local_count > 0 or
                    result.only_remote_count > 0
                )
            }
            print(json.dumps(json_output, indent=2))
            sys.exit(0)
        
        # Exit with error code if differences found (text mode)
        if result.different_count > 0 or result.only_local_count > 0 or result.only_remote_count > 0:
            sys.exit(1)
        else:
            print("\n✅ No differences detected")
            sys.exit(0)
    
    except Exception as e:
        print(f"❌ Error during comparison: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
