#!/usr/bin/env python3
"""CI wrapper for running script functions."""
import sys
from pathlib import Path

# Add shared utilities to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared_utilities"))
from paths import get_repo_root

project_root = get_repo_root()
sys.path.insert(0, str(project_root))

from scripts._shared.path_utils import PROJECT_ROOT

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/ci/run_script.py <module.path> <function_name>")
        sys.exit(1)

    module_path, function_name = sys.argv[1], sys.argv[2]

    try:
        module = __import__(module_path, fromlist=[function_name])
        func = getattr(module, function_name)
        sys.exit(func())
    except ImportError as e:
        print(f"❌ Failed to import module '{module_path}': {e}")
        sys.exit(1)
    except AttributeError as e:
        print(f"❌ Function '{function_name}' not found in module '{module_path}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error running function: {e}")
        sys.exit(1)

