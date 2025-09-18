#!/usr/bin/env bash
set -e
cd "."
PROJECT_DIR="/Users/jrandazzo/Documents/BARS_Github/BigAppleRecSports/.."
if [ -f /run_tests.sh ]; then
  echo "🧪 Running parse-registration-info function tests..."
  (cd  && ./run_tests.sh)
else
  echo "ℹ️ parse-registration-info run_tests.sh not found; skipping"
fi
