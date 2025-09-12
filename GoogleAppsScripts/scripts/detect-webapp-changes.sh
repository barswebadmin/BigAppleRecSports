#!/bin/bash

# Script to detect doGet/doPost function changes across all Google Apps Script projects
# This script can be used in CI/CD or as a pre-commit hook

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

# Check if we're in a git repository
if ! command -v git >/dev/null 2>&1; then
    log_error "Git is not installed"
    exit 1
fi

if [ ! -d .git ]; then
    log_error "Not in a git repository"
    exit 1
fi

# Get the commit range to check
COMMIT_RANGE="HEAD~1..HEAD"
if [ "$1" == "--staged" ]; then
    COMMIT_RANGE="--cached"
    log_info "Checking staged changes for doGet/doPost functions..."
elif [ -n "$1" ]; then
    COMMIT_RANGE="$1"
    log_info "Checking commit range '$COMMIT_RANGE' for doGet/doPost functions..."
else
    log_info "Checking last commit for doGet/doPost functions..."
fi

# Array to store projects with doGet/doPost changes
PROJECTS_WITH_CHANGES=()
AFFECTED_FILES=()

# Get list of Google Apps Script projects
GAS_PROJECTS=(
    "leadership-discount-codes"
    "product-variant-creation" 
    "parse-registration-info"
    "process-refunds-exchanges"
    "payment-assistance-tags"
    "veteran-tags"
    "waitlist-script"
)

log_info "Scanning ${#GAS_PROJECTS[@]} Google Apps Script projects..."

# Check each project for doGet/doPost changes
for project in "${GAS_PROJECTS[@]}"; do
    if [ ! -d "GoogleAppsScripts/$project" ]; then
        log_warning "Project directory not found: $project (skipping)"
        continue
    fi
    
    # Get changed .gs files in this project
    if [ "$COMMIT_RANGE" == "--cached" ]; then
        CHANGED_FILES=$(git diff --cached --name-only | grep "^GoogleAppsScripts/$project/.*\.gs$" || true)
    else
        CHANGED_FILES=$(git diff --name-only $COMMIT_RANGE | grep "^GoogleAppsScripts/$project/.*\.gs$" || true)
    fi
    
    if [ -z "$CHANGED_FILES" ]; then
        continue
    fi
    
    echo "  📁 Checking project: $project"
    
    # Check each changed file for doGet/doPost function changes
    for file in $CHANGED_FILES; do
        if [ ! -f "$file" ]; then
            log_warning "File not found: $file (may have been deleted)"
            continue
        fi
        
        # Check if the diff contains doGet or doPost function additions/modifications
        if [ "$COMMIT_RANGE" == "--cached" ]; then
            DIFF_OUTPUT=$(git diff --cached "$file" || true)
        else
            DIFF_OUTPUT=$(git diff $COMMIT_RANGE "$file" || true)
        fi
        
        # Look for function doGet or function doPost in added/modified lines
        if echo "$DIFF_OUTPUT" | grep -E "^\+.*function\s+(doGet|doPost)" >/dev/null; then
            echo "    🚨 doGet/doPost changes detected in: $file"
            PROJECTS_WITH_CHANGES+=("$project")
            AFFECTED_FILES+=("$file")
        fi
        
        # Also check for changes to existing doGet/doPost functions
        if echo "$DIFF_OUTPUT" | grep -B5 -A10 "^\+.*function\s\+(doGet\|doPost\)" | grep -E "^\+" >/dev/null; then
            echo "    🔄 Modifications near doGet/doPost in: $file"
            if [[ ! " ${PROJECTS_WITH_CHANGES[@]} " =~ " ${project} " ]]; then
                PROJECTS_WITH_CHANGES+=("$project")
            fi
            if [[ ! " ${AFFECTED_FILES[@]} " =~ " ${file} " ]]; then
                AFFECTED_FILES+=("$file")
            fi
        fi
    done
done

echo
echo "📊 Detection Summary:"
echo "===================="

if [ ${#PROJECTS_WITH_CHANGES[@]} -eq 0 ]; then
    log_success "No doGet/doPost function changes detected"
    echo "✅ All web app endpoints should maintain their current behavior"
    exit 0
fi

log_warning "doGet/doPost function changes detected in ${#PROJECTS_WITH_CHANGES[@]} project(s):"
for project in "${PROJECTS_WITH_CHANGES[@]}"; do
    echo "  - $project"
done

echo
log_error "🚨 CRITICAL DEPLOYMENT REQUIREMENT 🚨"
echo "========================================"
echo "The following projects MUST be deployed for changes to take effect:"
echo ""

for project in "${PROJECTS_WITH_CHANGES[@]}"; do
    echo "📦 Project: $project"
    echo "   📁 Directory: GoogleAppsScripts/$project"
    echo "   🚀 Deploy command: cd GoogleAppsScripts/$project && clasp deploy"
    echo "   🌐 Web app functions will NOT work until deployed!"
    echo ""
done

echo "🔧 Deployment Options:"
echo "  1. Manual: cd GoogleAppsScripts/[project] && clasp deploy"
echo "  2. Script: ./scripts/deploy-project.sh [project]"
echo "  3. Auto: Merge to master branch (triggers auto-deployment)"
echo ""

echo "📋 Affected Files:"
for file in "${AFFECTED_FILES[@]}"; do
    echo "  - $file"
done

echo ""
log_warning "💡 Remember: doGet handles GET requests, doPost handles POST requests"
log_warning "🌐 Web app URLs will continue to use OLD code until deployment!"

# Exit with non-zero status to indicate deployment is needed
exit 2
