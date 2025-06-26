# 🚀 Lambda Function Version Management

This directory uses **automatic version management** to track changes to lambda functions. Every time you modify a lambda function, its version number is automatically incremented.

## 📋 How It Works

### 🔄 Automatic Version Increment
- **When you commit changes** to any lambda function, the version is automatically incremented
- **Build numbers increase**: `1.0.0.1` → `1.0.0.2` → `1.0.0.3`
- **Last updated date** is refreshed automatically
- **Version files are staged** and included in your commit

### 📁 Version Files
Each lambda function has a `version.py` file with:
```python
__version__ = "1.0.0"      # Major.Minor.Patch
__build__ = 1              # Auto-incremented build number
__last_updated__ = "2024-06-26"  # Auto-updated date

def get_version():
    return __version__

def get_full_version():
    return f"{__version__}.{__build__}"
```

## 🛠️ Setup (One-time)

Run the setup script to install the version management system:

```bash
# Make setup script executable and run it
chmod +x scripts/setup_version_management.sh
./scripts/setup_version_management.sh
```

This installs:
- ✅ **Pre-commit git hook** for local development
- ✅ **GitHub Action workflow** for remote changes  
- ✅ **Version files** for all lambda functions
- ✅ **Version manager script** with auto-detection

## 🎯 Usage Examples

### Normal Development Workflow
```bash
# 1. Edit your lambda function
vi lambda-functions/CreateScheduleLambda/lambda_function.py

# 2. Stage your changes
git add lambda-functions/CreateScheduleLambda/

# 3. Commit (version auto-increments!)
git commit -m "feat: improve schedule creation logic"

# Output:
# 🔍 Checking for lambda function changes...
# 📝 Running automatic version increment...
# ✅ Updated CreateScheduleLambda: 1.0.0.1 → 1.0.0.2
# 📝 Staged 1 version file(s) for commit
```

### Using Versions in Your Code
```python
# In your lambda function:
from version import get_version, get_full_version

def lambda_handler(event, context):
    print(f"Lambda version: {get_full_version()}")
    
    return {
        'statusCode': 200,
        'body': {
            'version': get_version(),
            'build': get_full_version()
        }
    }
```

## 🔧 System Components

### 1. **Pre-commit Hook** (`.githooks/pre-commit`)
- Runs **before each commit**
- Detects lambda function changes
- Automatically increments version numbers
- Stages updated version files

### 2. **GitHub Action** (`.github/workflows/lambda-version-increment.yml`)
- Runs on **pushes to main**
- Backup system for remote changes
- Handles team collaboration scenarios
- Creates automatic version commits

### 3. **Version Manager** (`scripts/version_manager.py`)
- Core logic for version detection and increment
- Parses git changes to find modified lambda functions
- Updates version files with new build numbers
- Handles date stamps and staging

## 📊 Lambda Functions with Version Management

Current lambda functions with automatic versioning:

- ✅ `changePricesOfOpenAndWaitlistVariants/`
- ✅ `createScheduledPriceChanges/`
- ✅ `CreateScheduleLambda/`
- ✅ `MoveInventoryLambda/`
- ✅ `schedulePriceChanges/`

## 🚨 Important Notes

### ⚠️ Do NOT Edit Version Files Manually
- Version files are **auto-generated**
- Manual edits will be **overwritten**
- Let the system manage versions automatically

### 🔄 Build Number vs Version Number
- **Version** (`1.0.0`): Manual semantic versioning (major.minor.patch)
- **Build** (`1`, `2`, `3`): Auto-incremented on every change
- **Full Version** (`1.0.0.3`): Combines both for unique identification

### 🎯 When Versions Increment
Versions increment when you modify:
- ✅ Lambda function code (`lambda_function.py`)
- ✅ Requirements files (`requirements.txt`)
- ✅ Configuration files
- ✅ Documentation in lambda directories
- ❌ **NOT** when you only modify `version.py` (prevents infinite loops)

## 🧪 Testing the System

Test that version management is working:

```bash
# 1. Make a small change to any lambda function
echo "# Test comment" >> lambda-functions/CreateScheduleLambda/lambda_function.py

# 2. Stage and commit
git add lambda-functions/CreateScheduleLambda/
git commit -m "test: version increment system"

# 3. Check that version was incremented
cat lambda-functions/CreateScheduleLambda/version.py
```

## 🔍 Troubleshooting

### Pre-commit Hook Not Running
```bash
# Check git hooks configuration
git config core.hooksPath
# Should show: .githooks

# Re-run setup if needed
./scripts/setup_version_management.sh
```

### Version Not Incrementing
```bash
# Manually run version manager to debug
python3 scripts/version_manager.py

# Check if files are staged
git diff --cached --name-only
```

### GitHub Action Not Triggering
- Check that changes are in `lambda-functions/` directory
- Ensure you're pushing to `main` branch
- Verify the workflow file exists in `.github/workflows/`

## 🎉 Benefits

- 📈 **Automatic tracking** of all lambda function changes
- 🔍 **Easy debugging** with unique build numbers
- 📊 **Deployment tracking** with timestamps
- 🤝 **Team collaboration** with consistent versioning
- 🚀 **Zero maintenance** once set up

---

*This system automatically maintains version numbers so you can focus on coding! 🚀* 