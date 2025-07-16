# Local Development Setup

This guide explains how to set up local development for BARS Lambda Functions with full IDE support and proper import resolution.

## 🚀 Quick Setup

### 1. Run Setup Script
```bash
# From project root
python3 scripts/setup_local_development.py
```

This installs required dependencies:
- `boto3>=1.39.0` - AWS SDK for local testing
- `pytest>=7.0.0` - Testing framework
- `flake8>=7.0.0` - Code linting
- `coverage[toml]>=7.0.0` - Code coverage

### 2. Open in VS Code
The workspace-level configuration will automatically handle import resolution for all lambda functions.

## 📁 Project Structure

The project uses workspace-level configuration instead of duplicating code:

```
BigAppleRecSports/
├── .vscode/settings.json          # 🎯 Workspace Python configuration
├── pyproject.toml                 # 🎯 Pyright/pytest configuration  
├── lambda-layers/
│   └── bars-common-utils/
│       └── python/
│           └── bars_common_utils/ # 📦 Shared utilities (single source)
└── lambda-functions/
    ├── MoveInventoryLambda/       # ✅ No symlinks needed
    ├── shopifyProductUpdateHandler/
    └── ...
```

## 🔧 How It Works

### IDE Configuration
- **VS Code**: `.vscode/settings.json` configures Python paths workspace-wide
- **Pyright**: `pyproject.toml` provides import resolution for all tools
- **No symlinks**: Clean, DRY approach without code duplication

### Import Resolution
```python
# Works in all lambda functions
from bars_common_utils.date_utils import parse_date
from bars_common_utils.event_utils import parse_event_body

# Function-specific imports work too
from lambda_function import lambda_handler
```

## 🧪 Testing

### Run All Tests
```bash
cd lambda-functions/tests
python3 run_tests.py all
```

### Run Specific Tests
```bash
# Test specific function
python3 run_tests.py function --function MoveInventoryLambda

# Run with coverage
python3 run_tests.py coverage
```

### Test Individual Functions
```bash
# Test a function directly
cd lambda-functions/MoveInventoryLambda
python3 lambda_function.py  # If it has a main block
```

## 🔍 IDE Features

### Full IntelliSense Support
- ✅ Auto-completion for all imports
- ✅ Go to Definition across modules  
- ✅ Type checking and hints
- ✅ Error highlighting
- ✅ Refactoring support

### Debugging
- Set breakpoints in any lambda function
- Step through bars_common_utils code
- Full variable inspection

## 🛠️ Environment Variables

### Local Development
```bash
# AWS Region (used by boto3)
export AWS_DEFAULT_REGION=us-east-1

# Shopify credentials for testing (optional)
export SHOPIFY_ACCESS_TOKEN=your_token_here
export SHOPIFY_SHOP_DOMAIN=your_shop.myshopify.com
```

### Testing Environment
The test framework automatically sets required environment variables.

## 📦 Dependencies

### Core Dependencies
- **Python 3.9+** (matches AWS Lambda runtime)
- **boto3** - AWS SDK
- **pytest** - Testing framework

### Lambda Function Dependencies
Each function has its own `requirements.txt`:
- `lambda-functions/MoveInventoryLambda/requirements.txt`
- `lambda-functions/shopifyProductUpdateHandler/requirements.txt`
- etc.

## 🚀 Deployment

### Local Testing First
```bash
# Always run tests before deploying
cd lambda-functions/tests
python3 run_tests.py all

# Check linting
python3 -m flake8 ../
```

### AWS Deployment
Lambda functions deploy using the shared `bars-common-utils` layer:
- Layer contains shared utilities
- Functions import from layer at runtime
- No code duplication in deployment

## 🔄 Updating bars_common_utils

When updating shared utilities:
1. Edit files in `lambda-layers/bars-common-utils/python/bars_common_utils/`
2. Test changes: `cd lambda-functions/tests && python3 run_tests.py`
3. All lambda functions automatically get updates

## 🎯 Benefits of This Approach

### ✅ DRY (Don't Repeat Yourself)
- Single source of truth for shared code
- No symlinks or duplicated code
- Clean project structure

### ✅ Full IDE Support  
- IntelliSense works everywhere
- No import resolution errors
- Professional development experience

### ✅ Easy Maintenance
- Update shared code in one place
- Workspace-level configuration
- Clear separation of concerns

## 🐛 Troubleshooting

### Import Errors
If you see import errors:
1. Restart VS Code to reload configuration
2. Run: `python3 scripts/setup_local_development.py`
3. Check that `.vscode/settings.json` and `pyproject.toml` exist

### Missing Dependencies
```bash
# Reinstall dependencies
python3 -m pip install boto3 pytest flake8 coverage

# Or run setup again
python3 scripts/setup_local_development.py
```

### Test Failures
```bash
# Check test environment
cd lambda-functions/tests
python3 -c "import sys; print(sys.path)"

# Run specific test for debugging
python3 -m pytest unit/test_move_inventory_lambda.py::TestMoveInventoryLambda::test_veteran_to_early_move -v
``` 