#!/usr/bin/env python3
"""
Backend Version Manager & Changelog Generator
Automatically manages semantic versioning and generates changelogs for the BARS backend
"""

import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import json

def get_git_root():
    """Get the git repository root directory"""
    try:
        result = subprocess.run(['git', 'rev-parse', '--show-toplevel'], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None

def get_backend_changes():
    """Get list of backend files that have changes"""
    try:
        # First try to get staged files (for pre-commit usage)
        result = subprocess.run(['git', 'diff', '--cached', '--name-only'], 
                              capture_output=True, text=True, check=True)
        changed_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
        
        # If no staged files, check the last commit (for merge commits)
        if not changed_files or changed_files == ['']:
            result = subprocess.run(['git', 'diff', '--name-only', 'HEAD~1', 'HEAD'], 
                                  capture_output=True, text=True, check=True)
            changed_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
        
        backend_files = []
        for file_path in changed_files:
            if file_path and file_path.startswith('backend/') and not file_path.endswith('version.py') and not file_path.endswith('CHANGELOG.md'):
                backend_files.append(file_path)
        
        return backend_files
    except subprocess.CalledProcessError:
        return []

def get_commit_messages():
    """Get recent commit messages to analyze for version type"""
    try:
        # For merge commits, get the merge commit message and recent commits
        result = subprocess.run(['git', 'log', '--oneline', '-10', '--merges'], 
                              capture_output=True, text=True, check=True)
        merge_messages = result.stdout.strip().split('\n') if result.stdout.strip() else []
        
        # Also get regular recent commits
        result = subprocess.run(['git', 'log', '--oneline', '-10'], 
                              capture_output=True, text=True, check=True)
        regular_messages = result.stdout.strip().split('\n') if result.stdout.strip() else []
        
        # Combine and deduplicate
        all_messages = list(set(merge_messages + regular_messages))
        return all_messages[:10]  # Limit to 10 most recent
    except subprocess.CalledProcessError:
        return []

def determine_version_bump(changed_files, commit_messages):
    """Determine what type of version bump is needed"""
    # Analyze commit messages for conventional commits
    breaking_keywords = ['BREAKING', 'breaking change', 'major']
    feature_keywords = ['feat:', 'feature:', 'add:', 'new:']
    fix_keywords = ['fix:', 'bugfix:', 'patch:', 'hotfix:']
    
    # Check file types for impact assessment
    critical_files = ['main.py', 'config.py', 'requirements.txt']
    api_files = ['routers/', 'models/']
    service_files = ['services/']
    
    # Analyze commit messages
    has_breaking = any(any(keyword in msg.lower() for keyword in breaking_keywords) 
                      for msg in commit_messages)
    has_feature = any(any(keyword in msg.lower() for keyword in feature_keywords) 
                     for msg in commit_messages)
    has_fix = any(any(keyword in msg.lower() for keyword in fix_keywords) 
                 for msg in commit_messages)
    
    # Analyze changed files
    has_critical_changes = any(any(cf in file for cf in critical_files) 
                              for file in changed_files)
    has_api_changes = any(any(af in file for af in api_files) 
                         for file in changed_files)
    
    if has_breaking or (has_critical_changes and has_api_changes):
        return 'major'
    elif has_feature or has_api_changes:
        return 'minor'
    elif has_fix or changed_files:
        return 'patch'
    else:
        return 'build'  # Just increment build number

def parse_version(version_string):
    """Parse version string into components"""
    match = re.match(r'(\d+)\.(\d+)\.(\d+)', version_string)
    if match:
        return int(match.group(1)), int(match.group(2)), int(match.group(3))
    return 1, 0, 0

def increment_version(current_version, bump_type):
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

def generate_changelog_entry(version, bump_type, changed_files, commit_messages):
    """Generate a changelog entry for this version"""
    date = datetime.now().strftime("%Y-%m-%d")
    
    # Categorize changes
    features = []
    fixes = []
    breaking = []
    other = []
    
    for msg in commit_messages:
        msg_lower = msg.lower()
        if any(kw in msg_lower for kw in ['feat:', 'feature:', 'add:', 'new:']):
            features.append(msg.split(': ', 1)[-1] if ': ' in msg else msg)
        elif any(kw in msg_lower for kw in ['fix:', 'bugfix:', 'patch:']):
            fixes.append(msg.split(': ', 1)[-1] if ': ' in msg else msg)
        elif any(kw in msg_lower for kw in ['breaking', 'major']):
            breaking.append(msg.split(': ', 1)[-1] if ': ' in msg else msg)
        else:
            other.append(msg.split(': ', 1)[-1] if ': ' in msg else msg)
    
    # Build changelog entry
    entry = f"\n## [{version}] - {date}\n\n"
    
    if breaking:
        entry += "### 💥 BREAKING CHANGES\n"
        for item in breaking:
            entry += f"- {item}\n"
        entry += "\n"
    
    if features:
        entry += "### ✨ Features\n"
        for item in features:
            entry += f"- {item}\n"
        entry += "\n"
    
    if fixes:
        entry += "### 🐛 Bug Fixes\n"
        for item in fixes:
            entry += f"- {item}\n"
        entry += "\n"
    
    if other:
        entry += "### 🔧 Other Changes\n"
        for item in other:
            entry += f"- {item}\n"
        entry += "\n"
    
    # Add file changes summary
    if changed_files:
        entry += "### 📁 Files Changed\n"
        for file in changed_files[:10]:  # Limit to first 10 files
            entry += f"- `{file}`\n"
        if len(changed_files) > 10:
            entry += f"- ... and {len(changed_files) - 10} more files\n"
        entry += "\n"
    
    return entry

def update_version_file(git_root, new_version, bump_type, changelog_entry):
    """Update the backend version.py file"""
    version_file = os.path.join(git_root, 'backend', 'version.py')
    
    if not os.path.exists(version_file):
        print(f"Warning: Version file not found: {version_file}")
        return False
    
    with open(version_file, 'r') as f:
        content = f.read()
    
    # Extract current build number
    build_match = re.search(r'__build__ = (\d+)', content)
    current_build = int(build_match.group(1)) if build_match else 1
    
    # Increment build number, reset if major/minor version changed
    if bump_type in ['major', 'minor']:
        new_build = 1
    else:
        new_build = current_build + 1
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Update version info
    new_content = re.sub(r'__version__ = "[^"]+"', f'__version__ = "{new_version}"', content)
    new_content = re.sub(r'__build__ = \d+', f'__build__ = {new_build}', new_content)
    new_content = re.sub(r'__last_updated__ = "[^"]+"', f'__last_updated__ = "{current_date}"', new_content)
    
    with open(version_file, 'w') as f:
        f.write(new_content)
    
    print(f"✅ Updated {version_file}: {new_version}.{new_build}")
    return True

def update_changelog(git_root, changelog_entry):
    """Update or create the CHANGELOG.md file"""
    changelog_file = os.path.join(git_root, 'backend', 'CHANGELOG.md')
    
    if os.path.exists(changelog_file):
        with open(changelog_file, 'r') as f:
            existing_content = f.read()
        
        # Insert new entry after the header
        if "# Changelog" in existing_content:
            header, rest = existing_content.split("# Changelog", 1)
            new_content = f"# Changelog\n\nAll notable changes to the BARS backend will be documented in this file.\n{changelog_entry}{rest}"
        else:
            new_content = f"# Changelog\n\nAll notable changes to the BARS backend will be documented in this file.\n{changelog_entry}\n{existing_content}"
    else:
        new_content = f"""# Changelog

All notable changes to the BARS backend will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
{changelog_entry}"""
    
    with open(changelog_file, 'w') as f:
        f.write(new_content)
    
    print(f"✅ Updated {changelog_file}")
    return True

def main():
    """Main function to manage backend versioning"""
    git_root = get_git_root()
    if not git_root:
        print("Error: Not in a git repository")
        sys.exit(1)
    
    changed_files = get_backend_changes()
    if not changed_files:
        print("ℹ️  No backend changes detected")
        return
    
    print(f"🔍 Detected backend changes in: {len(changed_files)} files")
    
    # Get current version
    version_file = os.path.join(git_root, 'backend', 'version.py')
    if os.path.exists(version_file):
        with open(version_file, 'r') as f:
            content = f.read()
        version_match = re.search(r'__version__ = "([^"]+)"', content)
        current_version = version_match.group(1) if version_match else "1.0.0"
    else:
        current_version = "1.0.0"
    
    commit_messages = get_commit_messages()
    bump_type = determine_version_bump(changed_files, commit_messages)
    new_version = increment_version(current_version, bump_type)
    
    print(f"📈 Version bump: {bump_type} ({current_version} → {new_version})")
    
    # Generate changelog entry
    changelog_entry = generate_changelog_entry(new_version, bump_type, changed_files, commit_messages)
    
    # Update files
    if update_version_file(git_root, new_version, bump_type, changelog_entry):
        update_changelog(git_root, changelog_entry)
        
        # Stage updated files
        subprocess.run(['git', 'add', version_file], check=True)
        changelog_file = os.path.join(git_root, 'backend', 'CHANGELOG.md')
        if os.path.exists(changelog_file):
            subprocess.run(['git', 'add', changelog_file], check=True)
        
        print(f"📝 Staged version and changelog files")
    
    print("🎉 Backend version management complete!")

if __name__ == "__main__":
    main() 