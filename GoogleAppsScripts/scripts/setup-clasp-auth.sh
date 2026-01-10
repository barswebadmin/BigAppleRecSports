#!/bin/bash

# Setup script for clasp authentication in CI/CD environments
# This script helps configure the required secrets and authentication

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

function show_help() {
    echo "Google Apps Script CI/CD Authentication Setup"
    echo ""
    echo "This script helps you set up authentication for automated deployments."
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  setup-local     Set up clasp authentication locally"
    echo "  show-credentials Show current clasp credentials (for CI/CD setup)"
    echo "  test-auth       Test current authentication"
    echo "  help            Show this help message"
    echo ""
    echo "For CI/CD setup:"
    echo "  1. Run: $0 setup-local"
    echo "  2. Run: $0 show-credentials"
    echo "  3. Copy the output to GitHub Secrets as 'CLASP_CREDENTIALS'"
}

function setup_local_auth() {
    log_info "Setting up local clasp authentication..."
    
    # Check if clasp is installed
    if ! command -v clasp >/dev/null 2>&1; then
        log_error "clasp is not installed. Install it with: npm install -g @google/clasp"
        exit 1
    fi
    
    # Check if already logged in
    if clasp status >/dev/null 2>&1; then
        log_warning "Already logged in to clasp"
        read -p "Do you want to logout and login again? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            clasp logout
        else
            log_info "Keeping existing authentication"
            return 0
        fi
    fi
    
    log_info "Starting clasp login process..."
    echo ""
    echo "📋 Instructions:"
    echo "  1. A browser window will open"
    echo "  2. Sign in with your Google account"
    echo "  3. Grant permissions to Google Apps Script API"
    echo "  4. Return to this terminal"
    echo ""
    read -p "Press Enter to continue..."
    
    clasp login
    
    if clasp status >/dev/null 2>&1; then
        log_success "Successfully authenticated with clasp!"
    else
        log_error "Authentication failed"
        exit 1
    fi
}

function show_credentials() {
    log_info "Checking for clasp credentials..."
    
    CLASP_RC_FILE="$HOME/.clasprc.json"
    
    if [ ! -f "$CLASP_RC_FILE" ]; then
        log_error "No clasp credentials found. Run: $0 setup-local"
        exit 1
    fi
    
    log_info "Clasp credentials found at: $CLASP_RC_FILE"
    echo ""
    log_warning "🔒 SECURITY WARNING: These credentials provide access to your Google Apps Script projects!"
    log_warning "🚨 Store them securely and never commit them to version control!"
    echo ""
    echo "📋 Copy the following content to your GitHub repository secrets:"
    echo "   Secret name: CLASP_CREDENTIALS"
    echo "   Secret value:"
    echo ""
    echo "----------------------------------------"
    cat "$CLASP_RC_FILE"
    echo ""
    echo "----------------------------------------"
    echo ""
    log_info "To add this to GitHub:"
    echo "  1. Go to your repository on GitHub"
    echo "  2. Click Settings → Secrets and variables → Actions"
    echo "  3. Click 'New repository secret'"
    echo "  4. Name: CLASP_CREDENTIALS"
    echo "  5. Value: Paste the JSON content above"
    echo "  6. Click 'Add secret'"
}

function test_auth() {
    log_info "Testing clasp authentication..."
    
    if ! command -v clasp >/dev/null 2>&1; then
        log_error "clasp is not installed"
        exit 1
    fi
    
    # Test basic authentication
    if ! clasp status >/dev/null 2>&1; then
        log_error "Not authenticated with clasp. Run: $0 setup-local"
        exit 1
    fi
    
    log_success "✅ Basic authentication working"
    
    # Test API access
    log_info "Testing Google Apps Script API access..."
    
    # Try to list projects (this tests API permissions)
    if clasp list >/dev/null 2>&1; then
        log_success "✅ Google Apps Script API access working"
    else
        log_error "❌ Google Apps Script API access failed"
        log_info "💡 Try enabling the Google Apps Script API:"
        log_info "   https://script.google.com/home/usersettings"
        exit 1
    fi
    
    # Test project access if we're in a project directory
    if [ -f .clasp.json ]; then
        PROJECT_NAME=$(basename "$(pwd)")
        log_info "Testing project access for: $PROJECT_NAME"
        
        if clasp status | grep -q "Not logged in"; then
            log_error "❌ Not logged in to project"
        else
            log_success "✅ Project access working"
        fi
    fi
    
    log_success "🎉 All authentication tests passed!"
}

function validate_project_setup() {
    log_info "Validating Google Apps Script project setup..."
    
    # List all GAS projects and check their .clasp.json files
    GAS_PROJECTS=(
        "leadership-discount-codes"
        "product-variant-creation" 
        "parse-registration-info"
        "process-refunds-exchanges"
        "payment-assistance-tags"
        "veteran-tags"
        "waitlist-script"
    )
    
    VALID_PROJECTS=0
    INVALID_PROJECTS=0
    
    for project in "${GAS_PROJECTS[@]}"; do
        if [ -d "$project" ]; then
            if [ -f "$project/.clasp.json" ]; then
                log_success "✅ $project (configured)"
                VALID_PROJECTS=$((VALID_PROJECTS + 1))
            else
                log_error "❌ $project (missing .clasp.json)"
                INVALID_PROJECTS=$((INVALID_PROJECTS + 1))
            fi
        else
            log_warning "⚠️  $project (directory not found)"
        fi
    done
    
    echo ""
    log_info "📊 Project Status Summary:"
    echo "  ✅ Valid projects: $VALID_PROJECTS"
    echo "  ❌ Invalid projects: $INVALID_PROJECTS"
    echo "  📁 Total expected: ${#GAS_PROJECTS[@]}"
    
    if [ $INVALID_PROJECTS -gt 0 ]; then
        echo ""
        log_error "Some projects are not properly configured for deployment"
        log_info "💡 To fix missing .clasp.json files:"
        log_info "   1. cd [project-directory]"
        log_info "   2. clasp create --type standalone --title 'Project Name'"
        log_info "   3. Or clasp clone [existing-script-id]"
    fi
}

# Main command handling
case "${1:-help}" in
    "setup-local")
        setup_local_auth
        ;;
    "show-credentials")
        show_credentials
        ;;
    "test-auth")
        test_auth
        ;;
    "validate-projects")
        validate_project_setup
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
