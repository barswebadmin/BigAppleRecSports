#!/usr/bin/env python3
"""
Compare all GAS projects between local and remote.
Compares all GAS projects between local and remote.
"""

import json
import sys
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from .compare_project_remote_with_local import compare_project_remote_with_local
from .comparison_logic import ComparisonResult

REPO_ROOT = Path(__file__).parent.parent.parent
GAS_ROOT = REPO_ROOT / "GoogleAppsScripts"
PROJECTS_DIR = GAS_ROOT / "projects"


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
            if (item / ".clasp.json").exists():
                projects.append(item.name)
    
    return sorted(projects)


def check_project_has_build(project_dir: Path) -> bool:
    """Check if project uses esbuild (has esbuild.config.js)."""
    return (project_dir / "esbuild.config.js").exists()


def format_comparison_result(result: ComparisonResult) -> str:
    """Format ComparisonResult as string output."""
    lines = []
    if result.different_count > 0:
        lines.append("Different files:")
        for rel_path, file_comp in result.files.items():
            if file_comp.status.value == "different":
                lines.append(f"  - {rel_path}")
    
    if result.only_local_count > 0:
        lines.append("Files only in local:")
        for rel_path, file_comp in result.files.items():
            if file_comp.status.value == "only_local":
                lines.append(f"  - {rel_path}")
    
    if result.only_remote_count > 0:
        lines.append("Files only in remote:")
        for rel_path, file_comp in result.files.items():
            if file_comp.status.value == "only_remote":
                lines.append(f"  - {rel_path}")
    
    return "\n".join(lines)


def compare_push(project_name: str) -> Tuple[bool, Optional[str]]:
    """Compare local build vs remote for push operation."""
    project_dir = PROJECTS_DIR / project_name
    
    if project_name == "waitlist-script-comprehensive":
        return False, "Skipped - uses custom workflow"
    
    has_build = check_project_has_build(project_dir)
    
    if has_build:
        local_path = project_dir / "build"
    else:
        local_path = project_dir / "src"
    
    try:
        result = compare_project_remote_with_local(
            remote_origin_type="google",
            project_name=project_name,
            local_path=local_path,
            project_root=GAS_ROOT.parent
        )
        
        has_changes = (
            result.different_count > 0 or
            result.only_local_count > 0 or
            result.only_remote_count > 0
        )
        
        output = format_comparison_result(result)
        return has_changes, output
    except Exception as e:
        return False, f"Push comparison failed: {str(e)}"


def compare_pull(project_name: str) -> Tuple[bool, Optional[str]]:
    """Compare local vs remote for pull operation."""
    project_dir = PROJECTS_DIR / project_name
    
    if project_name == "waitlist-script-comprehensive":
        return False, "Skipped - uses custom workflow"
    
    local_path = project_dir / "src"
    
    try:
        result = compare_project_remote_with_local(
            remote_origin_type="google",
            project_name=project_name,
            local_path=local_path,
            project_root=GAS_ROOT.parent
        )
        
        has_changes = (
            result.different_count > 0 or
            result.only_local_count > 0 or
            result.only_remote_count > 0
        )
        
        output = format_comparison_result(result)
        return has_changes, output
    except Exception as e:
        return False, f"Pull comparison failed: {str(e)}"


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
    
    projects_with_push_changes = sum(1 for r in results if r.push_has_changes)
    projects_with_pull_changes = sum(1 for r in results if r.pull_has_changes)
    projects_with_errors = sum(1 for r in results if r.error)
    
    report_lines.append("SUMMARY")
    report_lines.append("-" * 80)
    report_lines.append(f"Projects with push changes (local build ≠ remote): {projects_with_push_changes}/{len(results)}")
    report_lines.append(f"Projects with pull changes (local src ≠ remote): {projects_with_pull_changes}/{len(results)}")
    report_lines.append(f"Projects with errors: {projects_with_errors}/{len(results)}")
    report_lines.append("")
    
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
        
        if result.push_has_changes:
            report_lines.append("  📤 PUSH: ⚠️  CHANGES DETECTED")
            if result.push_diff:
                diff_lines = result.push_diff.split('\n')
                for line in diff_lines[:20]:
                    if any(keyword in line for keyword in ["Different files:", "Files only in", "Moved files:"]):
                        report_lines.append(f"     {line}")
        else:
            report_lines.append("  📤 PUSH: ✅ No changes")
        
        if result.pull_has_changes:
            report_lines.append("  📥 PULL: ⚠️  CHANGES DETECTED")
            if result.pull_diff:
                diff_lines = result.pull_diff.split('\n')
                for line in diff_lines[:20]:
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
    
    report = generate_report(results)
    print("\n" + report)
    
    output_file = REPO_ROOT / "gas_comparison_results.json"
    with open(output_file, 'w') as f:
        json.dump([asdict(r) for r in results], f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {output_file}")
    
    if any(r.push_has_changes or r.pull_has_changes or r.error for r in results):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
