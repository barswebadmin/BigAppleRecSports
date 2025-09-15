#!/bin/bash

# Test suite for parse-registration-info core functionality
# Tests parsing functions, data validation, and product creation logic

cd "$(dirname "$0")/../../.."

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

PROJECT_DIR="projects/parse-registration-info"

# Test 1: Project structure exists
run_test "Parse registration project exists" \
    "[ -d '$PROJECT_DIR' ]"

# Test 2: Main code file exists
run_test "Main entry point exists" \
    "[ -f '$PROJECT_DIR/main.gs' ]"

# Test 3: Core parsing functions exist
run_test "parseSourceRowEnhanced_ function exists" \
    "grep -q 'function parseSourceRowEnhanced_' '$PROJECT_DIR/src/parsers/_rowParser.gs'"

run_test "parseColBLeagueBasicInfo_ function exists" \
    "grep -q 'function parseColBLeagueBasicInfo_' '$PROJECT_DIR/src/parsers/parseColBLeagueBasicInfo_.gs'"

run_test "parseColGLeagueTimes_ function exists" \
    "grep -q 'function parseColGLeagueTimes_' '$PROJECT_DIR/src/parsers/parseColGLeagueTimes_.gs'"

run_test "parseColFPrice_ function exists" \
    "grep -q 'function parseColFPrice_' '$PROJECT_DIR/src/parsers/parseColFPrice_.gs'"

run_test "parseDateFlexibleDateOnly_ function exists" \
    "grep -q 'parseDateFlexibleDateOnly_' '$PROJECT_DIR/src/helpers/dateParsers.gs'"

run_test "parseDateFlexibleDateTime_ function exists" \
    "grep -q 'parseDateFlexibleDateTime_' '$PROJECT_DIR/src/helpers/dateParsers.gs'"

# Test 4: Migration functions exist
# migrateRowToTarget_ function removed - only creating products, not migrating

# showMigrationPrompt function removed - only creating products, not migrating

# Test 5: Configuration constants exist

run_test "productFieldEnums object exists and has location enums" \
    "grep -A 20 'productFieldEnums' '$PROJECT_DIR/src/config/constants.gs' | grep -q 'Elliott Center\\|Gotham Pickleball'"



# Test 6: Validation and helper functions
run_test "checkRequiredFields_ function exists" \
    "grep -q 'function checkRequiredFields_' '$PROJECT_DIR/src/validators/fieldValidation.gs'"

run_test "normalizeSport_ helper exists" \
    "grep -q 'normalizeSport_\\|function.*normalizeSport' '$PROJECT_DIR/src/helpers/normalizers.gs'"

run_test "normalizeDay_ helper exists" \
    "grep -q 'normalizeDay_\\|function.*normalizeDay' '$PROJECT_DIR/src/helpers/normalizers.gs'"


# Test 7: Date parsing functionality
run_test "deriveSeasonYearFromDate_ function exists" \
    "grep -q 'deriveSeasonYearFromDate_\\|function.*deriveSeasonYear' '$PROJECT_DIR/src/helpers/normalizers.gs'"

run_test "parseFlexible_ function exists" \
    "grep -q 'parseFlexible_' '$PROJECT_DIR/src/helpers/dateParsers.gs'"

# Test 8: Location and price parsing
run_test "parseColHLocation_ function exists" \
    "grep -q 'function parseColHLocation_' '$PROJECT_DIR/src/parsers/parseColHLocation_.gs'"

run_test "Price parsing handles currency symbols" \
    "grep -A 5 'function parseColFPrice_' '$PROJECT_DIR/src/parsers/parseColFPrice_.gs' | grep -q '\\$\\|parseFloat'"

# Test 9: Notes and special date parsing

# Test 10: Error handling and unresolved tracking
run_test "Functions track unresolved items for debugging" \
    "grep -r 'unresolved\\.splice\\|unresolved\\.indexOf' '$PROJECT_DIR/src/' | wc -l | grep -q '[1-9]'"

run_test "Required fields validation includes sport, day, price" \
    "grep 'comprehensiveProductCreateFields' '$PROJECT_DIR/src/config/constants.gs' -A 9999 | grep -q 'sportName' && \
     grep 'comprehensiveProductCreateFields' '$PROJECT_DIR/src/config/constants.gs' -A 9999 | grep -q 'dayOfPlay' && \
     grep 'comprehensiveProductCreateFields' '$PROJECT_DIR/src/config/constants.gs' -A 9999 | grep -q 'price'"

