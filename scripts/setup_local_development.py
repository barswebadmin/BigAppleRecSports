#!/usr/bin/env python3
"""
Local Development Setup for Lambda Functions

This script creates symbolic links to the bars_common_utils lambda layer
in each lambda function directory so that imports work locally.

Usage:
    python scripts/setup_local_development.py
"""

import os
import sys
from pathlib import Path

def setup_lambda_layer_symlinks():
    """Create symlinks to bars_common_utils in all lambda function directories"""
    
    # Get the project root directory (where this script is run from)
    project_root = Path.cwd()
    
    # Paths
    layer_source = project_root / "lambda-layers" / "bars-common-utils" / "python" / "bars_common_utils"
    lambda_functions_dir = project_root / "lambda-functions"
    
    # Verify the layer exists
    if not layer_source.exists():
        print(f"❌ Lambda layer not found at: {layer_source}")
        return False
    
    # Verify lambda-functions directory exists
    if not lambda_functions_dir.exists():
        print(f"❌ Lambda functions directory not found at: {lambda_functions_dir}")
        return False
    
    print(f"🔍 Looking for lambda functions in: {lambda_functions_dir}")
    print(f"📦 Lambda layer source: {layer_source}")
    print()
    
    success_count = 0
    skip_count = 0
    
    # Find all lambda function directories
    for function_dir in lambda_functions_dir.iterdir():
        if not function_dir.is_dir():
            continue
            
        # Skip if it doesn't contain a lambda_function.py (not a lambda function)
        if not (function_dir / "lambda_function.py").exists():
            print(f"⏭️  Skipping {function_dir.name} (no lambda_function.py)")
            continue
        
        # Path where the symlink should be created
        symlink_target = function_dir / "bars_common_utils"
        
        # Skip if symlink already exists and is correct
        if symlink_target.exists():
            if symlink_target.is_symlink() and symlink_target.resolve() == layer_source.resolve():
                print(f"✅ {function_dir.name}/bars_common_utils (already linked)")
                skip_count += 1
                continue
            else:
                # Remove incorrect symlink or file
                if symlink_target.is_symlink():
                    symlink_target.unlink()
                    print(f"🔄 Removed incorrect symlink in {function_dir.name}")
                else:
                    print(f"⚠️  Warning: {symlink_target} exists but is not a symlink")
                    continue
        
        try:
            # Create the symlink
            symlink_target.symlink_to(layer_source, target_is_directory=True)
            print(f"🔗 Created {function_dir.name}/bars_common_utils -> {layer_source.relative_to(project_root)}")
            success_count += 1
            
        except OSError as e:
            print(f"❌ Failed to create symlink in {function_dir.name}: {e}")
    
    print()
    print(f"📊 Summary:")
    print(f"   ✅ Created: {success_count} symlinks")
    print(f"   ⏭️  Skipped: {skip_count} (already correct)")
    
    if success_count > 0:
        print()
        print("🎉 Local development setup complete!")
        print("   Your lambda functions can now import bars_common_utils locally.")
        print("   Example: from bars_common_utils.event_utils import parse_event_body")
    
    return True

def cleanup_lambda_layer_symlinks():
    """Remove all bars_common_utils symlinks from lambda function directories"""
    
    project_root = Path.cwd()
    lambda_functions_dir = project_root / "lambda-functions"
    
    if not lambda_functions_dir.exists():
        print(f"❌ Lambda functions directory not found at: {lambda_functions_dir}")
        return False
    
    print("🧹 Cleaning up lambda layer symlinks...")
    
    removed_count = 0
    
    for function_dir in lambda_functions_dir.iterdir():
        if not function_dir.is_dir():
            continue
        
        symlink_target = function_dir / "bars_common_utils"
        
        if symlink_target.exists() and symlink_target.is_symlink():
            symlink_target.unlink()
            print(f"🗑️  Removed {function_dir.name}/bars_common_utils")
            removed_count += 1
    
    print(f"📊 Removed {removed_count} symlinks")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        cleanup_lambda_layer_symlinks()
    else:
        setup_lambda_layer_symlinks() 