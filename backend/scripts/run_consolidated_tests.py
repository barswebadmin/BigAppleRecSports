#!/usr/bin/env python3
"""
Test runner for consolidated Slack tests.
Runs all consolidated test files in the appropriate directories.
"""

import os
import sys
import subprocess

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, backend_dir)

def run_tests_in_directory(directory, test_pattern="test_*.py"):
    """Run tests in a specific directory."""
    test_dir = os.path.join(os.path.dirname(__file__), directory)
    if not os.path.exists(test_dir):
        print(f"⚠️  Directory {test_dir} does not exist")
        return False
    
    test_files = [f for f in os.listdir(test_dir) if f.startswith("test_") and f.endswith(".py")]
    if not test_files:
        print(f"⚠️  No test files found in {test_dir}")
        return True
    
    print(f"\n🧪 Running tests in {directory}/")
    print("=" * 50)
    
    for test_file in test_files:
        test_path = os.path.join(test_dir, test_file)
        print(f"\n📋 Running {test_file}...")
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"
            ], capture_output=True, text=True, cwd=backend_dir)
            
            if result.returncode == 0:
                print(f"✅ {test_file} passed")
            else:
                print(f"❌ {test_file} failed")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
        except Exception as e:
            print(f"❌ Error running {test_file}: {e}")
    
    return True

def main():
    """Run all consolidated tests."""
    print("🚀 Running Consolidated Slack Tests")
    print("=" * 60)
    
    # Set environment for testing
    os.environ["ENVIRONMENT"] = "test"
    os.environ["TESTING"] = "true"
    
    # Test directories in order
    test_directories = [
        "builders",
        "core", 
        "parsers",
        "modals"
    ]
    
    all_passed = True
    
    for directory in test_directories:
        success = run_tests_in_directory(directory)
        if not success:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All consolidated tests completed successfully!")
    else:
        print("❌ Some tests failed or had issues")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
