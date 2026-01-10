#!/usr/bin/env python3
"""
Compare all GAS projects between local and remote.
Collects diff results and provides comprehensive evaluation.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

REPO_ROOT = Path(__file__).parent.parent
GAS_ROOT = REPO_ROOT / "GoogleAppsScripts"
PROJECTS_DIR = GAS_ROOT / "projects"
COMPARE_SCRIPT = REPO_ROOT / "scripts" / "file_comparison" / "compare_at_path.py"


@dataclass
class ProjectComparison:
    """Results of comparing a single project."""
    project_name: str
    has_build: bool
    push_diff: Optional[str] = None
    pull_diff: Optional[str] = None
    push_has_changes: bool = False
    pull_has_changes: bool = False
    error: Optional[str] = None
    comparison_timestamp: str = ""


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


def run_command(cmd: List[str], cwd: Optional[Path] = None, capture_output: bool = True) -> Tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            timeout=300
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out after 300 seconds"
    except Exception as e:
        return 1, "", str(e)


def check_project_has_build(project_dir: Path) -> bool:
    """Check if project uses esbuild (has esbuild.config.js)."""
    return (project_dir / "esbuild.config.js").exists()


def compare_push(project_name: str) -> Tuple[bool, Optional[str]]:
    """Compare local build vs remote for push operation."""
    project_dir = PROJECTS_DIR / project_name
    
    # Skip waitlist-script-comprehensive - it has its own workflow
    if project_name == "waitlist-script-comprehensive":
        return False, "Skipped - uses custom workflow"
    
    # Check if project uses build system
    has_build = check_project_has_build(project_dir)
    
    if has_build:
        # Use the centralized push script in compare mode
        script = GAS_ROOT / "remote-sync-tools" / "push.sh"
        exit_code, stdout, stderr = run_command(
            [str(script), project_name, "--compare-only"],
            cwd=GAS_ROOT
        )
        
        if exit_code != 0:
            return False, f"Push comparison failed: {stderr}"
        
        # Parse output to detect changes
        has_changes = (
            "Different files:" in stdout or
            "Files only in local:" in stdout or
            "Files only in remote:" in stdout
        )
        
        return has_changes, stdout
    else:
        # For non-build projects, compare local src/ structure vs remote
        # Use the pull comparison approach but compare src/ directly
        # First pull remote into temp, then compare
        script = GAS_ROOT / "remote-sync-tools" / "pull.sh"
        exit_code, stdout, stderr = run_command(
            [str(script), project_name, "--compare-only"],
            cwd=GAS_ROOT
        )
        
        if exit_code != 0:
            return False, f"Push comparison failed (using pull method): {stderr}"
        
        # For non-build projects, push comparison is same as pull comparison
        # (both compare local src/ vs remote)
        has_changes = (
            "Different files:" in stdout or
            "Files only in local:" in stdout or
            "Files only in remote:" in stdout
        )
        
        return has_changes, stdout


def compare_pull(project_name: str) -> Tuple[bool, Optional[str]]:
    """Compare local vs remote for pull operation."""
    project_dir = PROJECTS_DIR / project_name
    
    # Skip waitlist-script-comprehensive - it has its own workflow
    if project_name == "waitlist-script-comprehensive":
        return False, "Skipped - uses custom workflow"
    
    # Use the centralized pull script in compare mode
    script = GAS_ROOT / "remote-sync-tools" / "pull.sh"
    exit_code, stdout, stderr = run_command(
        [str(script), project_name, "--compare-only"],
        cwd=GAS_ROOT
    )
    
    if exit_code != 0:
        return False, f"Pull comparison failed: {stderr}"
    
    # Parse output to detect changes
    has_changes = (
        "Different files:" in stdout or
        "Files only in local:" in stdout or
        "Files only in remote:" in stdout
    )
    
    return has_changes, stdout


def compare_all_projects() -> List[ProjectComparison]:
    """Compare all GAS projects and collect results."""
    projects = get_gas_projects()
    results = []
    
    print(f"🔍 Found {len(projects)} GAS projects to compare")
    print("=" * 80)
    
    for i, project_name in enumerate(projects, 1):
        print(f"\n[{i}/{len(projects)}] Comparing: {project_name}")
        print("-" * 80)
        
        project_dir = PROJECTS_DIR / project_name
        has_build = check_project_has_build(project_dir)
        
        result = ProjectComparison(
            project_name=project_name,
            has_build=has_build,
            comparison_timestamp=datetime.now().isoformat()
        )
        
        # Compare push (local build vs remote)
        print("  📤 Comparing push (local build vs remote)...")
        try:
            push_has_changes, push_diff = compare_push(project_name)
            result.push_has_changes = push_has_changes
            result.push_diff = push_diff
            if push_has_changes:
                print("     ⚠️  Changes detected")
            else:
                print("     ✅ No changes")
        except Exception as e:
            result.error = f"Push comparison error: {str(e)}"
            print(f"     ❌ Error: {result.error}")
        
        # Compare pull (local src vs remote)
        print("  📥 Comparing pull (local src vs remote)...")
        try:
            pull_has_changes, pull_diff = compare_pull(project_name)
            result.pull_has_changes = pull_has_changes
            result.pull_diff = pull_diff
            if pull_has_changes:
                print("     ⚠️  Changes detected")
            else:
                print("     ✅ No changes")
        except Exception as e:
            if not result.error:
                result.error = f"Pull comparison error: {str(e)}"
            else:
                result.error += f"; Pull: {str(e)}"
            print(f"     ❌ Error: {str(e)}")
        
        results.append(result)
    
    return results


def generate_report(results: List[ProjectComparison]) -> str:
    """Generate comprehensive evaluation report."""
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("GAS PROJECTS COMPREHENSIVE COMPARISON REPORT")
    report_lines.append("=" * 80)
    report_lines.append(f"Generated: {datetime.now().isoformat()}")
    report_lines.append(f"Total Projects: {len(results)}")
    report_lines.append("")
    
    # Summary statistics
    projects_with_push_changes = sum(1 for r in results if r.push_has_changes)
    projects_with_pull_changes = sum(1 for r in results if r.pull_has_changes)
    projects_with_errors = sum(1 for r in results if r.error)
    
    report_lines.append("SUMMARY")
    report_lines.append("-" * 80)
    report_lines.append(f"Projects with push changes (local build ≠ remote): {projects_with_push_changes}/{len(results)}")
    report_lines.append(f"Projects with pull changes (local src ≠ remote): {projects_with_pull_changes}/{len(results)}")
    report_lines.append(f"Projects with errors: {projects_with_errors}/{len(results)}")
    report_lines.append("")
    
    # Detailed results per project
    report_lines.append("DETAILED RESULTS")
    report_lines.append("=" * 80)
    
    for result in results:
        report_lines.append("")
        report_lines.append(f"📁 {result.project_name}")
        report_lines.append("-" * 80)
        report_lines.append(f"  Build System: {'esbuild' if result.has_build else 'clasp_helpers'}")
        
        if result.error:
            report_lines.append(f"  ❌ ERROR: {result.error}")
            continue
        
        # Push comparison
        if result.push_has_changes:
            report_lines.append("  📤 PUSH: ⚠️  CHANGES DETECTED")
            if result.push_diff:
                # Extract key info from diff
                diff_lines = result.push_diff.split('\n')
                for line in diff_lines[:20]:  # First 20 lines
                    if any(keyword in line for keyword in ["Different files:", "Files only in", "Moved files:"]):
                        report_lines.append(f"     {line}")
        else:
            report_lines.append("  📤 PUSH: ✅ No changes")
        
        # Pull comparison
        if result.pull_has_changes:
            report_lines.append("  📥 PULL: ⚠️  CHANGES DETECTED")
            if result.pull_diff:
                # Extract key info from diff
                diff_lines = result.pull_diff.split('\n')
                for line in diff_lines[:20]:  # First 20 lines
                    if any(keyword in line for keyword in ["Different files:", "Files only in", "Moved files:"]):
                        report_lines.append(f"     {line}")
        else:
            report_lines.append("  📥 PULL: ✅ No changes")
    
    return "\n".join(report_lines)


def main():
    """Main entry point."""
    print("🚀 Starting comprehensive GAS project comparison...")
    print("")
    
    results = compare_all_projects()
    
    # Generate and print report
    report = generate_report(results)
    print("\n" + report)
    
    # Save results to JSON
    output_file = REPO_ROOT / "gas_comparison_results.json"
    with open(output_file, 'w') as f:
        json.dump([asdict(r) for r in results], f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {output_file}")
    
    # Exit with error code if any projects have changes or errors
    if any(r.push_has_changes or r.pull_has_changes or r.error for r in results):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
