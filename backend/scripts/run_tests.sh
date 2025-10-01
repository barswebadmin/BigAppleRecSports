#!/bin/bash

# Test runner for backend API tests
# This script activates the virtual environment and runs all backend tests

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Backend API - Test Suite${NC}"
echo "================================"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
cd "$BACKEND_DIR"

echo -e "\n${YELLOW}📍 Backend Directory: $BACKEND_DIR${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment not found. Please create one first:${NC}"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

echo -e "\n${GREEN}✅ Virtual environment found${NC}"

# Activate virtual environment
echo -e "\n${YELLOW}🔧 Activating virtual environment...${NC}"
source venv/bin/activate

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "\n${YELLOW}📦 Installing testing dependencies...${NC}"
    pip install pytest fastapi httpx pytest-mock
fi

echo -e "\n${BLUE}🚀 Running Backend API Tests...${NC}"
echo "=" * 50

# Run the backend API tests
if [ -f "tests/test_refunds_api.py" ]; then
    python -m pytest tests/test_refunds_api.py -v --tb=short
    TEST_EXIT_CODE=$?
    
    if [ $TEST_EXIT_CODE -eq 0 ]; then
        echo -e "\n${GREEN}🎉 All backend tests passed successfully!${NC}"
    else
        echo -e "\n${RED}❌ Backend tests failed with exit code: $TEST_EXIT_CODE${NC}"
        exit $TEST_EXIT_CODE
    fi
else
    echo -e "${RED}❌ Test file 'tests/test_refunds_api.py' not found.${NC}"
    exit 1
fi

echo -e "\n${BLUE}📋 Test Summary:${NC}"
echo "- Successful order validation: ✅"
echo "- Order not found (406): ✅"
echo "- Email mismatch (409): ✅"
echo "- Request validation: ✅"
echo "- Error handling: ✅"
echo "- Integration scenarios: ✅"

echo -e "\n${GREEN}✨ Backend test suite completed successfully!${NC}"

# Deactivate virtual environment
deactivate
