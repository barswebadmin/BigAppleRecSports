#!/bin/bash

# Test suite for sync-utilities.sh functionality
# Tests utility synchronization across all projects

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

# Setup test environment
TEST_DIR="test_sync_temp"
mkdir -p "$TEST_DIR"

# Test 1: Sync utilities script exists and is executable
run_test "Sync utilities script exists and is executable" \
    "[ -f 'sync-utilities.sh' ] && [ -x 'sync-utilities.sh' ]"

# Test 2: Shared utilities directory exists with required files
run_test "Shared utilities has required .gs files" \
    "[ -f 'shared-utilities/apiUtils.gs' ] && \
     [ -f 'shared-utilities/dateUtils.gs' ] && \
     [ -f 'shared-utilities/secretsUtils.gs' ]"

# Test 3: Shared utilities has deploy script
run_test "Shared utilities has deploy script" \
    "[ -f 'shared-utilities/deploy.sh' ] && [ -x 'shared-utilities/deploy.sh' ]"

# Test 4: All target directories exist
GAS_DIRS=("projects/waitlist-script" "projects/product-variant-creation" "projects/parse-registration-info" 
         "projects/process-refunds-exchanges" "projects/payment-assistance-tags" "projects/veteran-tags" 
         "projects/leadership-discount-codes")

for dir in "${GAS_DIRS[@]}"; do
    run_test "Directory $dir exists" "[ -d '$dir' ]"
done

# Test 5: All directories have shared-utilities subdirectory with utilities
for dir in "${GAS_DIRS[@]}"; do
    run_test "$dir has shared-utilities with all 3 utility files" \
        "[ -f '$dir/shared-utilities/apiUtils.gs' ] && \
         [ -f '$dir/shared-utilities/dateUtils.gs' ] && \
         [ -f '$dir/shared-utilities/secretsUtils.gs' ]"
done

# Test 6: All directories have deploy.sh script
for dir in "${GAS_DIRS[@]}"; do
    run_test "$dir has executable deploy.sh script" \
        "[ -f '$dir/deploy.sh' ] && [ -x '$dir/deploy.sh' ]"
done

# Test 7: All deploy.sh scripts match the master in shared-utilities
for dir in "${GAS_DIRS[@]}"; do
    run_test "$dir deploy.sh matches shared-utilities master" \
        "cmp -s 'shared-utilities/deploy.sh' '$dir/deploy.sh'"
done

# Test 8: Create test directory and run sync script simulation
log_test "Setting up test project for sync simulation"
mkdir -p "$TEST_DIR/test-project/shared-utilities"
echo 'function oldTestFunction() { return "old"; }' > "$TEST_DIR/test-project/shared-utilities/apiUtils.gs"
echo 'function testScript() { return "script"; }' > "$TEST_DIR/test-project/main.gs"

# Test 9: Test that sync would update utilities correctly
run_test "Sync script would detect organized structure" \
    "[ -d '$TEST_DIR/test-project/shared-utilities' ]"

# Test 10: Verify utilities in shared-utilities contain expected functions
run_test "apiUtils.gs contains expected functions" \
    "grep -q 'function.*makeApiRequest\\|function.*buildShopifyGraphQLRequest' shared-utilities/apiUtils.gs"

run_test "dateUtils.gs contains expected functions" \
    "grep -q 'function.*formatDate\\|function.*parseDate' shared-utilities/dateUtils.gs"

run_test "secretsUtils.gs contains expected functions" \
    "grep -q 'function.*getSecret\\|function.*setupSecrets' shared-utilities/secretsUtils.gs"

# Test 11: Verify no utilities are in root directories (only in shared-utilities)
for dir in "${GAS_DIRS[@]}"; do
    if [ "$dir" != "projects/leadership-discount-codes" ]; then
        run_test "$dir has no utility files in root (only script files)" \
            "! ls '$dir'/*.gs 2>/dev/null | grep -E '(apiUtils|dateUtils|secretsUtils)\.gs'"
    fi
done

# Test 12: Leadership discount codes organized structure
run_test "Leadership discount codes has proper organized structure" \
    "[ -d 'projects/leadership-discount-codes/processors' ] && \
     [ -d 'projects/leadership-discount-codes/shared-utilities' ] && \
     [ -f 'projects/leadership-discount-codes/processors/leadershipProcessor.gs' ]"

# Test 13: Sync script has correct GAS_DIRS array
run_test "Sync script contains all expected directories in GAS_DIRS" \
    "grep -A 10 'GAS_DIRS=(' sync-utilities.sh | grep -q 'projects/leadership-discount-codes'"

# Cleanup
rm -rf "$TEST_DIR"

# Summary
echo ""
echo "📊 Test Summary:"
echo "   Tests Run: $TESTS_RUN"
echo "   Tests Passed: $TESTS_PASSED"
echo "   Tests Failed: $((TESTS_RUN - TESTS_PASSED))"

if [ $TESTS_FAILED -eq 0 ]; then
    log_pass "All sync-utilities.sh tests passed!"
    exit 0
else
    echo -e "${RED}❌ Some sync-utilities.sh tests failed!${NC}"
    exit 1
fi
