"""Pytest path wiring for AWS Lambda function unit tests.

These tests live outside the function directories on purpose: test files must
never be bundled into a function's deploy zip (the deploy rsyncs from the
function dir). They still import each function's runtime modules directly, so
we put each function's dir on ``sys.path`` here — ``from validation import …``
then resolves to the function under test.

Add a function's directory name to ``_FUNCTION_DIRS`` when its tests land here.
"""

import sys
from pathlib import Path

_FUNCTIONS_ROOT = Path(__file__).resolve().parent.parent / "functions"

_FUNCTION_DIRS = (
    "ShopifyRefundHandler",
)

for _name in _FUNCTION_DIRS:
    sys.path.insert(0, str(_FUNCTIONS_ROOT / _name))
