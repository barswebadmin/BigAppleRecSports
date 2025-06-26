# 🚀 Backend Version Management & Changelog

The BARS backend uses **automatic semantic versioning** and **changelog generation** to track all changes and improvements. Every commit automatically updates version numbers and generates changelog entries.

## 📋 How It Works

### 🔄 Semantic Versioning
The backend follows [Semantic Versioning (SemVer)](https://semver.org/):
- **MAJOR** (`2.0.0`): Breaking changes, API changes
- **MINOR** (`1.1.0`): New features, backwards compatible
- **PATCH** (`1.0.1`): Bug fixes, backwards compatible
- **BUILD** (`1.0.0.4`): Auto-incremented build number

### 🤖 Automatic Detection
The system analyzes your commits and determines the version bump:

| Change Type | Triggers | Example |
|-------------|----------|---------|
| **Major** | API breaking changes, `BREAKING:` in commit | `feat: BREAKING change to API` |
| **Minor** | New features, `feat:` commits, API additions | `feat: add new endpoint` |
| **Patch** | Bug fixes, `fix:` commits | `fix: resolve authentication issue` |
| **Build** | Other changes | `docs: update README` |

### 📝 Automatic Changelog
- **Categorizes changes**: Features, Bug Fixes, Breaking Changes
- **Extracts from commits**: Uses conventional commit messages
- **Lists files changed**: Shows what was modified
- **Formats professionally**: Follows Keep a Changelog format

## 🎯 Conventional Commits

Use these commit prefixes for automatic categorization:

```bash
# Features (minor version bump)
feat: add new leadership endpoint
feature: implement email validation

# Bug fixes (patch version bump)  
fix: resolve CORS issue
bugfix: fix authentication timeout
patch: update error handling

# Breaking changes (major version bump)
feat: BREAKING change to API structure
BREAKING: remove deprecated endpoints

# Other changes (build increment only)
docs: update API documentation
refactor: improve code structure
test: add integration tests
style: fix formatting
```

## 📁 Version Files

### `backend/version.py`
Contains current version information:
```python
__version__ = "1.0.2"           # Semantic version
__build__ = 3                   # Auto-incremented build
__last_updated__ = "2025-06-26" # Last change date
__codename__ = "Render Ready"   # Release codename

def get_version_info():
    return {
        "version": __version__,
        "full_version": f"{__version__}.{__build__}",
        "last_updated": __last_updated__,
        "codename": __codename__
    }
```

### `backend/CHANGELOG.md`
Professional changelog with:
- ✨ **Features**: New functionality
- 🐛 **Bug Fixes**: Issue resolutions  
- 💥 **Breaking Changes**: API changes
- 🔧 **Other Changes**: Documentation, refactoring
- 📁 **Files Changed**: What was modified

## 🚀 API Integration

Version information is available through multiple endpoints:

### `GET /` - Root Endpoint
```json
{
  "message": "Big Apple Rec Sports API",
  "version": "1.0.2",
  "build": 3,
  "full_version": "1.0.2.3",
  "codename": "Render Ready",
  "last_updated": "2025-06-26",
  "environment": "production"
}
```

### `GET /health` - Health Check
```json
{
  "status": "healthy",
  "version": "1.0.2",
  "build": 3,
  "full_version": "1.0.2.3",
  "environment": "production",
  "last_updated": "2025-06-26"
}
```

### `GET /version` - Detailed Version Info
```json
{
  "version": "1.0.2",
  "build": 3,
  "full_version": "1.0.2.3",
  "last_updated": "2025-06-26",
  "codename": "Render Ready"
}
```

## 🛠️ Development Workflow

### Normal Development
```bash
# 1. Create feature branch and make changes
git checkout -b feature/email-validation
vi backend/services/leadership_service.py

# 2. Commit with conventional format (no version update yet)
git add backend/services/leadership_service.py
git commit -m "feat: add email validation to leadership processing"

# 3. Push and create PR
git push origin feature/email-validation

# 4. Merge PR to main - version updates automatically! 🎉
# Output (on merge to main):
# 📝 This is a merge commit - will update version
# 📈 Version bump: minor (1.0.2 → 1.1.0)
# ✅ Updated version.py and CHANGELOG.md
```

### Using Version in Code
```python
# In your backend code
from version import get_version_info

def some_function():
    version_info = get_version_info()
    print(f"Running backend version {version_info['full_version']}")
    
    return {
        "data": "some data",
        "version": version_info["version"]
    }
```

## 🔧 System Components

### 1. **Pre-commit Hook** (`.githooks/pre-commit`)
- Handles lambda function versioning only
- Backend versioning happens on merge/deploy
- Keeps commits clean during development

### 2. **Version Manager** (`scripts/backend_version_manager.py`)
- Analyzes commit messages for version type
- Implements semantic versioning rules
- Generates professional changelog entries
- Updates version file with new information

### 3. **Version Module** (`backend/version.py`)
- Stores current version information
- Provides version access functions
- Maintains version history
- Integrates with FastAPI application

## 📊 File Change Analysis

The system intelligently determines version bumps based on files changed:

| Files Changed | Impact | Version Bump |
|---------------|--------|--------------|
| `main.py`, `config.py` | Critical system files | Major/Minor |
| `routers/`, `models/` | API changes | Minor |
| `services/` | Business logic | Patch/Minor |
| `requirements.txt` | Dependencies | Patch |
| Documentation only | No functional impact | Build only |

## 🧪 Testing Version Management

Test the system with a sample change:

```bash
# 1. Make a test change
echo "# Test comment" >> backend/main.py

# 2. Stage and commit
git add backend/main.py
git commit -m "feat: test version management system"

# 3. Check version was updated
cat backend/version.py
cat backend/CHANGELOG.md
```

## 🔍 Troubleshooting

### Version Not Updating
```bash
# Check if backend files are staged
git diff --cached --name-only | grep backend/

# Manually run backend version manager
python3 scripts/backend_version_manager.py

# Check pre-commit hook is installed
git config core.hooksPath
```

### Changelog Not Generated
```bash
# Verify the changelog file exists
ls -la backend/CHANGELOG.md

# Check commit message format
git log --oneline -1

# Use conventional commit format
git commit --amend -m "feat: proper conventional commit message"
```

### Wrong Version Bump Type
The system analyzes:
1. **Commit messages** (conventional commits)
2. **Files changed** (critical vs regular)
3. **Keywords** (`BREAKING`, `feat:`, `fix:`)

Use proper conventional commits for accurate version bumps.

## 🎉 Benefits

- 📈 **Merge-based versioning** - Versions update only on deployment
- 📝 **Professional changelogs** - Auto-generated from PR merges
- 🔍 **Easy debugging** - Version info in API responses
- 📊 **Deployment tracking** - Clear version history tied to releases
- 🤝 **Team collaboration** - Clean feature branch workflow
- 🚀 **Zero maintenance** - Fully automated on merge to main

## 🏷️ Current Version Status

- **Current Version**: `1.0.2`
- **Build Number**: `3`
- **Codename**: "Render Ready"
- **Last Updated**: `2025-06-26`

---

*Automatic version management keeps your backend professionally versioned! 🚀* 