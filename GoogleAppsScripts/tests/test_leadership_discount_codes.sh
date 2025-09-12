#!/bin/bash

# Test suite for leadership-discount-codes functionality
# Tests core functions and structure

cd "$(dirname "$0")/.."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

function log_test() {
    echo -e "${BLUE}🧪 TEST: $1${NC}"
}

function log_pass() {
    echo -e "${GREEN}✅ PASS: $1${NC}"
}

function log_fail() {
    echo -e "${RED}❌ FAIL: $1${NC}"
    TESTS_FAILED=1
}

function log_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

function run_test() {
    local test_name="$1"
    local test_command="$2"
    
    ((TESTS_RUN++))
    log_test "$test_name"
    
    if eval "$test_command"; then
        log_pass "$test_name"
        ((TESTS_PASSED++))
    else
        log_fail "$test_name"
    fi
}

# Test 1: Leadership discount codes directory structure
run_test "Leadership directory has organized structure" \
    "[ -d 'projects/projects/leadership-discount-codes/processors' ] && \
     [ -d 'projects/projects/leadership-discount-codes/shared-utilities' ] && \
     [ -f 'projects/projects/leadership-discount-codes/clasp_helpers.sh' ] && \
     [ -f 'projects/projects/leadership-discount-codes/appsscript.json' ]"

# Test 2: Main processor file exists and has expected functions
run_test "Main processor file exists with core functions" \
    "[ -f 'projects/leadership-discount-codes/processors/leadershipProcessor.gs' ] && \
     grep -q 'function processLeadershipDiscountsSmartCSV' projects/leadership-discount-codes/processors/leadershipProcessor.gs && \
     grep -q 'function processLeadershipDiscountsWithHeaderPrompt' projects/leadership-discount-codes/processors/leadershipProcessor.gs && \
     grep -q 'function onOpen' projects/leadership-discount-codes/processors/leadershipProcessor.gs"

# Test 3: Processor file has backend integration
run_test "Processor has backend integration functions" \
    "grep -q 'function sendCSVToBackend' projects/leadership-discount-codes/processors/leadershipProcessor.gs && \
     grep -q 'function testBackendConnection' projects/leadership-discount-codes/processors/leadershipProcessor.gs && \
     grep -q 'getBackendUrl' projects/leadership-discount-codes/processors/leadershipProcessor.gs"

# Test 4: Shared utilities are properly organized
run_test "Shared utilities contain required files" \
    "[ -f 'projects/leadership-discount-codes/shared-utilities/apiUtils.gs' ] && \
     [ -f 'projects/leadership-discount-codes/shared-utilities/dateUtils.gs' ] && \
     [ -f 'projects/leadership-discount-codes/shared-utilities/secretsUtils.gs' ]"

# Test 5: Secrets utilities has required functions
run_test "Secrets utils has secret management functions" \
    "grep -q 'function getSecret' projects/leadership-discount-codes/shared-utilities/secretsUtils.gs && \
     grep -q 'function getBackendUrl' projects/leadership-discount-codes/shared-utilities/secretsUtils.gs && \
     grep -q 'function getSlackBotToken' projects/leadership-discount-codes/shared-utilities/secretsUtils.gs && \
     grep -q 'function setupSecrets' projects/leadership-discount-codes/shared-utilities/secretsUtils.gs"

# Test 6: API utils has required functions
run_test "API utils has helper functions" \
    "grep -q 'function makeApiCall\\|function.*Api' projects/leadership-discount-codes/shared-utilities/apiUtils.gs"

# Test 7: Date utils has required functions  
run_test "Date utils has date helper functions" \
    "grep -q 'function.*Date\\|function.*Time' projects/leadership-discount-codes/shared-utilities/dateUtils.gs"

# Test 8: Apps Script manifest is valid JSON
run_test "Apps Script manifest is valid JSON" \
    "python3 -m json.tool projects/leadership-discount-codes/appsscript.json > /dev/null 2>&1"

# Test 9: Clasp helper script is executable and has correct functions
run_test "Clasp helper script is executable with required functions" \
    "[ -x 'projects/leadership-discount-codes/clasp_helpers.sh' ] && \
     grep -q 'function prepare_for_gas' projects/leadership-discount-codes/clasp_helpers.sh && \
     grep -q 'function push_to_gas' projects/leadership-discount-codes/clasp_helpers.sh"

# Test 10: No hardcoded secrets in processor (should use getSecret)
run_test "No hardcoded secrets in processor file" \
    "! grep -E '(shpat_|xoxb-|https://hooks.slack.com)' projects/leadership-discount-codes/processors/leadershipProcessor.gs"

# Test 11: Processor uses secret helper functions
run_test "Processor uses secret helper functions instead of hardcoded values" \
    "grep -q 'getBackendUrl\\|getSecret\\|getSlackBotToken' projects/leadership-discount-codes/processors/leadershipProcessor.gs"

# Test 12: Menu creation function exists and is properly structured
run_test "Menu creation function exists and creates BARS Leadership menu" \
    "grep -A 10 'function onOpen' projects/leadership-discount-codes/processors/leadershipProcessor.gs | grep -q 'BARS Leadership'"

# Test 13: CSV processing functions handle errors properly
run_test "CSV processing functions have error handling" \
    "grep -q 'try {' projects/leadership-discount-codes/processors/leadershipProcessor.gs && \
     grep -q 'catch' projects/leadership-discount-codes/processors/leadershipProcessor.gs && \
     grep -q 'throw new Error\\|console.error\\|Logger.log.*Error' projects/leadership-discount-codes/processors/leadershipProcessor.gs"

# Test 14: Backend communication includes proper headers
run_test "Backend communication includes proper headers" \
    "grep -B 15 'UrlFetchApp.fetch' projects/leadership-discount-codes/processors/leadershipProcessor.gs | grep -q 'Content-Type.*application/json'"

# Test 15: Test clasp helper script prepare function (without actually deploying)
run_test "Clasp helper script prepare function works correctly" \
    "cd projects/leadership-discount-codes && \
     bash -c 'source ./clasp_helpers.sh && prepare_for_gas && \
     [ -d .deploy_temp ] && \
     [ -f .deploy_temp/appsscript.json ] && \
     ls .deploy_temp/ | grep -q processors'"

# Cleanup any temp files from tests
rm -rf projects/leadership-discount-codes/.deploy_temp

# Summary
echo ""
echo "📊 Test Summary:"
echo "   Tests Run: $TESTS_RUN"
echo "   Tests Passed: $TESTS_PASSED"
echo "   Tests Failed: $((TESTS_RUN - TESTS_PASSED))"

if [ $TESTS_FAILED -eq 0 ]; then
    log_pass "All leadership-discount-codes tests passed!"
    exit 0
else
    echo -e "${RED}❌ Some leadership-discount-codes tests failed!${NC}"
    exit 1
fi
