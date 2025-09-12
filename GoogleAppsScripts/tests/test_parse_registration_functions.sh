#!/bin/bash

# Test suite for parse-registration-info core functionality
# Tests parsing functions, data validation, and migration logic

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

PROJECT_DIR="projects/parse-registration-info"

# Test 1: Project structure exists
run_test "Parse registration project exists" \
    "[ -d '$PROJECT_DIR' ]"

# Test 2: Main code file exists
run_test "Main entry point exists" \
    "[ -f '$PROJECT_DIR/main.gs' ]"

# Test 3: Core parsing functions exist
run_test "parseSourceRowEnhanced_ function exists" \
    "grep -q 'function parseSourceRowEnhanced_' '$PROJECT_DIR/core/rowParser.gs'"

run_test "parseBFlags_ function exists" \
    "grep -q 'function parseBFlags_' '$PROJECT_DIR/core/flagsParser.gs'"

run_test "parseTimeRangeBothSessions_ function exists" \
    "grep -q 'function parseTimeRangeBothSessions_' '$PROJECT_DIR/core/timeParser.gs'"

run_test "parsePriceNumber_ function exists" \
    "grep -q 'function parsePriceNumber_' '$PROJECT_DIR/core/priceParser.gs'"

run_test "parseDateFlexibleDateOnly_ function exists" \
    "grep -q 'function parseDateFlexibleDateOnly_' '$PROJECT_DIR/core/dateParser.gs'"

run_test "parseDateFlexibleDateTime_ function exists" \
    "grep -q 'function parseDateFlexibleDateTime_' '$PROJECT_DIR/core/dateParser.gs'"

# Test 4: Migration functions exist
run_test "migrateRowToTarget_ function exists" \
    "grep -q 'function migrateRowToTarget_' '$PROJECT_DIR/core/migration.gs'"

run_test "showMigrationPrompt function exists" \
    "grep -q 'function showMigrationPrompt' '$PROJECT_DIR/main.gs'"

# Test 5: Configuration constants exist
run_test "TARGET_SPREADSHEET_ID constant exists" \
    "grep -q 'TARGET_SPREADSHEET_ID' '$PROJECT_DIR/config/constants.gs'"

run_test "CANONICAL_LOCATIONS array exists and has locations" \
    "grep -A 10 'CANONICAL_LOCATIONS' '$PROJECT_DIR/config/constants.gs' | grep -q 'Elliott Center\\|Chelsea Park'"

run_test "headerMapping object exists" \
    "grep -q 'headerMapping.*=' '$PROJECT_DIR/config/constants.gs'"

run_test "REQUIRED_TARGET_HEADERS array exists" \
    "grep -q 'REQUIRED_TARGET_HEADERS' '$PROJECT_DIR/config/constants.gs'"

# Test 6: Validation and helper functions
run_test "checkRequiredFields_ function exists" \
    "grep -q 'function checkRequiredFields_' '$PROJECT_DIR/validators/fieldValidation.gs'"

run_test "normalizeSport_ helper exists" \
    "grep -q 'normalizeSport_\\|function.*normalizeSport' '$PROJECT_DIR/helpers/normalizers.gs'"

run_test "normalizeDay_ helper exists" \
    "grep -q 'normalizeDay_\\|function.*normalizeDay' '$PROJECT_DIR/helpers/normalizers.gs'"

run_test "toTitleCase_ helper exists" \
    "grep -q 'toTitleCase_\\|function.*toTitleCase' '$PROJECT_DIR/helpers/textUtils.gs'"

# Test 7: Date parsing functionality
run_test "deriveSeasonYearFromDate_ function exists" \
    "grep -q 'deriveSeasonYearFromDate_\\|function.*deriveSeasonYear' '$PROJECT_DIR/helpers/normalizers.gs'"

run_test "parseFlexible_ function exists" \
    "grep -q 'function parseFlexible_' '$PROJECT_DIR/core/dateParser.gs'"

# Test 8: Location and price parsing
run_test "canonicalizeLocation_ function exists" \
    "grep -q 'canonicalizeLocation_\\|function.*canonicalizeLocation' '$PROJECT_DIR/helpers/normalizers.gs'"

