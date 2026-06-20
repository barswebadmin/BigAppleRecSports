#!/usr/bin/env python3
"""
Unified Version Manager
Automatically manages semantic versioning for:
- BARS backend (single version.json)
- Lambda functions (per-function version.json)

All version history is stored in version_history within version.json files.
Expected to be called from CI/CD workflow with explicit paths and bump types.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


def parse_version(version_string: str) -> Tuple[int, int, int]:
    """Parse version string into components"""
    match = re.match(r'(\d+)\.(\d+)\.(\d+)', version_string)
    if match:
        return int(match.group(1)), int(match.group(2)), int(match.group(3))
    return 1, 0, 0

def increment_version(current_version: str, bump_type: str) -> str:
    """Increment version based on bump type"""
    major, minor, patch = parse_version(current_version)
    
    if bump_type == 'major':
        return f"{major + 1}.0.0"
    elif bump_type == 'minor':
        return f"{major}.{minor + 1}.0"
    elif bump_type == 'patch':
        return f"{major}.{minor}.{patch + 1}"
    else:  # build increment only
        return current_version

def categorize_commit_messages(commit_messages: List[str]) -> Dict[str, List[str]]:
    """Categorize commit messages into features, fixes, breaking, and other"""
    categories = {
        'breaking': [],
        'features': [],
        'fixes': [],
        'other': []
    }
    
    for msg in commit_messages:
        msg_lower = msg.lower()
        clean_msg = msg.split(': ', 1)[-1] if ': ' in msg else msg
        
        if any(kw in msg_lower for kw in ['breaking', 'major']):
            categories['breaking'].append(clean_msg)
        elif any(kw in msg_lower for kw in ['feat:', 'feature:', 'add:', 'new:']):
            categories['features'].append(clean_msg)
        elif any(kw in msg_lower for kw in ['fix:', 'bugfix:', 'patch:', 'hotfix:']):
            categories['fixes'].append(clean_msg)
        else:
            categories['other'].append(clean_msg)
    
    return categories

def generate_version_history_entry(new_version: str, bump_type: str, commit_messages: List[str], 
                                  changed_files: Optional[List[str]] = None) -> Dict[str, Any]:
    """Generate a version history entry dictionary"""
    current_date = datetime.now().strftime("%Y-%m-%d")
    categories = categorize_commit_messages(commit_messages)
    
    # Generate description from first commit message
    description = "Version update"
    if commit_messages:
        first_msg = commit_messages[0]
        description = first_msg.split(': ', 1)[-1] if ': ' in first_msg else first_msg[:100]
    
    # Build description with categorized changes
    desc_parts = [description]
    if categories['breaking']:
        desc_parts.append(f"BREAKING: {', '.join(categories['breaking'][:3])}")
    if categories['features']:
        desc_parts.append(f"Features: {', '.join(categories['features'][:3])}")
    if categories['fixes']:
        desc_parts.append(f"Fixes: {', '.join(categories['fixes'][:3])}")
    
    full_description = " | ".join(desc_parts)
    if len(full_description) > 200:
        full_description = full_description[:197] + "..."
    
    return {
        "version": new_version,
        "date": current_date,
        "description": full_description
    }

def update_version_file(version_file_path: str, new_version: str, bump_type: str, 
                       commit_messages: List[str], changed_files: Optional[List[str]] = None) -> bool:
    """Update a version.json file with new version and history entry"""
    version_file = Path(version_file_path)
    
    if not version_file.exists():
        print(f"⚠️  Version file not found: {version_file_path}")
        return False
    
    # Read current version data
    with open(version_file, 'r') as f:
        data = json.load(f)
    
    current_version = data["version"]
    current_build = data["build"]
    
    # Increment build number, reset if major/minor version changed
    if bump_type in ['major', 'minor']:
        new_build = 1
    else:
        new_build = current_build + 1
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Update version data
    data["version"] = new_version
    data["build"] = new_build
    data["last_updated"] = current_date
    
    # Generate and insert new history entry at the beginning
    # Only add history entry if version actually changed (not just build increment)
    if new_version != current_version:
        history_entry = generate_version_history_entry(new_version, bump_type, commit_messages, changed_files)
        data["version_history"].insert(0, history_entry)
    
    # Write updated data
    with open(version_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Updated {version_file_path}: {current_version} → {new_version} (build {new_build})")
    return True

def get_version_info(version_file_path: str) -> Dict[str, Any]:
    """Return complete version information from a version.json file"""
    version_file = Path(version_file_path)
    
    with open(version_file, 'r') as f:
        data = json.load(f)
    
    version = data["version"]
    build = data["build"]
    last_updated = data["last_updated"]
    codename = data["codename"]
    
    return {
        "version": version,
        "build": build,
        "full_version": f"{version}.{build}",
        "last_updated": last_updated,
        "codename": codename
    }

def get_latest_changes(version_file_path: str, n: int = 1) -> Any:
    """Get the first N entries from version_history (most recent entries, since it's reverse chronological)
    
    Args:
        version_file_path: Path to version.json file
        n: Number of entries to return (default: 1)
    
    Returns:
        If n == 1: Single dict with the most recent entry
        If n > 1: List of dicts with the first N entries
    """
    version_file = Path(version_file_path)
    
    with open(version_file, 'r') as f:
        data = json.load(f)
    
    version_history = data["version_history"]
    entries = version_history[:n]
    return entries[0] if n == 1 else entries

def process_component(version_file_path: str, bump_type: str, 
                     commit_messages: List[str], changed_files: Optional[List[str]] = None) -> bool:
    """Process versioning for a single component (backend or lambda function)"""
    version_file = Path(version_file_path)
    
    if not version_file.exists():
        print(f"⚠️  Version file not found: {version_file_path}")
        return False
    
    # Read current version
    with open(version_file, 'r') as f:
        data = json.load(f)
    
    current_version = data["version"]
    
    # Calculate new version
    new_version = increment_version(current_version, bump_type)
    print(f"📈 Version bump: {bump_type} ({current_version} → {new_version})")
    
    # Update version file with new version and history entry
    return update_version_file(version_file_path, new_version, bump_type, commit_messages, changed_files)

def commit_and_push_changes(files_to_commit: List[str]) -> bool:
    """Commit and push version updates to main"""
    if not files_to_commit:
        print("ℹ️  No version files to commit")
        return False
    
    # Check if files actually changed
    changed_files = []
    for file_path in files_to_commit:
        try:
            # Check if file has uncommitted changes
            result = subprocess.run(['git', 'diff', '--quiet', file_path], 
                                  capture_output=True, check=False)
            if result.returncode != 0:
                changed_files.append(file_path)
            else:
                # Check staged changes
                result = subprocess.run(['git', 'diff', '--cached', '--quiet', file_path], 
                                      capture_output=True, check=False)
                if result.returncode != 0:
                    changed_files.append(file_path)
        except subprocess.CalledProcessError:
            pass
    
    if not changed_files:
        print("ℹ️  No version changes to commit")
        return False
    
    # Stage files
    for file_path in changed_files:
        try:
            subprocess.run(['git', 'add', file_path], check=True, capture_output=True)
            print(f"📝 Staged: {file_path}")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Failed to stage {file_path}: {e}")
    
    # Commit
    try:
        subprocess.run(['git', 'commit', '-m', 'chore: auto-update version and changelog [skip ci]'], 
                      check=True, capture_output=True)
        print("✅ Committed version updates")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Failed to commit: {e}")
        return False
    
    # Push
    try:
        subprocess.run(['git', 'push', 'origin', 'main'], check=True, capture_output=True)
        print("✅ Pushed version updates to main")
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Failed to push: {e}")
        return False

def main():
    """Main function - processes version updates based on CLI arguments"""
    parser = argparse.ArgumentParser(description='Update version files')
    
    # Backend options
    parser.add_argument('--backend-version-file', type=str, help='Path to backend version.json file')
    parser.add_argument('--backend-bump', type=str, choices=['major', 'minor', 'patch', 'build'],
                       help='Version bump type for backend')
    
    # Lambda function options (can be specified multiple times)
    parser.add_argument('--lambda-update', action='append', 
                       help='Lambda update in format: function_name:version_file_path:bump_type')
    
    # Commit messages and changed files
    parser.add_argument('--commit-messages', type=str, 
                       help='Newline-separated list of commit messages')
    parser.add_argument('--changed-files', type=str,
                       help='Newline-separated list of changed files (optional)')
    
    # CI/CD options
    parser.add_argument('--commit-and-push', action='store_true',
                       help='Commit and push changes (CI/CD only)')
    
    args = parser.parse_args()
    
    # Parse commit messages
    commit_messages = []
    if args.commit_messages:
        commit_messages = [msg.strip() for msg in args.commit_messages.split('\n') if msg.strip()]
    
    # Parse changed files
    changed_files = None
    if args.changed_files:
        changed_files = [f.strip() for f in args.changed_files.split('\n') if f.strip()]
    
    files_to_commit = []
    processed = False
    
    # Process backend
    if args.backend_version_file and args.backend_bump:
        if process_component(
            args.backend_version_file,
            args.backend_bump,
            commit_messages,
            changed_files
        ):
            processed = True
            files_to_commit.append(args.backend_version_file)
    
    # Process lambda functions
    if args.lambda_update:
        for lambda_spec in args.lambda_update:
            parts = lambda_spec.split(':')
            if len(parts) != 3:
                print(f"⚠️  Invalid lambda update format: {lambda_spec}")
                print("   Expected: function_name:version_file_path:bump_type")
                continue
            
            func_name, version_file, bump_type = parts
            
            if process_component(
                version_file,
                bump_type,
                commit_messages,
                changed_files
            ):
                processed = True
                files_to_commit.append(version_file)
    
    if not processed:
        print("ℹ️  No version updates processed")
        sys.exit(0)
    
    # Commit and push if requested (CI/CD mode)
    if args.commit_and_push:
        print("\n📤 Committing and pushing version updates...")
        commit_and_push_changes(files_to_commit)
    else:
        print("\n✅ Version files updated (ready for commit)")
        print("   Files to commit:")
        for file_path in files_to_commit:
            print(f"   - {file_path}")
        print("   git commit -m 'chore: update version'")
    
    print("🎉 Version management complete!")

if __name__ == "__main__":
    main()
