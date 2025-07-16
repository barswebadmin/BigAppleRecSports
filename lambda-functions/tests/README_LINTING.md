# Test Directory Linting Configuration

This document explains the linting and import resolution setup for the lambda function tests.

## Fixed Issues

### 1. Flake8 Style Issues ✅
- Line length violations (reduced to manageable limits)
- Whitespace and formatting issues
- Import organization
- Missing newlines at end of files

### 2. Import Resolution Issues ✅
- Lambda function imports (from different directories)
- bars_common_utils imports (from lambda layer)
- Optional dependency imports (like coverage)

## Configuration Files

### `.flake8`
- Configures flake8 linting rules
- Sets max line length to 88 characters
- Ignores auto-fixable style issues
- Allows necessary exceptions for test files

### `pyproject.toml`
- Configures Pyright/Pylance for proper import resolution
- Sets up Python paths for all lambda functions
- Configures pytest paths

### `.vscode/settings.json`
- VS Code specific configuration
- Ensures proper Python path resolution in the IDE
- Enables auto-import completions

## Import Strategy

### Lambda Function Imports
```python
from lambda_function import lambda_handler  # type: ignore
```

### bars_common_utils Imports
```python
from bars_common_utils.date_utils import parse_date  # type: ignore
```

### Optional Dependency Imports
```python
try:
    import coverage  # type: ignore
    print("✅ coverage already installed")
except ImportError:
    print("📦 Installing coverage...")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'coverage[toml]'])
    import coverage  # type: ignore
```

## Usage

### Running Linter
```bash
# From tests directory
python3 -m flake8 run_tests.py unit/

# Should show 0 errors
```

### Running Tests
```bash
# From tests directory
python3 run_tests.py all
```

## Notes

- `# type: ignore` comments suppress Pylance import resolution warnings
- The actual imports work correctly at runtime due to sys.path modifications
- All configuration files work together to provide clean linting in both CLI and IDE 