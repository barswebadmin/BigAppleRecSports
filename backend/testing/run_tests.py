#!/usr/bin/env python3
"""Backend test runner."""

import os
import subprocess
import sys
from pathlib import Path


def setup_test_environment():
    """Set up environment variables for backend tests."""
    os.environ.update({
        "SHOPIFY_URL_ADMIN_DOMAIN": "test-store.myshopify.com",
        "SHOPIFY_TOKEN": "test_token",
        "ENVIRONMENT": "test",
        "SLACK_REFUNDS_BOT_TOKEN": "test_slack_token",
    })


def discover_test_paths(test_type: str | None = None) -> list[str]:
    """Discover test paths based on test type.
    
    Args:
        test_type: 'unit', 'integration', or None for all
        
    Returns:
        List of test paths relative to backend directory
    """
    backend_dir = Path(__file__).parent.parent
    test_paths = []
    
    if not test_type or test_type == "unit":
        # Standard unit tests
        if (backend_dir / "tests" / "unit").exists():
            test_paths.append("tests/unit")
        
        # Service tests
        for service_tests in (backend_dir / "services").rglob("tests"):
            if service_tests.is_dir():
                test_paths.append(str(service_tests.relative_to(backend_dir)))
        
        # Router tests
        if (backend_dir / "routers" / "tests").exists():
            test_paths.append("routers/tests")
    
    if not test_type or test_type == "integration":
        if (backend_dir / "tests" / "integration").exists():
            test_paths.append("tests/integration")
    
    return test_paths


def run_tests(test_type: str | None = None) -> int:
    """Run backend tests.
    
    Args:
        test_type: 'unit', 'integration', or None for all
        
    Returns:
        Exit code (0 for success)
    """
    setup_test_environment()
    
    backend_dir = Path(__file__).parent.parent
    test_paths = discover_test_paths(test_type)
    
    if not test_paths:
        print("⚠️  No test files found")
        return 0
    
    print(f"🧪 Running backend tests ({test_type or 'all'})...")
    cmd = [sys.executable, "-m", "pytest", "-v"] + test_paths
    result = subprocess.run(cmd, cwd=backend_dir, check=False)
    return result.returncode


if __name__ == "__main__":
    test_type = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(run_tests(test_type))
