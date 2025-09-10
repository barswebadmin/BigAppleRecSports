#!/usr/bin/env python3
"""
Integration Test Runner for End-to-End Refund Flows

This script provides an easy way to run specific test scenarios
or all integration tests for the refund system.
"""

import sys
import subprocess
from typing import List, Optional

def run_pytest_command(args: List[str]) -> int:
    """Run pytest with the given arguments and return exit code."""
    cmd = ["python", "-m", "pytest"] + args
    print(f"Running: {' '.join(cmd)}")
    print("=" * 60)
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode
    except Exception as e:
        print(f"Error running pytest: {e}")
        return 1

def run_specific_scenario(scenario_name: str) -> int:
    """Run a specific test scenario."""
    test_file = "tests/integration/test_end_to_end_refund_flows.py"
    
    scenario_map = {
        # Initial Request Flows
        "invalid_order": "test_invalid_order_number_flow",
        "email_mismatch": "test_email_mismatch_flow", 
        "duplicate_pending": "test_duplicate_refund_pending_flow",
        "valid_refund": "test_valid_refund_request_early_timing",
        "valid_credit": "test_valid_credit_request_early_timing",
        
        # Timing Tier Tests
        "timing_tiers": "test_refund_timing_tiers",
        
        # Order Cancellation Flows
        "cancel_order": "test_cancel_order_button_flow",
        "proceed_no_cancel": "test_proceed_without_cancel_flow",
        
        # Refund Processing Flows
        "process_refund": "test_process_refund_flow",
        "no_refund": "test_no_refund_flow",
        
        # Inventory Restock Flows
        "restock": "test_restock_inventory_flow",
        "no_restock": "test_do_not_restock_flow",
        
        # Denial Flows
        "deny_modal": "test_deny_request_modal_flow",
        "deny_submit": "test_deny_request_submission_flow",
        
        # Error Handling
        "cancel_error": "test_order_cancellation_failure",
        "refund_error": "test_refund_creation_failure",
        
        # Update Request Details
        "edit_modal": "test_edit_request_details_modal",
        "edit_success": "test_edit_request_details_success_submission",
        
        # Message Consistency
        "message_consistency": "test_message_format_consistency",
        "refund_vs_credit": "test_refund_vs_credit_message_differences"
    }
    
    if scenario_name not in scenario_map:
        print(f"❌ Unknown scenario: {scenario_name}")
        print(f"Available scenarios: {', '.join(scenario_map.keys())}")
        return 1
    
    test_method = scenario_map[scenario_name]
    return run_pytest_command(["-v", "-k", test_method, test_file])

def run_category(category: str) -> int:
    """Run all tests in a specific category."""
    test_file = "tests/integration/test_end_to_end_refund_flows.py"
    
    category_map = {
        "initial": "test_invalid_order_number_flow or test_email_mismatch_flow or test_duplicate_refund_pending_flow or test_valid_refund_request_early_timing or test_valid_credit_request_early_timing",
        "timing": "test_refund_timing_tiers",
        "cancellation": "test_cancel_order_button_flow or test_proceed_without_cancel_flow",
        "processing": "test_process_refund_flow or test_no_refund_flow",
        "restock": "test_restock_inventory_flow or test_do_not_restock_flow",
        "denial": "test_deny_request_modal_flow or test_deny_request_submission_flow",
        "errors": "test_order_cancellation_failure or test_refund_creation_failure",
        "updates": "test_edit_request_details_modal or test_edit_request_details_success_submission",
        "consistency": "test_message_format_consistency or test_refund_vs_credit_message_differences"
    }
    
    if category not in category_map:
        print(f"❌ Unknown category: {category}")
        print(f"Available categories: {', '.join(category_map.keys())}")
        return 1
    
    test_pattern = category_map[category]
    return run_pytest_command(["-v", "-k", test_pattern, test_file])

def run_all_integration_tests() -> int:
    """Run all integration tests."""
    test_file = "tests/integration/test_end_to_end_refund_flows.py"
    return run_pytest_command(["-v", test_file])

def show_help():
    """Show usage help."""
    print("""
Integration Test Runner for End-to-End Refund Flows
==================================================

Usage:
    python run_integration_tests.py [command] [argument]

Commands:
    all                     Run all integration tests
    scenario <name>         Run a specific test scenario
    category <name>         Run all tests in a category
    help                    Show this help message

Scenarios:
    initial request flows:
        invalid_order       - Order not found (406)
        email_mismatch      - Email doesn't match order (409)
        duplicate_pending   - Duplicate refund with pending amount
        valid_refund        - Valid refund request (early timing)
        valid_credit        - Valid credit request (early timing)
    
    timing tiers:
        timing_tiers        - All refund timing calculations
    
    order cancellation:
        cancel_order        - Cancel order button flow
        proceed_no_cancel   - Proceed without canceling flow
    
    refund processing:
        process_refund      - Process refund button flow
        no_refund           - Do not provide refund flow
    
    inventory management:
        restock             - Restock inventory flow
        no_restock          - Do not restock flow
    
    denial flows:
        deny_modal          - Deny request modal opening
        deny_submit         - Deny request submission
    
    error handling:
        cancel_error        - Order cancellation failure
        refund_error        - Refund creation failure
    
    update flows:
        edit_modal          - Edit request details modal
        edit_success        - Successful edit submission
    
    message consistency:
        message_consistency - Verify message format consistency
        refund_vs_credit    - Verify refund vs credit differences

Categories:
    initial             - All initial request flows
    timing              - Timing tier tests
    cancellation        - Order cancellation flows
    processing          - Refund processing flows
    restock             - Inventory restock flows
    denial              - Denial flows
    errors              - Error handling tests
    updates             - Update request details flows
    consistency         - Message consistency tests

Examples:
    python run_integration_tests.py all
    python run_integration_tests.py scenario invalid_order
    python run_integration_tests.py category initial
    """)

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        show_help()
        return 1
    
    command = sys.argv[1].lower()
    
    if command == "help":
        show_help()
        return 0
    elif command == "all":
        return run_all_integration_tests()
    elif command == "scenario":
        if len(sys.argv) < 3:
            print("❌ Scenario name required")
            return 1
        return run_specific_scenario(sys.argv[2])
    elif command == "category":
        if len(sys.argv) < 3:
            print("❌ Category name required") 
            return 1
        return run_category(sys.argv[2])
    else:
        print(f"❌ Unknown command: {command}")
        show_help()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
