#!/usr/bin/env python3
"""
Setup script for local development of BARS Lambda Functions.

This script installs required dependencies for local development and testing.

🎯 DRY Architecture:
- Uses workspace-level VS Code configuration for IDE support
- Single symlink in tests/ directory for test execution
- No code duplication across lambda functions
- Clean, maintainable project structure
"""

import subprocess
import sys
from pathlib import Path


def install_dependencies():
    """Install required dependencies for local development."""
    dependencies = [
        'boto3>=1.39.0',
        'pytest>=7.0.0',
        'pytest-asyncio>=0.23.0',
        'flake8>=7.0.0',
        'coverage[toml]>=7.0.0'
    ]
    
    print("📦 Installing local development dependencies...")
    for dep in dependencies:
        try:
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'install', dep
            ], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"  ✅ {dep}")
            else:
                print(f"  ⚠️  Failed to install {dep}")
        except Exception:
            print(f"  ⚠️  Failed to install {dep}")
    
    print("\n✅ Dependencies installation complete!")


def verify_setup():
    """Verify that the setup is working correctly."""
    print("\n🔍 Verifying setup...")
    
    # Test import resolution
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root / "lambda-layers" / "bars-common-utils" / "python"))
    sys.path.insert(0, str(project_root / "lambda-functions" / "MoveInventoryLambda"))
    
    try:
        from bars_common_utils.date_utils import parse_date  # type: ignore
        print("  ✅ bars_common_utils imports working")
    except ImportError as e:
        print(f"  ❌ bars_common_utils import failed: {e}")
        return False
    
    try:
        from lambda_function import lambda_handler  # type: ignore
        print("  ✅ lambda_function imports working")
    except ImportError as e:
        print(f"  ❌ lambda_function import failed: {e}")
        return False
    
    return True


def setup_test_symlink():
    """Create symlink for test directory if needed."""
    project_root = Path(__file__).parent.parent
    tests_dir = project_root / "lambda-functions" / "tests"
    symlink_path = tests_dir / "bars_common_utils"
    target_path = project_root / "lambda-layers" / "bars-common-utils" / "python" / "bars_common_utils"
    
    if not tests_dir.exists():
        print("  ⏭️  Tests directory not found, skipping symlink setup")
        return True
    
    if symlink_path.exists():
        if symlink_path.is_symlink() and symlink_path.resolve() == target_path.resolve():
            print("  ✅ Test symlink already correct")
            return True
        else:
            print("  🔄 Removing incorrect symlink")
            symlink_path.unlink()
    
    try:
        symlink_path.symlink_to(target_path)
        print("  🔗 Created test symlink for bars_common_utils")
        return True
    except OSError as e:
        print(f"  ⚠️  Could not create test symlink: {e}")
        return False


def main():
    """Main setup function."""
    print("🚀 BARS Lambda Functions - Local Development Setup")
    print("=" * 60)
    print("🎯 DRY Architecture: One source of truth, workspace configuration")
    print()
    
    install_dependencies()
    setup_test_symlink()
    
    if verify_setup():
        print("\n🎉 Setup completed successfully!")
        print("\n📋 Next steps:")
        print("  1. Open the project in VS Code")
        print("  2. Workspace-level configuration handles import resolution")
        print("  3. Single symlink in tests/ enables test execution")
        print("  4. Run tests: cd lambda-functions/tests && python3 run_tests.py")
        print("  5. All lambda functions have full IDE support")
        print("\n✨ Benefits:")
        print("  • No code duplication (DRY)")
        print("  • Clean project structure")
        print("  • Full IDE IntelliSense")
        print("  • Easy maintenance")
    else:
        print("\n⚠️  Setup completed with warnings. Check error messages above.")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 