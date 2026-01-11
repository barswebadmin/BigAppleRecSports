#!/bin/bash
#
# Backup GAS projects by pulling code from remote
# Creates timestamped backups in GoogleAppsScripts/backups/
#
# Usage: ./scripts/backup_gas_projects.sh [project-name ...]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GAS_ROOT="$REPO_ROOT/GoogleAppsScripts"
PROJECTS_DIR="$GAS_ROOT/projects"
BACKUP_DIR="$GAS_ROOT/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Projects to backup
PROJECTS=(
    "waitlist-script-comprehensive"
    "veteran-tags"
    "process-refunds-exchanges"
    "create-products-new"
    "add-sold-out-product-to-waitlist"
)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if clasp is available
if ! command -v clasp >/dev/null 2>&1; then
    log_error "clasp command not found. Please install clasp CLI."
    exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"
BACKUP_TIMESTAMP_DIR="$BACKUP_DIR/$TIMESTAMP"
mkdir -p "$BACKUP_TIMESTAMP_DIR"

log_info "Creating backup in: $BACKUP_TIMESTAMP_DIR"
echo ""

# Use provided projects or default list
if [ $# -gt 0 ]; then
    PROJECTS=("$@")
fi

# Backup each project
for PROJECT_NAME in "${PROJECTS[@]}"; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "Backing up: $PROJECT_NAME"
    echo ""
    
    PROJECT_DIR="$PROJECTS_DIR/$PROJECT_NAME"
    BACKUP_PROJECT_DIR="$BACKUP_TIMESTAMP_DIR/$PROJECT_NAME"
    
    # Check if project exists locally
    if [ ! -d "$PROJECT_DIR" ]; then
        log_warning "Project directory not found locally: $PROJECT_DIR"
        echo ""
        continue
    fi
    
    # Check if .clasp.json exists
    if [ ! -f "$PROJECT_DIR/.clasp.json" ]; then
        log_warning ".clasp.json not found for $PROJECT_NAME - skipping"
        echo ""
        continue
    fi
    
    # Create backup directory for this project
    mkdir -p "$BACKUP_PROJECT_DIR"
    
    # Create temp directory for clasp pull
    TEMP_PULL_DIR=$(mktemp -d)
    trap "rm -rf $TEMP_PULL_DIR" EXIT
    
    log_info "Pulling code from remote..."
    
    # Copy .clasp.json to temp directory
    cp "$PROJECT_DIR/.clasp.json" "$TEMP_PULL_DIR/.clasp.json"
    
    # Pull from remote
    cd "$TEMP_PULL_DIR"
    
    if clasp pull >/dev/null 2>&1; then
        log_success "Successfully pulled from remote"
        
        # Copy all pulled files to backup directory
        log_info "Copying pulled files to backup..."
        cp -r "$TEMP_PULL_DIR"/* "$BACKUP_PROJECT_DIR/" 2>/dev/null || true
        
        # Also copy .clasp.json
        cp "$PROJECT_DIR/.clasp.json" "$BACKUP_PROJECT_DIR/.clasp.json"
        
        # Create metadata file
        cat > "$BACKUP_PROJECT_DIR/BACKUP_METADATA.txt" <<EOF
Backup created: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
Project: $PROJECT_NAME
Source: Remote (clasp pull)
Backup location: $BACKUP_PROJECT_DIR
EOF
        
        log_success "Backup complete: $BACKUP_PROJECT_DIR"
        
        # List files backed up
        FILE_COUNT=$(find "$BACKUP_PROJECT_DIR" -type f ! -name "BACKUP_METADATA.txt" | wc -l | tr -d ' ')
        log_info "Files backed up: $FILE_COUNT"
    else
        log_error "Failed to pull from remote for $PROJECT_NAME"
        # Still create backup directory with metadata
        cat > "$BACKUP_PROJECT_DIR/BACKUP_METADATA.txt" <<EOF
Backup created: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
Project: $PROJECT_NAME
Source: Remote (clasp pull)
Status: FAILED - Could not pull from remote
Backup location: $BACKUP_PROJECT_DIR
EOF
    fi
    
    # Cleanup temp directory
    rm -rf "$TEMP_PULL_DIR"
    trap - EXIT
    
    cd "$REPO_ROOT"
    echo ""
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_success "Backup complete!"
log_info "Backup location: $BACKUP_TIMESTAMP_DIR"
echo ""
log_info "To restore a project:"
echo "  1. Copy files from: $BACKUP_TIMESTAMP_DIR/<project-name>/"
echo "  2. To project directory: GoogleAppsScripts/projects/<project-name>/"
echo ""