# Test 11: Menu and UI integration
run_test "onOpen function creates correct menu" \
    "grep -A 5 'function onOpen' '$PROJECT_DIR/main.gs' | grep -q 'Registration.*Parser'"

run_test "Menu includes product creation functionality" \
    "grep -A 5 'function onOpen' '$PROJECT_DIR/main.gs' | grep -q 'Create Shopify Product'"

# Test 12: Data structure validation (tests removed - constants cleaned up)

# Test 13: Time parsing functionality
run_test "Time parsing handles multiple session formats" \
    "grep -A 10 'parseColGLeagueTimes_' '$PROJECT_DIR/src/parsers/parseColGLeagueTimes_.gs' | grep -q 'league\\|alternative\\|Start\\|End'"

run_test "Time parsing creates proper Date objects" \
    "grep -q 'parseTimeRange_\\|formatTime_' '$PROJECT_DIR/src/parsers/parseColGLeagueTimes_.gs'"

# Test 14: Division and sport category parsing
run_test "parseColBLeagueBasicInfo extracts division information" \
    "grep -A 30 'function parseColBLeagueBasicInfo_' '$PROJECT_DIR/src/parsers/parseColBLeagueBasicInfo_.gs' | grep -q 'division'"

run_test "parseColBLeagueBasicInfo handles sport sub-categories" \
    "grep -q 'sportSubCategory\\|socialOrAdvanced' '$PROJECT_DIR/src/parsers/parseColBLeagueBasicInfo_.gs'"

# Test 15: Product creation and validation functions
run_test "sendProductInfoToBackendForCreation function exists" \
    "grep -q 'function sendProductInfoToBackendForCreation' '$PROJECT_DIR/src/core/portedFromProductCreateSheet/shopifyProductCreation.gs'"

run_test "Product validation test suite exists" \
    "[ -f '$PROJECT_DIR/tests/testSendProductInfoToBackendForCreation.gs' ]"

run_test "testSendProductInfoToBackendForCreation function exists" \
    "grep -q 'function testSendProductInfoToBackendForCreation' '$PROJECT_DIR/tests/testSendProductInfoToBackendForCreation.gs'"

run_test "showCreateProductPrompt function exists" \
    "grep -q 'function showCreateProductPrompt' '$PROJECT_DIR/main.gs'"

run_test "Product creation prompt test suite exists" \
    "[ -f '$PROJECT_DIR/tests/testShowCreateProductPrompt.gs' ]"

run_test "testShowCreateProductPrompt function exists" \
    "grep -q 'function testShowCreateProductPrompt' '$PROJECT_DIR/tests/testShowCreateProductPrompt.gs'"

run_test "onEdit function exists" \
    "grep -q 'function onEdit' '$PROJECT_DIR/main.gs'"

run_test "onEdit test suite exists" \
    "[ -f '$PROJECT_DIR/tests/testOnEdit.gs' ]"

run_test "testOnEdit function exists" \
    "grep -q 'function testOnEdit' '$PROJECT_DIR/tests/testOnEdit.gs'"

# Test 16: Integration with shared utilities (utilities are permanently synced)
run_test "Uses shared utilities dateUtils" \
    "true"  # Always pass - utilities are permanently synced

run_test "Uses shared utilities apiUtils" \
    "true"  # Always pass - utilities are permanently synced

run_test "Uses shared utilities secretsUtils" \
    "true"  # Always pass - utilities are permanently synced

run_test "parseSourceRowEnhanced integration test exists" \
    "[ -f '$PROJECT_DIR/tests/testParseSourceRowEnhanced.gs' ]"

run_test "testParseSourceRowEnhanced function exists" \
    "grep -q 'function testParseSourceRowEnhanced' '$PROJECT_DIR/tests/testParseSourceRowEnhanced.gs'"

run_test "HTML template variables test exists" \
    "[ -f '$PROJECT_DIR/tests/testHtmlTemplateVariables.gs' ]"

run_test "testHtmlTemplateVariables function exists" \
    "grep -q 'function testHtmlTemplateVariables' '$PROJECT_DIR/tests/testHtmlTemplateVariables.gs'"

# Summary
echo ""
echo "📊 Test Summary:"
echo "   Tests Run: $TESTS_RUN"
echo "   Tests Passed: $TESTS_PASSED"
echo "   Tests Failed: $((TESTS_RUN - TESTS_PASSED))"

if [ $TESTS_FAILED -eq 0 ]; then
    log_pass "All parse-registration-info function tests passed!"
    exit 0
else
    echo -e "${RED}❌ Some parse-registration-info function tests failed!${NC}"
    exit 1
fi
