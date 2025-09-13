# 🔧 Pre-Commit Hook Guide

## 🤔 Why Pre-Commit "Fails" After Auto-Fixing

When you see this:
```
trim trailing whitespace.................................................Failed
- hook id: trailing-whitespace
- exit code: 1
- files were modified by this hook

Fixing .github/workflows/deploy-to-render.yml
```

This is **intentional behavior**, not a bug! Pre-commit:
1. ✅ **Auto-fixes** the issues (trailing whitespace, formatting)
2. ❌ **"Fails"** to force you to review the changes
3. 🔄 **Requires re-commit** so you see what was changed

## 🚀 Smoother Workflow Options

### Option 1: Run Pre-Commit Before Committing
```bash
# Run pre-commit first to fix all issues
pre-commit run --all-files

# Then commit (will pass cleanly)
git add .
git commit -m "your message"
```

### Option 2: Use Git Aliases (Recommended)
Add to your `~/.gitconfig`:
```ini
[alias]
    # Smart commit: runs pre-commit, then commits
    sc = !git add . && pre-commit run --all-files && git add . && git commit

    # Quick commit: commits with pre-commit auto-fixes
    qc = !f() { git add . && git commit -m "$1" || (git add . && git commit -m "$1"); }; f
```

Then use:
```bash
git sc -m "your message"  # Smart commit
git qc "your message"     # Quick commit
```

### Option 3: Configure Pre-Commit to be Less Strict

If you want pre-commit to auto-fix and continue without failing:

```yaml
# In .pre-commit-config.yaml
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.8.2
  hooks:
    - id: ruff
      args: [--fix, --exit-zero]  # Don't fail on fixable issues
    - id: ruff-format
      # Formatting always continues
```

## 🎯 Current Configuration

Your pre-commit hooks:
- ✅ **Auto-fix**: trailing whitespace, missing newlines, ruff formatting
- ❌ **Still fail on**: unfixable linting errors, large files, invalid YAML
- 🔄 **Require review**: when files are modified (safety feature)

## 💡 Recommendation

Keep the current behavior for safety, but use **Option 2** (git aliases) for a smoother workflow. This ensures you always review auto-fixes while making commits faster.
