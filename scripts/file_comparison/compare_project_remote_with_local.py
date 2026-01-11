#!/usr/bin/env python3
"""
Compare local project code with remote code.
Supports both Lambda functions and GAS projects.
"""

import argparse
import sys
import tempfile
from pathlib import Path
from typing import Optional

# Handle both module and standalone execution
try:
    from ..remote_sync.aws_lambda_fetcher import AWSLambdaFetcher
    from ..remote_sync.gas_fetcher import GASFetcher
    from .unified_comparison import UnifiedComparison
except ImportError:
    # Standalone execution - add parent directory to path
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    sys.path.insert(0, str(repo_root))
    
    from scripts.remote_sync.aws_lambda_fetcher import AWSLambdaFetcher
    from scripts.remote_sync.gas_fetcher import GASFetcher
    from scripts.file_comparison.unified_comparison import UnifiedComparison


def detect_project_type(local_path: Path) -> str:
    """
    Detect project type from local path.
    
    Returns:
        "lambda" or "gas"
    """
    # Check if it's a Lambda function
    if (local_path / "lambda_function.py").exists():
        return "lambda"
    
    # Check if it's a GAS project
    if (local_path / ".clasp.json").exists():
        return "gas"
    
    # Check parent directories
    parent = local_path.parent
    if parent.name == "lambda-functions" or "lambda" in str(local_path).lower():
        return "lambda"
    if "GoogleAppsScripts" in str(local_path) or "gas" in str(local_path).lower():
        return "gas"
    
    # Default to lambda for Python projects
    if any(local_path.glob("*.py")):
        return "lambda"
    
    # Default to gas for JS projects
    if any(local_path.glob("*.js")) or any(local_path.glob("*.gs")):
        return "gas"
    
    return "lambda"  # Default


def main():
    parser = argparse.ArgumentParser(
        description='Compare local project code with remote code',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Lambda function
  %(prog)s --local-path lambda-functions/MoveInventoryLambda
  
  # GAS project
  %(prog)s --local-path GoogleAppsScripts/projects/waitlist-script-comprehensive
  
  # With options
  %(prog)s --local-path path/to/project --show-diffs --keep-temp
        """
    )
    
    parser.add_argument(
        '--local-path',
        type=Path,
        required=True,
        help='Path to local project directory'
    )
    parser.add_argument(
        '--project-type',
        choices=['auto', 'lambda', 'gas'],
        default='auto',
        help='Project type (default: auto-detect)'
    )
    parser.add_argument(
        '--identifier',
        type=str,
        help='Project/function identifier (default: directory name)'
    )
    parser.add_argument(
        '--show-diffs',
        action='store_true',
        help='Show diff content for different files'
    )
    parser.add_argument(
        '--max-diff-lines',
        type=int,
        default=50,
        help='Maximum diff lines to show per file (default: 50)'
    )
    parser.add_argument(
        '--keep-temp',
        action='store_true',
        help='Keep temporary directory after comparison'
    )
    parser.add_argument(
        '--language',
        choices=['auto', 'python', 'javascript'],
        default='auto',
        help='Language for comparison (default: auto-detect)'
    )
    
    args = parser.parse_args()
    
    # Validate local path
    if not args.local_path.exists():
        print(f"❌ Local path does not exist: {args.local_path}", file=sys.stderr)
        sys.exit(1)
    
    if not args.local_path.is_dir():
        print(f"❌ Local path is not a directory: {args.local_path}", file=sys.stderr)
        sys.exit(1)
    
    # Detect project type
    project_type = args.project_type
    if project_type == 'auto':
        project_type = detect_project_type(args.local_path)
    
    # Get identifier
    identifier = args.identifier or args.local_path.name
    
    # Create fetcher
    if project_type == 'lambda':
        fetcher = AWSLambdaFetcher()
        if not fetcher.check_credentials():
            print("❌ AWS credentials not configured", file=sys.stderr)
            print("   Run: aws configure or aws sso login", file=sys.stderr)
            sys.exit(1)
    elif project_type == 'gas':
        fetcher = GASFetcher()
        if not fetcher.check_credentials():
            print("❌ clasp not installed or not authenticated", file=sys.stderr)
            print("   Run: npm install -g @google/clasp && clasp login", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"❌ Unknown project type: {project_type}", file=sys.stderr)
        sys.exit(1)
    
    # Create temp directory
    temp_dir = Path(tempfile.mkdtemp(prefix='compare_remote_'))
    
    try:
        # Fetch remote code
        print(f"📥 Fetching remote code for {identifier}...")
        remote_path = fetcher.fetch(identifier, temp_dir)
        print(f"✅ Remote code fetched to: {remote_path}")
        
        # Prepare local path
        # For GAS projects with esbuild, we need to compare build/ directory
        # For Lambda, compare the directory as-is
        local_compare_path = args.local_path
        if project_type == 'gas':
            # Check if project uses esbuild
            build_dir = args.local_path / "build"
            if build_dir.exists():
                local_compare_path = build_dir
                print(f"📦 Using build directory for comparison: {build_dir}")
        
        # Create comparison engine
        comparator = UnifiedComparison(language=args.language)
        
        # Compare
        print(f"\n🔍 Comparing local vs remote...")
        print(f"   Local:  {local_compare_path}")
        print(f"   Remote: {remote_path}")
        print()
        
        result = comparator.compare_directories(local_compare_path, remote_path)
        
        # Format and print output
        output = comparator.format_output(
            result,
            show_diffs=args.show_diffs,
            max_diff_lines=args.max_diff_lines
        )
        print(output)
        
        # Print output in format expected by bash scripts
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
        
        # Exit code
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
    
    finally:
        # Cleanup temp directory
        if not args.keep_temp and temp_dir.exists():
            import shutil
            shutil.rmtree(temp_dir)
        elif args.keep_temp:
            print(f"\n📁 Temporary directory kept: {temp_dir}")


if __name__ == '__main__':
    main()
