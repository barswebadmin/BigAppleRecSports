# Pre-Commit Hooks Setup

This repository uses pre-commit hooks to ensure code quality and validate CI deployment logic before commits.

## Quick Setup

```bash
# Install pre-commit (if not already installed)
pip install pre-commit

# Install the hooks
pre-commit install
```

## What's Validated

### CI Deployment Logic Tests
✅ **Lambda layer deployment is properly restricted to manual-only**
✅ **Self-contained deployment will only copy needed modules**
✅ **BARS sport detection works correctly (only 4 sports)**
✅ **Workflows are properly isolated**
✅ **Dependency detection logic is configured correctly**

### Code Quality
✅ **Trailing whitespace removal**
✅ **End-of-file fixing**
✅ **YAML validation**
✅ **Large file detection**
✅ **Python code formatting (Black)**
✅ **Python linting (Flake8)**

## Manual Testing

Run all hooks on all files:
```bash
pre-commit run --all-files
```

Run only CI deployment tests:
```bash
pre-commit run test-deploy-workflows --all-files
```

## What This Prevents

🚫 **Accidental lambda layer overwrites**
🚫 **Incorrect CI trigger configurations**
🚫 **Broken BARS sport detection**
🚫 **Non-selective shared utility deployment**
🚫 **Workflow configuration conflicts**
🚫 **Code quality issues**

## Files Monitored

The CI deployment tests run when these files change:
- `.github/workflows/*.yml`
- `shared-utilities/**/*`
- `lambda-functions/**/*`

## Benefits

✅ **Immediate feedback** - Catches issues before they reach CI/CD
✅ **Fast execution** - Runs in ~0.1 seconds
✅ **Comprehensive coverage** - Tests all critical deployment logic
✅ **Zero maintenance** - Automatically runs on every commit
✅ **Clear error messages** - Shows exactly what's wrong when tests fail
