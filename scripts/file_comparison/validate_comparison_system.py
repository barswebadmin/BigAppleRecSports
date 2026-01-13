#!/usr/bin/env python3
"""
Validation script for comparison system.
Compares local and remote code using fetchers, comparison logic, and formatters.
"""

import sys
from pathlib import Path
from typing import List
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from .compare_project_remote_with_local import compare_project_remote_with_local

REPO_ROOT = Path(__file__).parent.parent.parent
GAS_ROOT = REPO_ROOT / "GoogleAppsScripts"
PROJECTS_DIR = GAS_ROOT / "projects"
LAMBDA_FUNCTIONS_DIR = REPO_ROOT / "lambda" / "functions"


class ComparisonStatus(Enum):
    """Status of a comparison operation."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class ComparisonResult:
    """Result of comparing a single project/function."""
    name: str
    type: str
    status: ComparisonStatus
    has_changes: bool = False
    output: str = ""
    error: str = ""
    duration_seconds: float = 0.0
    timestamp: str = ""


def get_gas_projects() -> List[str]:
    """Get list of all GAS project directories."""
    if not PROJECTS_DIR.exists():
        return []
    
    projects = []
    for item in PROJECTS_DIR.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            if (item / ".clasp.json").exists():
                projects.append(item.name)
    
    return sorted(projects)


def get_lambda_functions() -> List[str]:
    """Get list of all Lambda function directories."""
    if not LAMBDA_FUNCTIONS_DIR.exists():
        return []
    
    functions = []
    for item in LAMBDA_FUNCTIONS_DIR.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            if (item / "lambda_function.py").exists():
                functions.append(item.name)
    
    return sorted(functions)


def validate_gas_project(project_name: str, verbose: bool = False) -> ComparisonResult:
    """Validate comparison for a single GAS project."""
    import time
    start_time = time.time()
    
    project_dir = PROJECTS_DIR / project_name
    
    if project_name == "waitlist-script-comprehensive":
        return ComparisonResult(
            name=project_name,
            type="gas",
            status=ComparisonStatus.SKIPPED,
            error="Uses custom workflow",
            timestamp=datetime.now().isoformat()
        )
    
    try:
        local_path = project_dir / "src"
        if not local_path.exists():
            return ComparisonResult(
                name=project_name,
                type="gas",
                status=ComparisonStatus.ERROR,
                error="src/ directory not found",
                timestamp=datetime.now().isoformat()
            )
        
        result = compare_project_remote_with_local(
            remote_origin_type="google",
            project_name=project_name,
            local_path=local_path,
            project_root=GAS_ROOT.parent
        )
        
        duration = time.time() - start_time
        
        has_changes = (
            result.different_count > 0 or
            result.only_local_count > 0 or
            result.only_remote_count > 0
        )
        
        from .formatters import format_comparison_result
        output = format_comparison_result(result)
        
        return ComparisonResult(
            name=project_name,
            type="gas",
            status=ComparisonStatus.SUCCESS,
            has_changes=has_changes,
            output=output,
            duration_seconds=duration,
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        duration = time.time() - start_time
        return ComparisonResult(
            name=project_name,
            type="gas",
            status=ComparisonStatus.ERROR,
            error=str(e),
            duration_seconds=duration,
            timestamp=datetime.now().isoformat()
        )


def validate_lambda_function(function_name: str, verbose: bool = False) -> ComparisonResult:
    """Validate comparison for a single Lambda function."""
    import time
    start_time = time.time()
    
    function_dir = LAMBDA_FUNCTIONS_DIR / function_name
    
    if not function_dir.exists():
        return ComparisonResult(
            name=function_name,
            type="lambda",
            status=ComparisonStatus.ERROR,
            error="Function directory not found",
            timestamp=datetime.now().isoformat()
        )
    
    try:
        result = compare_project_remote_with_local(
            remote_origin_type="aws",
            project_name=function_name,
            local_path=function_dir
        )
        
        duration = time.time() - start_time
        
        has_changes = (
            result.different_count > 0 or
            result.only_local_count > 0 or
            result.only_remote_count > 0
        )
        
        from .formatters import format_comparison_result
        output = format_comparison_result(result)
        
        return ComparisonResult(
            name=function_name,
            type="lambda",
            status=ComparisonStatus.SUCCESS,
            has_changes=has_changes,
            output=output,
            duration_seconds=duration,
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        duration = time.time() - start_time
        return ComparisonResult(
            name=function_name,
            type="lambda",
            status=ComparisonStatus.ERROR,
            error=str(e),
            duration_seconds=duration,
            timestamp=datetime.now().isoformat()
        )


def validate_all_gas_projects(verbose: bool = False) -> List[ComparisonResult]:
    """Validate all GAS projects."""
    projects = get_gas_projects()
    results = []
    
    print(f"🔍 Validating {len(projects)} GAS projects...")
    
    for i, project_name in enumerate(projects, 1):
        if verbose:
            print(f"\n[{i}/{len(projects)}] {project_name}")
        else:
            print(f"[{i}/{len(projects)}] {project_name}...", end=" ", flush=True)
        
        result = validate_gas_project(project_name, verbose=verbose)
        results.append(result)
        
        if verbose:
            if result.status == ComparisonStatus.SUCCESS:
                status_icon = "⚠️" if result.has_changes else "✅"
                print(f"  {status_icon} {result.status.value} (changes: {result.has_changes})")
            else:
                print(f"  ❌ {result.status.value}: {result.error}")
        else:
            if result.status == ComparisonStatus.SUCCESS:
                status_icon = "⚠️" if result.has_changes else "✅"
                print(f"{status_icon}")
            else:
                print(f"❌ {result.error[:50]}")
    
    return results


def validate_all_lambda_functions(verbose: bool = False) -> List[ComparisonResult]:
    """Validate all Lambda functions."""
    functions = get_lambda_functions()
    results = []
    
    print(f"🔍 Validating {len(functions)} Lambda functions...")
    
    for i, function_name in enumerate(functions, 1):
        if verbose:
            print(f"\n[{i}/{len(functions)}] {function_name}")
        else:
            print(f"[{i}/{len(functions)}] {function_name}...", end=" ", flush=True)
        
        result = validate_lambda_function(function_name, verbose=verbose)
        results.append(result)
        
        if verbose:
            if result.status == ComparisonStatus.SUCCESS:
                status_icon = "⚠️" if result.has_changes else "✅"
                print(f"  {status_icon} {result.status.value} (changes: {result.has_changes})")
            else:
                print(f"  ❌ {result.status.value}: {result.error}")
        else:
            if result.status == ComparisonStatus.SUCCESS:
                status_icon = "⚠️" if result.has_changes else "✅"
                print(f"{status_icon}")
            else:
                print(f"❌ {result.error[:50]}")
    
    return results


def generate_summary(all_results: List[ComparisonResult]) -> str:
    """Generate summary report."""
    summary_lines = []
    summary_lines.append("=" * 80)
    summary_lines.append("COMPARISON SYSTEM VALIDATION SUMMARY")
    summary_lines.append("=" * 80)
    summary_lines.append(f"Generated: {datetime.now().isoformat()}")
    summary_lines.append("")
    
    gas_results = [r for r in all_results if r.type == "gas"]
    lambda_results = [r for r in all_results if r.type == "lambda"]
    
    summary_lines.append("GAS Projects:")
    summary_lines.append(f"  Total: {len(gas_results)}")
    summary_lines.append(f"  ✅ Success (no changes): {sum(1 for r in gas_results if r.status == ComparisonStatus.SUCCESS and not r.has_changes)}")
    summary_lines.append(f"  ⚠️  Success (with changes): {sum(1 for r in gas_results if r.status == ComparisonStatus.SUCCESS and r.has_changes)}")
    summary_lines.append(f"  ❌ Errors: {sum(1 for r in gas_results if r.status == ComparisonStatus.ERROR)}")
    summary_lines.append(f"  ⏭️  Skipped: {sum(1 for r in gas_results if r.status == ComparisonStatus.SKIPPED)}")
    summary_lines.append("")
    
    summary_lines.append("Lambda Functions:")
    summary_lines.append(f"  Total: {len(lambda_results)}")
    summary_lines.append(f"  ✅ Success (no changes): {sum(1 for r in lambda_results if r.status == ComparisonStatus.SUCCESS and not r.has_changes)}")
    summary_lines.append(f"  ⚠️  Success (with changes): {sum(1 for r in lambda_results if r.status == ComparisonStatus.SUCCESS and r.has_changes)}")
    summary_lines.append(f"  ❌ Errors: {sum(1 for r in lambda_results if r.status == ComparisonStatus.ERROR)}")
    summary_lines.append("")
    
    total_duration = sum(r.duration_seconds for r in all_results)
    summary_lines.append(f"Total validation time: {total_duration:.2f} seconds")
    summary_lines.append("=" * 80)
    
    return "\n".join(summary_lines)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validate comparison system for all GAS projects and Lambda functions"
    )
    parser.add_argument("--gas-only", action="store_true",
                       help="Only validate GAS projects")
    parser.add_argument("--lambda-only", action="store_true",
                       help="Only validate Lambda functions")
    parser.add_argument("--verbose", action="store_true",
                       help="Show detailed output for each comparison")
    parser.add_argument("--output", type=str,
                       help="Save results to JSON file")
    
    args = parser.parse_args()
    
    if args.gas_only and args.lambda_only:
        print("❌ Cannot use --gas-only and --lambda-only together")
        sys.exit(1)
    
    print("🚀 Starting comparison system validation...")
    print(f"   Timestamp: {datetime.now().isoformat()}")
    
    all_results = []
    
    if not args.lambda_only:
        gas_results = validate_all_gas_projects(args.verbose)
        all_results.extend(gas_results)
    
    if not args.gas_only:
        lambda_results = validate_all_lambda_functions(args.verbose)
        all_results.extend(lambda_results)
    
    summary = generate_summary(all_results)
    print("\n" + summary)
    
    if args.output:
        import json
        with open(args.output, 'w') as f:
            json.dump([asdict(r) for r in all_results], f, indent=2)
        print(f"\n💾 Results saved to: {args.output}")
    
    if any(r.status == ComparisonStatus.ERROR for r in all_results):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
