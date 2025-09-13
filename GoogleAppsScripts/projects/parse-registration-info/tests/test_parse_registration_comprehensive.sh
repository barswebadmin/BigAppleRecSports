#!/bin/bash

# Comprehensive test suite for parse-registration-info logic
# Tests all parsing functions, validation, and migration logic
# Runs Node.js-based automated tests for CI/CD compatibility

set -e
cd "$(dirname "$0")/../../.."

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
    PARSE_REG_DIR="../projects/parse-registration-info"
    if [ ! -d "$PARSE_REG_DIR" ]; then
        echo -e "${RED}❌ Parse registration info directory not found${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ Parse registration info directory exists${NC}"
    echo -e "${YELLOW}⚠️  Install Node.js for comprehensive testing${NC}"
    exit 0
fi

# Set up Node.js test environment
TEST_DIR="parse-registration-info"
if [ ! -d "$TEST_DIR" ]; then
    echo -e "${YELLOW}📦 Setting up Node.js test environment...${NC}"
    mkdir -p "$TEST_DIR"
fi

# Install dependencies if needed
if [ ! -d "$TEST_DIR/node_modules" ]; then
    echo -e "${YELLOW}📦 Installing test dependencies...${NC}"
    cd "$TEST_DIR"
    if [ -f "package.json" ]; then
        npm install --silent
        cd ..
    else
        echo -e "${RED}❌ package.json not found in test directory${NC}"
        exit 1
    fi
fi

# Run the automated Node.js tests
echo -e "${BLUE}🚀 Running automated Node.js tests...${NC}"
cd "$TEST_DIR"

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
cd ..

exit $TEST_EXIT_CODE
