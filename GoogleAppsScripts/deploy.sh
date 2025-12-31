#!/bin/bash

# Project-specific clasp deployment wrapper
# Delegates to shared GAS clasp deployment script

# Get the directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Execute the shared deployment script
exec bash "$SCRIPT_DIR/../../shared-build-tools/gas-clasp-deploy.sh" "$@"
