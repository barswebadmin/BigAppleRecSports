#!/usr/bin/env bash
set -e
cd "."
PROJECT_DIR="/Users/jrandazzo/Documents/BARS_Github/BigAppleRecSports/.."
if [ -f /run_comprehensive_tests.sh ]; then
  echo "🧪 Running parse-registration-info comprehensive tests..."
  (cd  && ./run_comprehensive_tests.sh)
else
  echo "ℹ️ parse-registration-info run_comprehensive_tests.sh not found; skipping"
fi
