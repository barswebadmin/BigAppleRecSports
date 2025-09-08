#!/bin/bash

# Test suite for deploy.sh functionality
# Tests both root-level and shared-utilities deploy scripts

cd "$(dirname "$0")/.."
SCRIPT_ROOT="$(pwd)"

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

# Setup test environment
TEST_DIR="test_deploy_temp"
mkdir -p "$TEST_DIR"

# Test 1: Root deploy.sh exists and is executable
run_test "Root deploy.sh exists and is executable" \
    "[ -f 'deploy.sh' ] && [ -x 'deploy.sh' ]"

# Test 2: Shared utilities deploy.sh exists and is executable  
run_test "Shared utilities deploy.sh exists and is executable" \
    "[ -f 'shared-utilities/deploy.sh' ] && [ -x 'shared-utilities/deploy.sh' ]"

# Test 3: Root and shared-utilities deploy.sh are identical
run_test "Root and shared-utilities deploy.sh are identical" \
    "cmp -s 'deploy.sh' 'shared-utilities/deploy.sh'"

# Test 4: Deploy script has required functions
run_test "Deploy script contains required functions" \
    "grep -q 'function prepare_for_gas' shared-utilities/deploy.sh && \
     grep -q 'function push_to_gas' shared-utilities/deploy.sh && \
     grep -q 'function organize_from_gas' shared-utilities/deploy.sh"

# Test 5: Deploy script has help command
run_test "Deploy script has help functionality" \
    "grep -q 'function show_help' shared-utilities/deploy.sh"

# Test 6: Test deploy script help output (without actually running clasp)
run_test "Deploy script help shows correct commands" \
    "cd $TEST_DIR && ../shared-utilities/deploy.sh help | grep -q 'push' && \
     ../shared-utilities/deploy.sh help | grep -q 'pull' && \
     ../shared-utilities/deploy.sh help | grep -q 'deploy' && \
     ../shared-utilities/deploy.sh help | grep -q 'status'"

# Test 7: Create a test directory structure for organized project
log_test "Setting up test organized project structure"
mkdir -p "$TEST_DIR/test-project/shared-utilities"
mkdir -p "$TEST_DIR/test-project/processors"
echo 'function testFunction() { return "test"; }' > "$TEST_DIR/test-project/shared-utilities/testUtils.gs"
echo 'function mainProcessor() { return "main"; }' > "$TEST_DIR/test-project/processors/main.gs"
echo '{"timeZone": "America/New_York"}' > "$TEST_DIR/test-project/appsscript.json"
cp ../shared-utilities/deploy.sh "$TEST_DIR/test-project/"
chmod +x "$TEST_DIR/test-project/deploy.sh"

# Test 8: Test deploy script prepare_for_gas function
run_test "Deploy script prepare_for_gas creates temp structure correctly" \
    "cd $TEST_DIR/test-project && \
     bash -c 'source ./deploy.sh && prepare_for_gas && \
     [ -f .deploy_temp/appsscript.json ] && \
     [ -f \".deploy_temp/shared-utilities/testUtils.gs\" ] && \
     [ -f \".deploy_temp/processors/main.gs\" ]'"

# Test 9: Verify deploy script handles missing .clasp.json gracefully
run_test "Deploy script handles missing .clasp.json gracefully" \
    "(cd \"\$SCRIPT_ROOT\" && rm -rf test_clasp_temp && mkdir -p test_clasp_temp && cd test_clasp_temp && \
     cp ../shared-utilities/deploy.sh . && chmod +x deploy.sh && \
     echo '{\"timeZone\": \"America/New_York\"}' > appsscript.json && \
     ./deploy.sh push 2>&1 | grep -q '.clasp.json not found')"

# Test 10: Leadership discount codes directory has proper structure
run_test "Leadership discount codes has organized structure" \
    "(cd \"\$SCRIPT_ROOT\" && [ -d 'projects/leadership-discount-codes/shared-utilities' ] && \
     [ -d 'projects/leadership-discount-codes/processors' ] && \
     [ -f 'projects/leadership-discount-codes/deploy.sh' ])"

# Cleanup
rm -rf "$TEST_DIR"

# Summary
echo ""
echo "📊 Test Summary:"
echo "   Tests Run: $TESTS_RUN"
echo "   Tests Passed: $TESTS_PASSED"
echo "   Tests Failed: $((TESTS_RUN - TESTS_PASSED))"

if [ $TESTS_FAILED -eq 0 ]; then
    log_pass "All deploy.sh tests passed!"
    exit 0
else
    echo -e "${RED}❌ Some deploy.sh tests failed!${NC}"
    exit 1
fi
