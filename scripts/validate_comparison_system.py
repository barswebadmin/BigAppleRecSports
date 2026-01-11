#!/usr/bin/env python3
"""
Validation script for comparison system.
Runs comparison for all GAS projects and Lambda functions to validate the system works.

Usage:
    python3 scripts/validate_comparison_system.py [--gas-only] [--lambda-only] [--verbose]
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

REPO_ROOT = Path(__file__).parent.parent
GAS_ROOT = REPO_ROOT / "GoogleAppsScripts"
PROJECTS_DIR = GAS_ROOT / "projects"
LAMBDA_FUNCTIONS_DIR = REPO_ROOT / "lambda-functions"


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
    type: str  # "gas" or "lambda"
    status: ComparisonStatus
    has_changes: Optional[bool] = None
    output: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: Optional[float] = None
    timestamp: str = ""


def get_gas_projects() -> List[str]:
    """Get list of all GAS project directories."""
    if not PROJECTS_DIR.exists():
        return []
    
    projects = []
    for item in PROJECTS_DIR.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            # Check if it has .clasp.json
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
            # Check if it has lambda_function.py
            if (item / "lambda_function.py").exists():
                functions.append(item.name)
    
    return sorted(functions)


def run_command(
    cmd: List[str],
    cwd: Optional[Path] = None,
    timeout: int = 300,
    capture_output: bool = True
) -> Tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"Command timed out after {timeout} seconds"
    except Exception as e:
        return 1, "", str(e)


def validate_gas_project(project_name: str, verbose: bool = False) -> ComparisonResult:
    """Validate comparison for a single GAS project."""
    import time
    start_time = time.time()
    
    project_dir = PROJECTS_DIR / project_name
    
    # Skip waitlist-script-comprehensive if it has custom workflow
    if project_name == "waitlist-script-comprehensive":
        return ComparisonResult(
            name=project_name,
            type="gas",
            status=ComparisonStatus.SKIPPED,
            error="Uses custom workflow",
            timestamp=datetime.now().isoformat()
        )
    
    # Check if project uses build system
    has_build = (project_dir / "esbuild.config.js").exists()
    
    # Try pull comparison (most comprehensive)
    pull_script = GAS_ROOT / "remote-sync-tools" / "pull.sh"
    
    if not pull_script.exists():
        return ComparisonResult(
            name=project_name,
            type="gas",
            status=ComparisonStatus.ERROR,
            error=f"Pull script not found: {pull_script}",
            timestamp=datetime.now().isoformat()
        )
    
    # Run pull comparison
    cmd = [str(pull_script), project_name, "--compare-only"]
    exit_code, stdout, stderr = run_command(cmd, cwd=GAS_ROOT, timeout=300)
    
    duration = time.time() - start_time
    
    # Parse output to detect changes
    has_changes = (
        "Different files:" in stdout or
        "Files only in local:" in stdout or
        "Files only in remote:" in stdout or
        "Moved files:" in stdout
    )
    
    # Check for "no differences" or "identical"
    no_changes = (
        "No differences" in stdout or
        "No changes detected" in stdout or
        "identical" in stdout.lower()
    )
    
    if exit_code == 0:
        if has_changes:
            status = ComparisonStatus.SUCCESS
        elif no_changes:
            status = ComparisonStatus.SUCCESS
            has_changes = False
        else:
            status = ComparisonStatus.SUCCESS
            has_changes = None  # Couldn't determine
    else:
        status = ComparisonStatus.FAILED
    
    output_text = stdout
    if stderr:
        output_text += f"\n--- STDERR ---\n{stderr}"
    
    return ComparisonResult(
        name=project_name,
        type="gas",
        status=status,
        has_changes=has_changes,
        output=output_text if verbose else None,
        error=stderr if exit_code != 0 else None,
        duration_seconds=round(duration, 2),
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
            error=f"Function directory not found: {function_dir}",
            timestamp=datetime.now().isoformat()
        )
    
    # Check AWS credentials first
    aws_check_cmd = ["aws", "sts", "get-caller-identity"]
    exit_code, _, stderr = run_command(aws_check_cmd, timeout=10)
    
    if exit_code != 0:
        return ComparisonResult(
            name=function_name,
            type="lambda",
            status=ComparisonStatus.SKIPPED,
            error="AWS credentials not configured or expired",
            timestamp=datetime.now().isoformat()
        )
    
    # Use the existing comparison script
    compare_script = LAMBDA_FUNCTIONS_DIR / "compare_aws_to_local.sh"
    
    if not compare_script.exists():
        return ComparisonResult(
            name=function_name,
            type="lambda",
            status=ComparisonStatus.ERROR,
            error=f"Comparison script not found: {compare_script}",
            timestamp=datetime.now().isoformat()
        )
    
    # Run comparison (script compares all functions, but we can filter output)
    # For now, run it and check if our function appears in output
    cmd = ["bash", str(compare_script)]
    exit_code, stdout, stderr = run_command(cmd, cwd=LAMBDA_FUNCTIONS_DIR, timeout=300)
    
    duration = time.time() - start_time
    
    # Check if function was found and compared
    function_found = function_name in stdout
    
    # Try to detect if there were differences for this function
    # The script outputs "IDENTICAL" or "DIFFERENT" for each function
    has_changes = None
    if function_found:
        # Look for this function's section in output
        lines = stdout.split('\n')
        in_function_section = False
        for i, line in enumerate(lines):
            if function_name in line and "Comparing:" in line:
                in_function_section = True
            elif in_function_section:
                if "IDENTICAL" in line:
                    has_changes = False
                    break
                elif "DIFFERENT" in line:
                    has_changes = True
                    break
                elif "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" in line and i > 0:
                    # Moved to next function
                    break
    
    if exit_code == 0 and function_found:
        status = ComparisonStatus.SUCCESS
    elif exit_code == 0 and not function_found:
        status = ComparisonStatus.SKIPPED
        error = "Function not found in comparison output (may not exist in AWS)"
    else:
        status = ComparisonStatus.FAILED
        error = stderr if stderr else "Comparison script failed"
    
    output_text = stdout
    if stderr:
        output_text += f"\n--- STDERR ---\n{stderr}"
    
    return ComparisonResult(
        name=function_name,
        type="lambda",
        status=status,
        has_changes=has_changes,
        output=output_text if verbose else None,
        error=error if status != ComparisonStatus.SUCCESS else None,
        duration_seconds=round(duration, 2),
        timestamp=datetime.now().isoformat()
    )


def validate_all_gas_projects(verbose: bool = False) -> List[ComparisonResult]:
    """Validate all GAS projects."""
    projects = get_gas_projects()
    results = []
    
    print(f"\n🔍 Validating {len(projects)} GAS projects...")
    print("=" * 80)
    
    for i, project_name in enumerate(projects, 1):
        print(f"\n[{i}/{len(projects)}] GAS: {project_name}")
        print("-" * 80)
        
        result = validate_gas_project(project_name, verbose)
        results.append(result)
        
        # Print status
        if result.status == ComparisonStatus.SUCCESS:
            change_status = "⚠️  Changes detected" if result.has_changes else "✅ No changes"
            print(f"   Status: {result.status.value.upper()} - {change_status}")
            if result.duration_seconds:
                print(f"   Duration: {result.duration_seconds}s")
        elif result.status == ComparisonStatus.SKIPPED:
            print(f"   Status: SKIPPED - {result.error}")
        else:
            print(f"   Status: {result.status.value.upper()}")
            if result.error:
                print(f"   Error: {result.error}")
        
        if verbose and result.output:
            print(f"\n   Output:\n{result.output[:500]}...")  # First 500 chars
    
    return results


def validate_all_lambda_functions(verbose: bool = False) -> List[ComparisonResult]:
    """Validate all Lambda functions."""
    functions = get_lambda_functions()
    results = []
    
    print(f"\n🔍 Validating {len(functions)} Lambda functions...")
    print("=" * 80)
    
    for i, function_name in enumerate(functions, 1):
        print(f"\n[{i}/{len(functions)}] Lambda: {function_name}")
        print("-" * 80)
        
        result = validate_lambda_function(function_name, verbose)
        results.append(result)
        
        # Print status
        if result.status == ComparisonStatus.SUCCESS:
            change_status = "⚠️  Changes detected" if result.has_changes else "✅ No changes"
            print(f"   Status: {result.status.value.upper()} - {change_status}")
            if result.duration_seconds:
                print(f"   Duration: {result.duration_seconds}s")
        elif result.status == ComparisonStatus.SKIPPED:
            print(f"   Status: SKIPPED - {result.error}")
        else:
            print(f"   Status: {result.status.value.upper()}")
            if result.error:
                print(f"   Error: {result.error}")
        
        if verbose and result.output:
            print(f"\n   Output:\n{result.output[:500]}...")  # First 500 chars
    
    return results


def generate_summary(all_results: List[ComparisonResult]) -> str:
    """Generate summary report."""
    gas_results = [r for r in all_results if r.type == "gas"]
    lambda_results = [r for r in all_results if r.type == "lambda"]
    
    gas_success = sum(1 for r in gas_results if r.status == ComparisonStatus.SUCCESS)
    gas_failed = sum(1 for r in gas_results if r.status == ComparisonStatus.FAILED)
    gas_skipped = sum(1 for r in gas_results if r.status == ComparisonStatus.SKIPPED)
    gas_errors = sum(1 for r in gas_results if r.status == ComparisonStatus.ERROR)
    
    lambda_success = sum(1 for r in lambda_results if r.status == ComparisonStatus.SUCCESS)
    lambda_failed = sum(1 for r in lambda_results if r.status == ComparisonStatus.FAILED)
    lambda_skipped = sum(1 for r in lambda_results if r.status == ComparisonStatus.SKIPPED)
    lambda_errors = sum(1 for r in lambda_results if r.status == ComparisonStatus.ERROR)
    
    total_success = gas_success + lambda_success
    total_failed = gas_failed + lambda_failed
    total_errors = gas_errors + lambda_errors
    
    summary_lines = []
    summary_lines.append("\n" + "=" * 80)
    summary_lines.append("VALIDATION SUMMARY")
    summary_lines.append("=" * 80)
    summary_lines.append(f"Generated: {datetime.now().isoformat()}")
    summary_lines.append("")
    
    summary_lines.append("GAS Projects:")
    summary_lines.append(f"  Total: {len(gas_results)}")
    summary_lines.append(f"  ✅ Success: {gas_success}")
    summary_lines.append(f"  ❌ Failed: {gas_failed}")
    summary_lines.append(f"  ⏭️  Skipped: {gas_skipped}")
    summary_lines.append(f"  🚨 Errors: {gas_errors}")
    summary_lines.append("")
    
    summary_lines.append("Lambda Functions:")
    summary_lines.append(f"  Total: {len(lambda_results)}")
    summary_lines.append(f"  ✅ Success: {lambda_success}")
    summary_lines.append(f"  ❌ Failed: {lambda_failed}")
    summary_lines.append(f"  ⏭️  Skipped: {lambda_skipped}")
    summary_lines.append(f"  🚨 Errors: {lambda_errors}")
    summary_lines.append("")
    
    summary_lines.append("Overall:")
    summary_lines.append(f"  Total: {len(all_results)}")
    summary_lines.append(f"  ✅ Success: {total_success}")
    summary_lines.append(f"  ❌ Failed: {total_failed}")
    summary_lines.append(f"  🚨 Errors: {total_errors}")
    summary_lines.append("=" * 80)
    
    return "\n".join(summary_lines)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validate comparison system for all GAS projects and Lambda functions"
    )
    parser.add_argument(
        "--gas-only",
        action="store_true",
        help="Only validate GAS projects"
    )
    parser.add_argument(
        "--lambda-only",
        action="store_true",
        help="Only validate Lambda functions"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output for each comparison"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save results to JSON file"
    )
    
    args = parser.parse_args()
    
    if args.gas_only and args.lambda_only:
        print("❌ Cannot use --gas-only and --lambda-only together")
        sys.exit(1)
    
    print("🚀 Starting comparison system validation...")
    print(f"   Timestamp: {datetime.now().isoformat()}")
    
    all_results = []
    
    # Validate GAS projects
    if not args.lambda_only:
        gas_results = validate_all_gas_projects(args.verbose)
        all_results.extend(gas_results)
    
    # Validate Lambda functions
    if not args.gas_only:
        lambda_results = validate_all_lambda_functions(args.verbose)
        all_results.extend(lambda_results)
    
    # Generate and print summary
    summary = generate_summary(all_results)
    print(summary)
    
    # Save results to JSON if requested
    if args.output:
        output_file = Path(args.output)
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": len(all_results),
                "success": sum(1 for r in all_results if r.status == ComparisonStatus.SUCCESS),
                "failed": sum(1 for r in all_results if r.status == ComparisonStatus.FAILED),
                "skipped": sum(1 for r in all_results if r.status == ComparisonStatus.SKIPPED),
                "errors": sum(1 for r in all_results if r.status == ComparisonStatus.ERROR),
            },
            "results": [asdict(r) for r in all_results]
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {output_file}")
    
    # Exit with error code if any failures
    has_failures = any(
        r.status in (ComparisonStatus.FAILED, ComparisonStatus.ERROR)
        for r in all_results
    )
    
    if has_failures:
        print("\n❌ Validation completed with failures")
        sys.exit(1)
    else:
        print("\n✅ Validation completed successfully")
        sys.exit(0)


if __name__ == "__main__":
    main()
