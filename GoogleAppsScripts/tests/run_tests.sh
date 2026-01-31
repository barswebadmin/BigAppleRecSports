#!/usr/bin/env bash
# Google Apps Scripts test runner - verifies all projects build successfully

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GAS_ROOT="$(dirname "$SCRIPT_DIR")"
PROJECTS_DIR="$GAS_ROOT/projects"
BUILD_SCRIPT="$(dirname "$(dirname "$GAS_ROOT")")/scripts/deployment/google/build.js"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found"
    exit 1
fi

# Check build script exists
if [ ! -f "$BUILD_SCRIPT" ]; then
    echo "❌ Build script not found: $BUILD_SCRIPT"
    exit 1
fi

# Check projects directory exists
if [ ! -d "$PROJECTS_DIR" ]; then
    echo "❌ Projects directory not found: $PROJECTS_DIR"
    exit 1
fi

# Find all project directories
mapfile -t projects < <(find "$PROJECTS_DIR" -mindepth 1 -maxdepth 1 -type d ! -name '.*' | sort)

if [ ${#projects[@]} -eq 0 ]; then
    echo "⚠️  No GAS projects found"
    exit 1
fi

echo "🧪 Testing ${#projects[@]} GAS projects (verifying builds)..."

exit_code=0

for project_dir in "${projects[@]}"; do
    project_name="$(basename "$project_dir")"
    
    # Skip projects without esbuild.config.js
    if [ ! -f "$project_dir/esbuild.config.js" ]; then
        echo "  ⏭️  $project_name: No esbuild.config.js (skipping)"
        continue
    fi
    
    echo "  🔨 $project_name: Building..."
    
    # Build project
    if node "$BUILD_SCRIPT" "$project_dir" > /dev/null 2>&1; then
        echo "    ✅ Build successful"
    else
        echo "    ❌ Build failed"
        exit_code=1
    fi
done

if [ $exit_code -eq 0 ]; then
    echo "✅ All GAS projects built successfully"
else
    echo "❌ Some GAS project builds failed"
fi

exit $exit_code
