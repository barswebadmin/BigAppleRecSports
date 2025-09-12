#!/bin/bash

# Pre-commit hook to detect doGet/doPost function changes
# To install: ln -s ../../GoogleAppsScripts/scripts/pre-commit-hook.sh .git/hooks/pre-commit

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

function log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

function log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

function log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

function log_error() {
    echo -e "${RED}❌ $1${NC}"
}

echo "🔍 Checking for Google Apps Script doGet/doPost changes..."

# Navigate to the repository root
cd "$(git rev-parse --show-toplevel)"

# Run the detection script for staged changes
if [ -f "GoogleAppsScripts/scripts/detect-webapp-changes.sh" ]; then
    if GoogleAppsScripts/scripts/detect-webapp-changes.sh --staged; then
        log_success "No doGet/doPost changes detected in staged files"
        exit 0
    fi
    
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 2 ]; then
        echo ""
        log_warning "🚨 doGet/doPost function changes detected in your commit!"
        echo ""
        echo "🤔 What does this mean?"
        echo "  • You've modified web app endpoint functions"
        echo "  • These changes won't be active until deployed to Google Apps Script"
        echo "  • Users will still see the OLD behavior until deployment"
        echo ""
        echo "🚀 Next steps after committing:"
        echo "  1. Push to master branch (triggers auto-deployment)"
        echo "  2. Or manually deploy: ./GoogleAppsScripts/scripts/deploy-project.sh [project]"
        echo ""
        echo "💡 This is just a warning - your commit will proceed normally."
        echo ""
        
        # Ask user if they want to continue
        read -p "Continue with commit? (Y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            log_info "Commit cancelled by user"
            exit 1
        fi
        
        log_success "Proceeding with commit..."
        exit 0
    else
        log_error "Error running doGet/doPost detection script"
        exit 1
    fi
else
    log_warning "doGet/doPost detection script not found - skipping check"
    exit 0
fi
