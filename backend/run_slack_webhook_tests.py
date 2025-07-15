#!/usr/bin/env python3
"""
Test runner for Slack webhook functionality
Run this to validate that Slack webhook interactions work correctly in debug mode
"""

import sys
import os
import subprocess

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_slack_webhook_tests():
    """Run the Slack webhook tests"""
    print("🧪 Running Slack Webhook Tests...")
    print("=" * 60)
    print("📋 Testing webhook functionality including:")
    print("   • Signature validation")
    print("   • Cancel order webhook actions")
    print("   • Process refund webhook actions")
    print("   • Restock inventory webhook actions")
    print("   • Debug mode message formatting")
    print("   • Message content validation")
    print("=" * 60)
    
    try:
        # Run the slack webhook tests
        result = subprocess.run([
            "python3", "-m", "pytest", 
            "routers/tests/test_slack_router.py", 
            "-v", "--tb=short"
        ], cwd=os.path.dirname(os.path.abspath(__file__)))
        
        if result.returncode == 0:
            print("\n✅ All Slack webhook tests passed!")
            print("🎯 Debug message formatting is working correctly")
            print("🔒 Webhook signature validation is working")
            print("📨 Message format matches expected debug environment output")
        else:
            print("\n❌ Some webhook tests failed!")
            print("⚠️  Slack webhook functionality may have issues")
            
        return result.returncode
        
    except FileNotFoundError:
        print("\n❌ pytest not found!")
        print("💡 Install pytest: pip install pytest")
        return 1
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        return 1

def run_all_slack_tests():
    """Run both webhook and message formatting tests"""
    print("🧪 Running ALL Slack Tests...")
    print("=" * 60)
    
    # First run webhook tests
    webhook_result = run_slack_webhook_tests()
    
    print("\n" + "=" * 60)
    
    # Then run message formatting tests
    try:
        print("🧪 Running Slack Message Formatting Tests...")
        format_result = subprocess.run([
            "python3", "-m", "pytest", 
            "tests/unit/test_slack_message_formatting.py", 
            "-v", "--tb=short"
        ], cwd=os.path.dirname(os.path.abspath(__file__)))
        
        if webhook_result == 0 and format_result.returncode == 0:
            print("\n🎉 ALL SLACK TESTS PASSED!")
            print("✅ Webhook functionality working")
            print("✅ Message formatting working") 
        else:
            print("\n❌ Some tests failed")
            
        return max(webhook_result, format_result.returncode)
        
    except Exception as e:
        print(f"\n❌ Error running message formatting tests: {e}")
        return 1

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        exit_code = run_all_slack_tests()
    else:
        exit_code = run_slack_webhook_tests()
    
    if exit_code == 0:
        print("\n🚀 Ready to test webhook functionality!")
        print("💡 To test all Slack functionality: python3 run_slack_webhook_tests.py --all")
    
    sys.exit(exit_code) 