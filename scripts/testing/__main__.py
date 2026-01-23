"""Entry point for python -m scripts.testing (delegates to run_tests.main)."""
from .run_tests import main

if __name__ == "__main__":
    import sys
    sys.exit(main())
