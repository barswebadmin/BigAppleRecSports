#!/usr/bin/env python3
"""Debug parser auto-export issue"""

import sys
sys.path.append('.')
import tempfile
from pathlib import Path

# Create test that mimics the exact issue
test_dir = Path(tempfile.mkdtemp())
test_module = test_dir / "test_parsers"
test_module.mkdir()

# Create file with same name as function (the issue!)
(test_module / "__init__.py").write_text("")
(test_module / "parse_shopify_response.py").write_text('''
def parse_shopify_response(data):
    """Function to parse response"""
    return "parsed"

def another_function():
    return "another"
''')

sys.path.insert(0, str(test_dir))

# Test auto_export with name collision
from backend.shared.auto_export import auto_export_module

test_globals = {'__name__': 'test_parsers', '__path__': [str(test_module)]}
exports = auto_export_module([str(test_module)], test_globals)

print(f"Exports found: {exports}")
print(f"Globals keys: {[k for k in test_globals.keys() if not k.startswith('_')]}")

# Check what parse_shopify_response is
if 'parse_shopify_response' in test_globals:
    obj = test_globals['parse_shopify_response']
    print(f"parse_shopify_response type: {type(obj)}")
    print(f"parse_shopify_response callable: {callable(obj)}")
    print(f"parse_shopify_response has __file__: {hasattr(obj, '__file__')}")
    if hasattr(obj, '__file__'):
        print(f"parse_shopify_response __file__: {obj.__file__}")

# Cleanup
import shutil
shutil.rmtree(test_dir)

print("\n🚧 ISSUE: Module and function have same name causing collision!")
