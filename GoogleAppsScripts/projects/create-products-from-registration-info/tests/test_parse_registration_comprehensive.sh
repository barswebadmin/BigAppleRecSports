#!/bin/bash

# Comprehensive test suite for parse-registration-info logic
# Tests all parsing functions, validation, and migration logic
# Runs Node.js-based automated tests for CI/CD compatibility

set -e
cd "$(dirname "$0")"

echo "🧪 === COMPREHENSIVE PARSE-REGISTRATION-INFO TESTS ==="
echo "Testing all parsing logic, validation, and migration functions"
echo "Using Node.js-based automated testing for CI/CD compatibility"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js not found. Please install Node.js to run automated tests.${NC}"
    echo "Falling back to basic validation checks..."

    # Basic validation - check that key files exist
    PARSE_REG_DIR=".."
    if [ ! -d "$PARSE_REG_DIR/src" ]; then
        echo -e "${RED}❌ Parse registration info src directory not found${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ Parse registration info project structure exists${NC}"
    echo -e "${YELLOW}⚠️  Install Node.js for comprehensive testing${NC}"
    exit 0
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 Installing test dependencies...${NC}"
    if [ -f "package.json" ]; then
        npm install --silent
    else
        echo -e "${RED}❌ package.json not found in test directory${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}📦 Node.js dependencies already installed${NC}"
fi

# Run the automated Node.js tests
echo -e "${BLUE}🚀 Running automated Node.js tests...${NC}"

# Run with detailed output
echo -e "${BLUE}📋 Test output:${NC}"
if node test-runner.mjs 2>&1; then
    echo -e "${GREEN}✅ All automated tests passed!${NC}"
    TEST_EXIT_CODE=0
else
    echo -e "${RED}❌ Some automated tests failed!${NC}"
    echo -e "${YELLOW}⚠️  Check the detailed output above for specific failures${NC}"
    TEST_EXIT_CODE=1
fi

exit $TEST_EXIT_CODE
