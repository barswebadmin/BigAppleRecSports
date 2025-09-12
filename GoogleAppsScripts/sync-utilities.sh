#!/bin/bash

# Sync shared utilities to all Google Apps Script directories
# Usage: ./sync-utilities.sh

echo "🔄 Syncing shared utilities to all Google Apps Script directories..."

# Array of all GAS directories (excluding shared-utilities itself)
GAS_DIRS=(
  "projects/waitlist-script"
  "projects/product-variant-creation" 
  "projects/parse-registration-info"
  "projects/process-refunds-exchanges"
  "projects/payment-assistance-tags"
  "projects/veteran-tags"
  "projects/leadership-discount-codes"
)

# Verify we're in the GoogleAppsScripts directory
if [ ! -d "shared-utilities" ]; then
  echo "❌ Error: shared-utilities directory not found!"
  echo "   Make sure you're running this from the GoogleAppsScripts directory."
  exit 1
fi

# Check if shared-utilities has .gs files to sync
if [ ! "$(ls shared-utilities/*.gs 2>/dev/null)" ]; then
  echo "⚠️  Warning: No .gs files found in shared-utilities directory!"
  exit 1
fi

echo "📂 Found shared utilities (.gs files only):"
ls -la shared-utilities/*.gs

echo ""
echo "🎯 Target directories:"
for dir in "${GAS_DIRS[@]}"; do
  if [ -d "$dir" ]; then
    echo "  ✅ $dir"
  else
    echo "  ❌ $dir (not found)"
  fi
done

echo ""
read -p "🚀 Continue with sync? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "❌ Sync cancelled."
  exit 1
fi

echo ""
echo "🔄 Syncing utilities..."

# Sync to each directory
SUCCESS_COUNT=0
FAILED_COUNT=0

for dir in "${GAS_DIRS[@]}"; do
  if [ -d "$dir" ]; then
    echo "  📂 Syncing to $dir..."
    
    # Check if this directory uses organized structure (has shared-utilities subdirectory)
    if [ -d "$dir/shared-utilities" ]; then
      echo "    🗂️  Using organized structure"
      
      # Copy utilities to the shared-utilities subdirectory
      UTILITIES_SUCCESS=false
      if cp shared-utilities/*.gs "$dir/shared-utilities/" 2>/dev/null; then
        echo "    ✅ Utilities copied to shared-utilities/"
        UTILITIES_SUCCESS=true
      else
        echo "    ❌ Failed to copy utilities to $dir/shared-utilities"
      fi
      
      
      # Count success only if utilities copied successfully
      if [ "$UTILITIES_SUCCESS" = true ]; then
        ((SUCCESS_COUNT++))
      else
        ((FAILED_COUNT++))
      fi
    else
      echo "    📄 Using flat structure - converting to organized"
      
      # Create shared-utilities directory and copy utilities there
      mkdir -p "$dir/shared-utilities"
      UTILITIES_SUCCESS=false
      if cp shared-utilities/*.gs "$dir/shared-utilities/" 2>/dev/null; then
        echo "    ✅ Utilities copied to shared-utilities/"
        UTILITIES_SUCCESS=true
      else
        echo "    ❌ Failed to copy utilities to $dir/shared-utilities"
      fi
      
      
      # Count success only if utilities copied successfully
      if [ "$UTILITIES_SUCCESS" = true ]; then
        ((SUCCESS_COUNT++))
      else
        ((FAILED_COUNT++))
      fi
    fi
  else
    echo "  ⚠️  Skipping $dir (directory not found)"
    ((FAILED_COUNT++))
  fi
done

echo ""
echo "📊 Sync Results:"
echo "  ✅ Successful: $SUCCESS_COUNT directories"
echo "  ❌ Failed/Skipped: $FAILED_COUNT directories"

if [ $FAILED_COUNT -eq 0 ]; then
  echo ""
  echo "🎉 All utilities synced successfully!"
  echo ""
  echo "📝 Next steps:"
  echo "  1. Test your changes in individual scripts"
  echo "  2. All directories now use organized structure!"
  echo "  3. Use './clasp_helpers.sh push' to deploy any project"
  echo "  4. Utilities are in each project's shared-utilities/ directory"
  echo "  5. Update this script if you add new GAS directories"
else
  echo ""
  echo "⚠️  Some directories had issues. Check the output above."
fi

echo ""
echo "🔧 Files synced:"
echo "📁 Utility files (.gs):"
ls shared-utilities/*.gs | xargs -n 1 basename | sed 's/^/  • /'
echo ""
echo "🚀 Clasp Helper Scripts:"
echo "  • Each project has its own clasp_helpers.sh"
echo "  • All projects support './clasp_helpers.sh push'"
echo "  • Project-specific clasp management"
