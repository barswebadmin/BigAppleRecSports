# BARS Smart Git Commit Setup

## 🎯 What This Does
Automatically handles pre-commit formatting fixes so you can run `git commit` once and it "just works" - no more running it twice when only whitespace issues are found.

## 🔧 Setup Instructions

### Option 1: Use the script directly
```bash
# From any BARS repo directory:
./scripts/git-commit-bars -m "your commit message"
```

### Option 2: Auto-override git commit (Recommended)
Add this line to your `~/.zshrc` file:

```bash
# BARS Smart Git Commit
source ~/Documents/scripts/zshrc_scripts
```

Then reload your shell: `source ~/.zshrc`

Now `git commit` will automatically use smart commit in BARS repos!

## ✅ How It Works

1. **First Attempt**: Runs `git commit` normally
2. **If It Fails**: Checks if the failure was due to auto-formatting fixes
3. **Auto-Recovery**: If formatting issues were found and fixed:
   - Automatically stages the fixes (`git add .`)
   - Re-runs the commit
   - Shows success message
4. **Real Failures**: If it's not a formatting issue, shows the original error

## 🛡️ Safety Features

- **BARS-Only**: Only works in directories containing "BARS_Github"
- **Non-Invasive**: Doesn't affect other repositories
- **Transparent**: Shows exactly what it's doing
- **Fallback**: If script is missing, uses regular git commit

## 🎉 Usage Examples

```bash
# These now work seamlessly, even with formatting issues:
git commit -m "feat: add new feature"
git commit -am "fix: update logic"
git commit -m "refactor: improve code structure"
```

No more seeing pre-commit failures and having to run the commit twice! 🚀
