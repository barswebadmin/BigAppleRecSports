#!/usr/bin/env python3
"""
Lambda Function Version Manager
Automatically increments version numbers for lambda functions when changes are detected
"""

import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

def get_git_root():
    """Get the git repository root directory"""
    try:
        result = subprocess.run(['git', 'rev-parse', '--show-toplevel'], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None

def get_changed_lambda_functions():
    """Get list of lambda functions that have changes in the current commit"""
    try:
        # Get staged files
        result = subprocess.run(['git', 'diff', '--cached', '--name-only'], 
                              capture_output=True, text=True, check=True)
        changed_files = result.stdout.strip().split('\n')
        
        lambda_functions = set()
        for file_path in changed_files:
            if file_path.startswith('lambda-functions/'):
                # Extract the lambda function directory name
                parts = file_path.split('/')
                if len(parts) >= 2:
                    lambda_function = parts[1]
                    # Skip version.py files to avoid infinite loop
                    if not file_path.endswith('version.py'):
                        lambda_functions.add(lambda_function)
        
        return list(lambda_functions)
    except subprocess.CalledProcessError:
        return []

def increment_version(version_file_path):
    """Increment the version number in a version.py file"""
    if not os.path.exists(version_file_path):
        print(f"Warning: Version file not found: {version_file_path}")
        return False
    
    with open(version_file_path, 'r') as f:
        content = f.read()
    
    # Extract current version info
    version_match = re.search(r'__version__ = "([^"]+)"', content)
    build_match = re.search(r'__build__ = (\d+)', content)
    
    if not version_match or not build_match:
        print(f"Warning: Could not parse version info in {version_file_path}")
        return False
    
    current_version = version_match.group(1)
    current_build = int(build_match.group(1))
    
    # Increment build number
    new_build = current_build + 1
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Update the file content
    new_content = re.sub(r'__build__ = \d+', f'__build__ = {new_build}', content)
    new_content = re.sub(r'__last_updated__ = "[^"]+"', f'__last_updated__ = "{current_date}"', new_content)
    
    with open(version_file_path, 'w') as f:
        f.write(new_content)
    
    print(f"✅ Updated {version_file_path}: {current_version}.{current_build} → {current_version}.{new_build}")
    return True

def main():
    """Main function to increment versions for changed lambda functions"""
    git_root = get_git_root()
    if not git_root:
        print("Error: Not in a git repository")
        sys.exit(1)
    
    changed_functions = get_changed_lambda_functions()
    if not changed_functions:
        print("ℹ️  No lambda function changes detected")
        return
    
    print(f"🔍 Detected changes in lambda functions: {', '.join(changed_functions)}")
    
    updated_files = []
    for func_name in changed_functions:
        version_file = os.path.join(git_root, 'lambda-functions', func_name, 'version.py')
        if increment_version(version_file):
            updated_files.append(version_file)
    
    # Stage the updated version files
    if updated_files:
        for file_path in updated_files:
            subprocess.run(['git', 'add', file_path], check=True)
        print(f"📝 Staged {len(updated_files)} version file(s) for commit")
    
    print("🎉 Version management complete!")

if __name__ == "__main__":
    main() 