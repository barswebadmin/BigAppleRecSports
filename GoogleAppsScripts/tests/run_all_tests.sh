#!/bin/bash

# Master test runner for all GoogleAppsScripts tests
# Runs all test suites and provides summary

set -e
cd "$(dirname "$0")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

function log_header() {
    echo -e "${BLUE}$1${NC}"
    echo "=========================================================================================="
}

function log_pass() {
    echo -e "${GREEN}✅ $1${NC}"
}

function log_fail() {
    echo -e "${RED}❌ $1${NC}"
}

function log_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Test suite results
TOTAL_SUITES=0
PASSED_SUITES=0
FAILED_SUITES=()

function run_test_suite() {
    local suite_name="$1"
    local script_path="$2"
    
    ((TOTAL_SUITES++))
    
    log_header "Running $suite_name"
    
    if $script_path; then
        log_pass "$suite_name completed successfully"
        ((PASSED_SUITES++))
        echo ""
    else
        log_fail "$suite_name failed"
        FAILED_SUITES+=("$suite_name")
        echo ""
    fi
}

# Start test execution
log_header "🧪 GoogleAppsScripts Test Suite Runner"
echo "Starting comprehensive test execution..."
echo ""

# Run all test suites
run_test_suite "Deploy Script Tests" "./test_deploy.sh"
run_test_suite "Sync Utilities Tests" "./test_sync_utilities.sh" 
run_test_suite "Leadership Discount Codes Tests" "./test_leadership_discount_codes.sh"
run_test_suite "Parse Registration Functions Tests" "./test_parse_registration_functions.sh"
run_test_suite "Parse Registration Comprehensive Tests" "./test_parse_registration_comprehensive.sh"
run_test_suite "Process Refunds & Exchanges GAS Tests" "./process-refunds-exchanges/run_tests.sh"
run_test_suite "Instructions Tests" "./test_instructions.sh"

# Final summary
log_header "📊 Final Test Results Summary"
echo "Total Test Suites: $TOTAL_SUITES"
echo "Passed: $PASSED_SUITES"
echo "Failed: $((TOTAL_SUITES - PASSED_SUITES))"
echo ""

if [ $PASSED_SUITES -eq $TOTAL_SUITES ]; then
    log_pass "🎉 ALL TEST SUITES PASSED!"
    echo ""
    log_info "✨ GoogleAppsScripts codebase is ready for deployment!"
    exit 0
else
    log_fail "❌ SOME TEST SUITES FAILED!"
    echo ""
    echo "Failed suites:"
    for suite in "${FAILED_SUITES[@]}"; do
        echo "  • $suite"
    done
    echo ""
    log_info "🔧 Please fix the failing tests before deploying."
    exit 1
fi
