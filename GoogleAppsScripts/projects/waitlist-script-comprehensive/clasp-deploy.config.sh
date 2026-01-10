#!/bin/bash

# Project-specific configuration for clasp deployment
# Project-specific configuration for clasp deployment
# Override any defaults from deploy.sh here

# Package manager (npm, pnpm, yarn)
export PACKAGE_MANAGER="pnpm"

# Build output directory
export BUILD_DIR="build"

# Output filename from esbuild
export OUTPUT_FILE="Code.js"

# Temporary deployment directory
export DEPLOY_TEMP="deploy_temp"

# Project name (optional, defaults to directory name)
# export PROJECT_NAME="waitlist-script-comprehensive"

