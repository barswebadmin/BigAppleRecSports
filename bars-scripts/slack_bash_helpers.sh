#!/bin/bash
# Shared bash helper functions for Slack scripts

# Process --raw flag and convert to --json flag for Python scripts
# Usage: process_slack_flags "$@"
# Returns: Modified arguments with --raw converted to --json
process_slack_flags() {
    local args=()
    for arg in "$@"; do
        if [ "$arg" = "--raw" ]; then
            args+=("--json")
        else
            args+=("$arg")
        fi
    done
    echo "${args[@]}"
}

# Check and activate virtual environment
# Usage: activate_venv
# Returns: 0 on success, exits with 1 on failure
activate_venv() {
    if [ -f .venv/bin/activate ]; then
        source .venv/bin/activate
    else
        echo "❌ Virtual environment not found. Run 'make venv' first." >&2
        exit 1
    fi
}

# Run a Python Slack script with processed arguments
# Usage: run_slack_script "script_name.py" "$@"
run_slack_script() {
    local script_name="$1"
    shift
    local processed_args
    processed_args=$(process_slack_flags "$@")
    
    python3 "$SCRIPT_DIR/$script_name" $processed_args
}

