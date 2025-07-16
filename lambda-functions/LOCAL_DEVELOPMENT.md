# 🛠️ Local Development Setup for Lambda Functions

This guide explains how to set up local development so that `bars_common_utils` imports work correctly in your IDE and local Python environment.

## 🎯 Problem

Lambda functions import shared utilities from the `bars_common_utils` layer:

```python
from bars_common_utils.event_utils import parse_event_body
from bars_common_utils.response_utils import format_response
```

These imports work in AWS Lambda (where the layer is available), but fail locally because Python can't find the module.

## ✅ Solution

We use symbolic links to make the lambda layer available to each function locally.

### 🚀 Quick Setup

1. **Install dependencies:**
   ```bash
   pip3 install boto3
   ```

2. **Set up lambda layer symlinks:**
   ```bash
   python3 scripts/setup_local_development.py
   ```

3. **Set AWS region (optional but recommended):**
   ```bash
   export AWS_DEFAULT_REGION=us-east-1
   ```

This creates symlinks in each lambda function directory:
```
lambda-functions/
├── schedulePriceChanges/
│   ├── bars_common_utils -> ../../lambda-layers/bars-common-utils/python/bars_common_utils
│   └── lambda_function.py
├── MoveInventoryLambda/
│   ├── bars_common_utils -> ../../lambda-layers/bars-common-utils/python/bars_common_utils
│   └── lambda_function.py
└── ... (all other functions)
```

### 🔍 Verify Setup

Check that symlinks are working:

```bash
# List the symlink
ls -la lambda-functions/*/bars_common_utils

# Verify contents are accessible
ls lambda-functions/schedulePriceChanges/bars_common_utils/
# Should show: __init__.py, event_utils.py, response_utils.py, etc.
```

### 🧹 Cleanup (if needed)

To remove all symlinks:

```bash
python3 scripts/setup_local_development.py cleanup
```

## 📋 What This Setup Provides

### ✅ Working Imports
All lambda functions can now import from:

**bars_common_utils layer:**
- `event_utils` - Event parsing and validation
- `response_utils` - HTTP response formatting
- `shopify_utils` - Shopify API operations
- `scheduler_utils` - EventBridge scheduler utilities
- `date_utils` - Date parsing and calculations
- `request_utils` - HTTP request utilities

**AWS SDK:**
- `boto3` - AWS services (EventBridge Scheduler, etc.)

**Standard library:**
- `urllib`, `json`, `datetime`, `zoneinfo` - Built-in Python modules

### ✅ IDE Support
Your IDE (VS Code, PyCharm, etc.) will:
- ✅ Recognize imports (no red squiggly lines)
- ✅ Provide autocomplete for layer functions
- ✅ Allow "Go to Definition" navigation
- ✅ Show proper type hints

### ✅ Local Testing
You can run and test lambda functions locally:

```python
# This will work locally now
from bars_common_utils.event_utils import parse_event_body

def test_my_lambda():
    event = {"body": '{"test": "data"}'}
    body = parse_event_body(event)
    assert body["test"] == "data"
```

## 🔐 Git Considerations

### Symlinks are Git-Ignored
The symlinks are added to `.gitignore`:
```gitignore
# Lambda layer symlinks (for local development)  
lambda-functions/*/bars_common_utils
```

This ensures:
- ❌ Symlinks are **NOT** committed to git
- ✅ Production deployments work normally
- ✅ AWS Lambda uses the actual layer (not symlinks)

### Team Development
Each developer needs to run the setup script on their machine:
```bash
python3 scripts/setup_local_development.py
```

## 🚀 Production Deployment

The symlinks don't affect production deployment:

1. **GitHub Actions** packages lambda functions without symlinks
2. **AWS Lambda** uses the actual `bars-common-utils` layer
3. **Imports work normally** in the AWS environment

## 🐛 Troubleshooting

### Import Errors Still Occur

1. **Re-run the setup script:**
   ```bash
   python3 scripts/setup_local_development.py
   ```

2. **Check symlink status:**
   ```bash
   ls -la lambda-functions/*/bars_common_utils
   ```

3. **Verify layer exists:**
   ```bash
   ls lambda-layers/bars-common-utils/python/bars_common_utils/
   ```

### IDE Not Recognizing Imports

1. **Restart your IDE** after running setup
2. **Refresh project** if using VS Code
3. **Clear Python cache** if needed:
   ```bash
   find . -name "__pycache__" -exec rm -rf {} +
   ```

### Permission Issues

If symlink creation fails with permission errors:
```bash
# Make script executable
chmod +x scripts/setup_local_development.py

# Run with proper permissions
python3 scripts/setup_local_development.py
```

## 📚 Available Utilities

### Event Utilities (`event_utils.py`)
```python
from bars_common_utils.event_utils import (
    parse_event_body,
    validate_required_fields,
    get_field_safe
)
```

### Response Utilities (`response_utils.py`)
```python
from bars_common_utils.response_utils import (
    format_response,
    format_error
)
```

### Shopify Utilities (`shopify_utils.py`)
```python
from bars_common_utils.shopify_utils import (
    get_inventory_item_and_quantity,
    adjust_inventory,
    get_product_variants
)
```

### Date Utilities (`date_utils.py`)
```python
from bars_common_utils.date_utils import (
    parse_date,
    parse_time,
    calculate_discounted_schedule
)
```

### Scheduler Utilities (`scheduler_utils.py`)
```python
from bars_common_utils.scheduler_utils import (
    create_schedule_target
)
```

### Request Utilities (`request_utils.py`)
```python
from bars_common_utils.request_utils import (
    wait_until_next_minute
)
```

---

## 🎉 You're Ready to Go!

Your lambda functions now have full access to the shared utilities layer for local development. Happy coding! 🚀 