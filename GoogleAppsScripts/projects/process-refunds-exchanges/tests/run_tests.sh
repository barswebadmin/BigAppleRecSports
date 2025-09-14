#!/bin/bash

# Test runner for process-refunds-exchanges Google Apps Script tests
# This script sets up the test environment and runs all tests

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Process Refunds & Exchanges - Test Suite${NC}"
echo "=============================================="

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "\n${YELLOW}📍 Test Directory: $SCRIPT_DIR${NC}"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is not installed. Please install Node.js to run tests.${NC}"
    exit 1
fi

echo -e "\n${GREEN}✅ Node.js found: $(node --version)${NC}"

# Install dependencies if package.json exists
if [ -f "package.json" ]; then
    echo -e "\n${YELLOW}📦 Installing test dependencies...${NC}"
    if command -v npm &> /dev/null; then
        npm install --silent
    else
        echo -e "${RED}❌ npm not found. Please install npm.${NC}"
        exit 1
    fi
else
    echo -e "\n${YELLOW}⚠️  No package.json found. Running tests without dependencies...${NC}"
fi

echo -e "\n${BLUE}🚀 Running Google Apps Script Form Submission Tests...${NC}"
echo "=" * 60

# Run the main test file
if [ -f "test_form_submission.js" ]; then
    node test_form_submission.js
    TEST_EXIT_CODE=$?

    if [ $TEST_EXIT_CODE -eq 0 ]; then
        echo -e "\n${GREEN}🎉 All tests passed successfully!${NC}"
    else
        echo -e "\n${RED}❌ Tests failed with exit code: $TEST_EXIT_CODE${NC}"
        exit $TEST_EXIT_CODE
    fi
else
    echo -e "${RED}❌ Test file 'test_form_submission.js' not found.${NC}"
    exit 1
fi

echo -e "\n${BLUE}📋 Test Summary:${NC}"
echo "- Form data extraction: ✅"
echo "- Backend payload construction: ✅"
echo "- Successful backend calls: ✅"
echo "- Error handling: ✅"
echo "- Field variations: ✅"

echo -e "\n${GREEN}✨ Test suite completed successfully!${NC}"
