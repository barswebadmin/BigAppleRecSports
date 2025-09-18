#!/bin/bash

# Test suite for instructions.gs functionality across all projects
# Verifies that each Google Apps Script project has proper instructions

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
    ((TESTS_FAILED++))
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

# List of all Google Apps Script projects that should have instructions
PROJECTS=(
    "projects/leadership-discount-codes"
    "projects/create-products-from-registration-info"
    "projects/process-refunds-exchanges"
    # "projects/payment-assistance-tags"  # temporarily excluded from CI
    "projects/veteran-tags"
)

# Test 1: Each project has instructions.gs file
for project in "${PROJECTS[@]}"; do
    run_test "$project has instructions.gs file" \
        "[ -f '$project/instructions.gs' ]"
done

# Test 2: Each instructions.gs contains showInstructions function
for project in "${PROJECTS[@]}"; do
    run_test "$project instructions contain showInstructions function" \
        "grep -q 'function showInstructions' '$project/instructions.gs'"
done

# Test 3: Each instructions.gs uses SpreadsheetApp.getUi().alert
for project in "${PROJECTS[@]}"; do
    run_test "$project instructions use SpreadsheetApp.getUi().alert" \
        "grep -q 'SpreadsheetApp.getUi().alert' '$project/instructions.gs'"
done

# Test 4: Each project's onOpen function calls showInstructions
for project in "${PROJECTS[@]}"; do
    case $project in
        "projects/leadership-discount-codes")
            file="$project/processors/leadershipProcessor.gs"
            ;;
        "projects/create-products-from-registration-info")
            file="$project/main.gs"
            ;;
        "projects/process-refunds-exchanges")
            file="$project/New.gs"
            ;;
        "projects/veteran-tags")
            file="$project/Add Menu Item to UI.gs"
            ;;
    esac
    
    run_test "$project onOpen function calls showInstructions" \
        "grep -q 'showInstructions()' '$file'"
done

# Test 5: Each project's menu includes "View Instructions" item
for project in "${PROJECTS[@]}"; do
    case $project in
        "projects/leadership-discount-codes")
            file="$project/processors/leadershipProcessor.gs"
            ;;
        "projects/create-products-from-registration-info")
            file="$project/main.gs"
            ;;
        "projects/process-refunds-exchanges")
            file="$project/New.gs"
            ;;
        "projects/veteran-tags")
            file="$project/Add Menu Item to UI.gs"
            ;;
    esac
    
    run_test "$project menu includes View Instructions item" \
        "grep -q 'View Instructions.*showInstructions' '$file'"
done

# Test 6: Instructions contain project-specific information
run_test "Leadership instructions mention discount codes" \
    "grep -q 'discount codes' projects/leadership-discount-codes/instructions.gs"

run_test "Product creation instructions mention variants" \
    "grep -q 'variants' projects/create-products-from-registration-info/instructions.gs"

run_test "Refunds instructions mention exchanges" \
    "grep -q 'exchanges\\|refund' projects/process-refunds-exchanges/instructions.gs"

# Skipping payment assistance instructions check in CI
# run_test "Payment assistance instructions mention tags" \
#     "grep -q 'tags\\|assistance' projects/payment-assistance-tags/instructions.gs"

run_test "Veteran instructions mention veteran tags" \
    "grep -q 'veteran' projects/veteran-tags/instructions.gs"

# (Removed) Emoji header checks – no longer required

echo ""
echo "📊 Test Results:"
echo "  🧪 Total Tests: $TESTS_RUN"
echo "  ✅ Passed: $TESTS_PASSED"
echo "  ❌ Failed: $TESTS_FAILED"

if [ $TESTS_FAILED -eq 0 ]; then
    echo ""
    log_pass "All instructions tests passed!"
    exit 0
else
    echo ""
    echo -e "${RED}❌ Some instructions tests failed!${NC}"
    exit 1
fi
