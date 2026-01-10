#!/usr/bin/env python3
"""
Test script for get_customer_details_pydantic.py

Tests various scenarios by calling main() with simulated command-line arguments,
testing against the production API.
"""

import sys
import json
import io
from contextlib import redirect_stdout, redirect_stderr
from typing import Dict, Any, List, Tuple, Optional
from unittest.mock import patch

# Import main function from the script
from get_customer_details_pydantic import main as main_function


def run_test_case(
    args: List[str],
    description: str = "",
    input_text: Optional[str] = None
) -> Tuple[bool, int, str, str]:
    """
    Run a test case by calling main() with simulated command-line arguments.
    
    Args:
        args: List of command-line arguments (e.g., ["--id", "123", "--json"])
        description: Test description
        input_text: Optional input to provide when script prompts for input
    
    Returns:
        (passed, exit_code, stdout, stderr)
    """
    print(f"\n{'='*80}")
    print(f"TEST: {description}")
    print(f"COMMAND: python get_customer_details_pydantic.py {' '.join(args)}")
    if input_text:
        print(f"INPUT: {input_text}")
    print(f"{'='*80}")
    
    # Save original argv
    original_argv = sys.argv.copy()
    
    try:
        # Set up sys.argv to simulate command-line arguments
        sys.argv = ["get_customer_details_pydantic.py"] + args
        
        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        # For multiple results that require input, we need to mock stdin
        # Patch input in the get_customer_details_pydantic module namespace
        if input_text:
            with patch('get_customer_details_pydantic.input', return_value=input_text.strip()):
                with redirect_stdout(stdout_capture):
                    with redirect_stderr(stderr_capture):
                        exit_code = main_function()
        else:
            with redirect_stdout(stdout_capture):
                with redirect_stderr(stderr_capture):
                    exit_code = main_function()
        
        stdout = stdout_capture.getvalue()
        stderr = stderr_capture.getvalue()
        
        # Print output for visibility
        if stdout:
            print(stdout)
        if stderr:
            print(stderr, file=sys.stderr)
        
        return True, exit_code, stdout, stderr
        
    except Exception as e:
        error_msg = f"Exception: {str(e)}"
        print(f"\n❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return False, 1, "", str(e)
    finally:
        # Restore original argv
        sys.argv = original_argv


def main():
    """Run all test scenarios."""
    tests_passed = 0
    tests_failed = 0
    test_results: List[Dict[str, Any]] = []
    
    # Test cases - each defines args directly
    test_cases = [
        # Valid ID tests
        {
            "description": "Valid ID (7836631203934) - non-JSON",
            "args": ["--id", "7836631203934"],
            "expected_exit": 0,
            "expected_contains": ["Customer Found", "Marouane", "Baiouak"]
        },
        {
            "description": "Valid ID (7836631203934) - JSON",
            "args": ["--json", "--id", "7836631203934"],
            "expected_exit": 0,
            "expected_contains": ["success", "true"]
        },
        
        # Invalid ID tests
        {
            "description": "Invalid ID (somethinginvalid) - non-JSON",
            "args": ["--id", "somethinginvalid"],
            "expected_exit": 1,
            "expected_contains": ["No customer found"]
        },
        {
            "description": "Invalid ID (somethinginvalid) - JSON",
            "args": ["--json", "--id", "somethinginvalid"],
            "expected_exit": 1,
            "expected_contains": ["success", "false"]
        },
        
        # Valid email tests
        {
            "description": "Valid email (jdazz87@gmail.com) - non-JSON",
            "args": ["--email", "jdazz87@gmail.com"],
            "expected_exit": 0,
            "expected_contains": ["Customer Found", "jdazz87@gmail.com"]
        },
        {
            "description": "Valid email (jdazz87@gmail.com) - JSON",
            "args": ["--json", "--email", "jdazz87@gmail.com"],
            "expected_exit": 0,
            "expected_contains": ["success", "true"]
        },
        
        # Invalid email tests
        {
            "description": "Invalid email (someinvalidemail@gmail.com) - non-JSON",
            "args": ["--email", "someinvalidemail@gmail.com"],
            "expected_exit": 1,
            "expected_contains": ["No customer found"]
        },
        {
            "description": "Invalid email (someinvalidemail@gmail.com) - JSON",
            "args": ["--json", "--email", "someinvalidemail@gmail.com"],
            "expected_exit": 1,
            "expected_contains": ["success", "false"]
        },
        
        # Single name search tests
        {
            "description": "Single name (marouane baiouak) - non-JSON",
            "args": ["marouane baiouak"],
            "expected_exit": 0,
            "expected_contains": ["Customer Found", "Marouane", "Baiouak"]
        },
        {
            "description": "Single name (marouane baiouak) - JSON",
            "args": ["--json", "marouane baiouak"],
            "expected_exit": 0,
            "expected_contains": ["success", "true"]
        },
        
        # Multiple results tests (name search) - COMMENTED OUT FOR NOW
        # {
        #     "description": "Multiple results (brian ramirez) - non-JSON",
        #     "args": ["brian", "ramirez"],
        #     "expected_exit": 0,
        #     "expected_contains": ["Found", "customers", "Brian", "Ramirez"],
        #     "input": "1"  # Select first customer
        # },
        # {
        #     "description": "Multiple results (brian ramirez) - JSON",
        #     "args": ["--json", "brian", "ramirez"],
        #     "expected_exit": 0,
        #     "expected_contains": ["success", "true", "Found"]
        # },
        
        # Invalid name tests
        {
            "description": "Invalid name (invalid invalid) - non-JSON",
            "args": ["invalid invalid"],
            "expected_exit": 1,
            "expected_contains": ["No customers found"]
        },
        {
            "description": "Invalid name (invalid invalid) - JSON",
            "args": ["--json", "invalid invalid"],
            "expected_exit": 1,
            "expected_contains": ["success", "false"]
        },
    ]
    
    # Run all tests
    for test_case in test_cases:
        passed, exit_code, stdout, stderr = run_test_case(
            args=test_case["args"],
            description=test_case["description"],
            input_text=test_case.get("input")
        )
        
        # Validate results
        issues = []
        
        # Check if test execution passed
        if not passed:
            issues.append(f"Test execution failed: {stderr}")
        else:
            # Check exit code
            expected_exit = test_case["expected_exit"]
            if exit_code != expected_exit:
                issues.append(f"Exit code mismatch: expected {expected_exit}, got {exit_code}")
            
            # Check for expected keywords in output
            if test_case.get("expected_contains"):
                output_text = (stdout + stderr).lower()
                for keyword in test_case["expected_contains"]:
                    if keyword.lower() not in output_text:
                        issues.append(f"Expected keyword '{keyword}' not found in output")
            
            # For JSON output, validate JSON format
            if "--json" in test_case["args"]:
                try:
                    json.loads(stdout)
                except json.JSONDecodeError:
                    issues.append("Output is not valid JSON")
        
        # Record result
        test_result = {
            "description": test_case["description"],
            "passed": len(issues) == 0,
            "exit_code": exit_code,
            "stdout_preview": stdout[:300] + "..." if len(stdout) > 300 else stdout,
            "stderr_preview": stderr[:300] + "..." if len(stderr) > 300 else stderr,
            "issues": issues
        }
        test_results.append(test_result)
        
        if len(issues) == 0:
            tests_passed += 1
            print(f"✅ PASSED")
        else:
            tests_failed += 1
            print(f"❌ FAILED")
            for issue in issues:
                print(f"   - {issue}")
    
    # Summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Total tests: {len(test_cases)}")
    print(f"✅ Passed: {tests_passed}")
    print(f"❌ Failed: {tests_failed}")
    print(f"{'='*80}\n")
    
    # Detailed results for failed tests
    if tests_failed > 0:
        print("FAILED TESTS:")
        for result in test_results:
            if not result["passed"]:
                print(f"\n  ❌ {result['description']}")
                print(f"     Exit code: {result['exit_code']}")
                for issue in result["issues"]:
                    print(f"     - {issue}")
                if result["stdout_preview"]:
                    print(f"     STDOUT: {result['stdout_preview']}")
                if result["stderr_preview"]:
                    print(f"     STDERR: {result['stderr_preview']}")
    
    return 0 if tests_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
