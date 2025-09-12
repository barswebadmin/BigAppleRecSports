#!/bin/bash
# Safe commit script - apply fixes and test before committing

echo "🔧 Applying safe ruff fixes..."
python -m ruff check . --fix --select "F541,E701,W292,I001" --quiet

echo "🔍 Checking for breaking changes..."
python -c "
import subprocess
import sys

# Quick compilation check
try:
    result = subprocess.run(['python', '-m', 'py_compile', '-q'], 
                          capture_output=True, cwd='backend')
    if result.returncode != 0:
        print('❌ Compilation errors found')
        sys.exit(1)
except:
    pass  # py_compile not available, skip

# Quick backend test
result = subprocess.run(['python', '-m', 'pytest', 'backend/tests/', '-x', '--tb=no', '-q'], 
                       capture_output=True)
if result.returncode != 0:
    print('❌ Tests failed')
    print(result.stdout.decode()[-200:])  # Last 200 chars
    sys.exit(1)

print('✅ All checks passed!')
"

if [ $? -eq 0 ]; then
    echo "🎉 Safe to commit!"
    git add .
    git commit "$@"
else
    echo "❌ Issues found - manual review needed"
    echo "💡 Run 'git diff' to see what ruff changed"
fi
