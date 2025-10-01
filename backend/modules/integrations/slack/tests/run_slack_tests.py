#!/usr/bin/env python3
"""
Simple test runner for Slack message formatting tests
Run this to validate that Slack message formatting behavior is consistent
"""

import sys
import os
import subprocess

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_slack_tests():
    """Run the Slack message formatting tests"""
    print("🧪 Running Slack Message Formatting Tests...")
    print("=" * 60)
    
    try:
        # Try to run with python3 -m pytest (more reliable than direct pytest command)
        result = subprocess.run([
            "python3", "-m", "pytest", 
            "tests/unit/test_slack_message_formatting.py", 
            "-v", "--tb=short"
        ], cwd=os.path.dirname(os.path.abspath(__file__)))
        
        if result.returncode == 0:
            print("\n✅ All Slack message formatting tests passed!")
            print("🎯 Behavior-driven development consistency maintained")
        else:
            print("\n❌ Some tests failed!")
            print("⚠️  Slack message formatting behavior may have changed")
            
        return result.returncode
        
    except FileNotFoundError:
        print("\n❌ pytest not found!")
        print("💡 Install pytest: pip install pytest")
        return 1
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        return 1

if __name__ == "__main__":
    exit_code = run_slack_tests()
    sys.exit(exit_code) 