run_test "Price parsing handles currency symbols" \
    "grep -A 5 'function parsePriceNumber_' '$PROJECT_DIR/core/priceParser.gs' | grep -q '\\$\\|parseFloat'"

# Test 9: Notes and special date parsing
run_test "parseNotes_ function exists for extracting special dates" \
    "grep -q 'function parseNotes_' '$PROJECT_DIR/core/notesParser.gs'"

run_test "Notes parsing extracts orientation and scout night" \
    "grep -A 20 'function parseNotes_' '$PROJECT_DIR/core/notesParser.gs' | grep -q 'orientation\\|scout'"

# Test 10: Error handling and unresolved tracking
run_test "Functions track unresolved items for debugging" \
    "grep -r 'unresolved\\.push\\|unresolved\\[' '$PROJECT_DIR/core/' | wc -l | grep -q '[1-9]'"

run_test "Required fields validation includes sport, day, price" \
    "grep -A 15 'REQUIRED_TARGET_HEADERS' '$PROJECT_DIR/config/constants.gs' | grep -q 'sport' && \
     grep -A 15 'REQUIRED_TARGET_HEADERS' '$PROJECT_DIR/config/constants.gs' | grep -q 'day' && \
     grep -A 15 'REQUIRED_TARGET_HEADERS' '$PROJECT_DIR/config/constants.gs' | grep -q 'price'"

# Test 11: Menu and UI integration
run_test "onOpen function creates correct menu" \
    "grep -A 5 'function onOpen' '$PROJECT_DIR/main.gs' | grep -q 'Registration.*Parser'"

run_test "Menu includes migration functionality" \
    "grep -A 5 'function onOpen' '$PROJECT_DIR/main.gs' | grep -q 'Migrate Row'"

# Test 12: Data structure validation
run_test "Header mapping includes essential fields" \
    "grep -A 30 'headerMapping.*=' '$PROJECT_DIR/config/constants.gs' | grep -q 'sport' && \
     grep -A 30 'headerMapping.*=' '$PROJECT_DIR/config/constants.gs' | grep -q 'day' && \
     grep -A 30 'headerMapping.*=' '$PROJECT_DIR/config/constants.gs' | grep -q 'price' && \
     grep -A 30 'headerMapping.*=' '$PROJECT_DIR/config/constants.gs' | grep -q 'location'"

run_test "Target spreadsheet configuration is valid" \
    "grep 'TARGET_SPREADSHEET_ID' '$PROJECT_DIR/config/constants.gs' | grep -q '1w9Hj4JMmjTIQM5c8FbXuKnTMjVOLipgXaC6WqeSV_vc'"

# Test 13: Time parsing functionality
run_test "Time parsing handles multiple session formats" \
    "grep -A 10 'parseTimeRangeBothSessions_' '$PROJECT_DIR/core/timeParser.gs' | grep -q 'primary\\|alt\\|Start\\|End'"

run_test "Time parsing creates proper Date objects" \
    "grep -A 10 'parseTimeRangeBothSessions_' '$PROJECT_DIR/core/timeParser.gs' | grep -q 'Date\\|DateOnly'"

# Test 14: Division and sport category parsing
run_test "parseBFlags extracts division information" \
    "grep -A 10 'function parseBFlags_' '$PROJECT_DIR/core/flagsParser.gs' | grep -q 'division'"

run_test "parseBFlags handles sport sub-categories" \
    "grep -q 'sportSubCategory\\|socialOrAdvanced' '$PROJECT_DIR/core/flagsParser.gs'"

# Test 15: Integration with shared utilities
run_test "Uses shared utilities dateUtils" \
    "[ -f '$PROJECT_DIR/shared-utilities/dateUtils.gs' ]"

run_test "Uses shared utilities apiUtils" \
    "[ -f '$PROJECT_DIR/shared-utilities/apiUtils.gs' ]"

run_test "Uses shared utilities secretsUtils" \
    "[ -f '$PROJECT_DIR/shared-utilities/secretsUtils.gs' ]"

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
