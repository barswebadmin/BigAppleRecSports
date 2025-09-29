#!/usr/bin/env python3
"""Tests for auto_export utility"""

import sys
import tempfile
import shutil
from pathlib import Path
import pytest

sys.path.append('.')
from backend.shared.auto_export import auto_export_module


def test_auto_export_functionality():
    """Test auto_export_module with various scenarios"""
    
    test_cases = [
        {
            "name": "basic_functions_and_classes",
            "modules": {
                "module_a.py": '''
def public_function():
    return "test"

class PublicClass:
    pass

def _private_function():
    return "private"
                '''
            },
            "expected_exports": ["PublicClass", "public_function"],
            "excluded": ["_private_function"]
        },
        {
            "name": "multiple_modules",
            "modules": {
                "builders.py": '''
def build_order_request(data):
    return {"query": "order", "data": data}

class RequestBuilder:
    pass
                ''',
                "parsers.py": '''
def parse_response(data):
    return data

class ResponseParser:
    pass
                '''
            },
            "expected_exports": ["build_order_request", "RequestBuilder", "parse_response", "ResponseParser"],
            "excluded": []
        },
        {
            "name": "mixed_public_private",
            "modules": {
                "utils.py": '''
def public_util():
    return "public"

def _private_util():
    return "private"

class PublicUtil:
    pass

class _PrivateUtil:
    pass

CONSTANT = "value"
_PRIVATE_CONSTANT = "private"
                '''
            },
            "expected_exports": ["PublicUtil", "public_util"],
            "excluded": ["_private_util", "_PrivateUtil", "_PRIVATE_CONSTANT"]
        }
    ]
    
    for i, case in enumerate(test_cases):
        print(f"\n🧪 Testing: {case['name']}")
        
        # Create temporary test module with unique name
        test_dir = Path(tempfile.mkdtemp())
        test_module_name = f"test_module_{i}"
        test_module = test_dir / test_module_name
        test_module.mkdir()
        
        try:
            # Create __init__.py
            (test_module / "__init__.py").write_text("")
            
            # Create module files
            for filename, content in case["modules"].items():
                (test_module / filename).write_text(content)
            
            # Test auto_export_module
            sys.path.insert(0, str(test_dir))
            test_globals = {'__name__': test_module_name, '__path__': [str(test_module)]}
            
            exports = auto_export_module([str(test_module)], test_globals)
            
            # Verify expected exports
            for expected in case["expected_exports"]:
                assert expected in exports, f"❌ Expected '{expected}' in exports, got: {exports}"
                assert expected in test_globals, f"❌ Expected '{expected}' in globals"
                print(f"   ✅ Found expected export: {expected}")
            
            # Verify excluded items
            for excluded in case["excluded"]:
                assert excluded not in exports, f"❌ '{excluded}' should not be exported, got: {exports}"
                print(f"   ✅ Correctly excluded: {excluded}")
            
            # Test __all__ assignment
            test_globals['__all__'] = exports
            assert len(test_globals['__all__']) == len(case["expected_exports"]), \
                f"❌ __all__ length mismatch: expected {len(case['expected_exports'])}, got {len(test_globals['__all__'])}"
            
            # Test function execution if available
            if 'build_order_request' in test_globals:
                func = test_globals['build_order_request']
                result = func({"id": "123"})
                assert result == {"query": "order", "data": {"id": "123"}}, f"❌ Function execution failed: {result}"
                print(f"   ✅ Function execution test passed")
            
            print(f"   ✅ {case['name']}: {len(exports)} exports found")
            
        finally:
            # Cleanup
            if str(test_dir) in sys.path:
                sys.path.remove(str(test_dir))
            shutil.rmtree(test_dir)
    
    print(f"\n🎉 All auto-export functionality tests passed!")
    print(f"   ✅ Functions and classes properly discovered")
    print(f"   ✅ Private items correctly excluded")  
    print(f"   ✅ __all__ correctly populated")
    print(f"   ✅ Exported functions are callable")


if __name__ == "__main__":
    test_auto_export_functionality()
