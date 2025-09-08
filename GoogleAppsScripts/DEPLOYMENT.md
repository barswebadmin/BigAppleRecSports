# 🚀 Google Apps Script Automated Deployment System

This document describes the comprehensive CI/CD system for automatically deploying Google Apps Script projects when changes are merged to the master branch.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Setup Instructions](#setup-instructions)
- [Usage](#usage)
- [Scripts Reference](#scripts-reference)
- [Troubleshooting](#troubleshooting)
- [Advanced Configuration](#advanced-configuration)

## 🎯 Overview

This system provides:

1. **Automatic deployment** when changes are merged to master
2. **Version management** with automatic cleanup of old versions
3. **doGet/doPost detection** with alerts for web app changes
4. **Manual deployment tools** for development and testing
5. **Comprehensive logging** and error handling

## ✨ Features

### 🔄 Automatic Deployment
- Detects changes to Google Apps Script projects
- Deploys only changed projects (not all projects)
- Manages the 200 version limit automatically
- Creates deployment with descriptive names and timestamps

### 🚨 doGet/doPost Detection
- Scans for changes to web app endpoint functions
- Creates GitHub issues for critical changes
- Provides clear alerts about deployment requirements
- Pre-commit hooks for early warning

### 📊 Version Management
- Automatically cleans up old versions when approaching 200 limit
- Keeps the most recent 10 versions for safety
- Provides detailed logging of cleanup operations
- Graceful handling of cleanup failures

### 🛠️ Developer Tools
- Manual deployment scripts
- Authentication setup helpers
- Change detection utilities
- Pre-commit hooks

## 🛠️ Setup Instructions

### 1. Enable Google Apps Script API
1. Go to [Google Apps Script API Settings](https://script.google.com/home/usersettings)
2. Turn on "Google Apps Script API"

### 2. Setup Local Authentication
```bash
cd GoogleAppsScripts
./scripts/setup-clasp-auth.sh setup-local
```

### 3. Get CI/CD Credentials
```bash
./scripts/setup-clasp-auth.sh show-credentials
```

### 4. Add GitHub Secret
1. Go to your GitHub repository
2. Navigate to Settings → Secrets and variables → Actions
3. Create a new secret:
   - **Name**: `CLASP_CREDENTIALS`
   - **Value**: The JSON output from step 3

### 5. Install Pre-commit Hook (Optional)
```bash
# From repository root
ln -s ../../GoogleAppsScripts/scripts/pre-commit-hook.sh .git/hooks/pre-commit
```

## 🎮 Usage

### Automatic Deployment
1. Make changes to any Google Apps Script project
2. Commit and push to master branch
3. GitHub Actions automatically detects changes
4. Only modified projects are deployed
5. Check the Actions tab for deployment status

### Manual Deployment
```bash
# Deploy a specific project
./scripts/deploy-project.sh leadership-discount-codes

# Deploy current project (auto-detect)
cd projects/leadership-discount-codes
../../scripts/deploy-project.sh

# Force deployment even without changes
./scripts/deploy-project.sh leadership-discount-codes --force

# Just create a version without deploying
./scripts/deploy-project.sh leadership-discount-codes --version-only
```

### Check for doGet/doPost Changes
```bash
# Check last commit
./scripts/detect-webapp-changes.sh

# Check staged changes
./scripts/detect-webapp-changes.sh --staged

# Check specific commit range
./scripts/detect-webapp-changes.sh HEAD~5..HEAD
```

### Test Authentication
```bash
./scripts/setup-clasp-auth.sh test-auth
```

## 📚 Scripts Reference

### 🔧 Core Scripts

#### `scripts/manage-versions-and-deploy.js`
- **Purpose**: Handles version cleanup and deployment
- **Features**: 
  - Automatically cleans old versions when approaching 200 limit
  - Creates new deployment with timestamp and commit info
  - Provides detailed logging for CI/CD
- **Usage**: Called automatically by GitHub Actions

#### `scripts/deploy-project.sh`
- **Purpose**: Manual deployment tool for developers
- **Features**:
  - Auto-detects project if run from project directory
  - Checks for uncommitted changes
  - Detects doGet/doPost functions
  - Shows web app URLs
- **Usage**: `./scripts/deploy-project.sh [project-name] [options]`

#### `scripts/detect-webapp-changes.sh`
- **Purpose**: Detects doGet/doPost function changes
- **Features**:
  - Scans all Google Apps Script projects
  - Identifies web app endpoint changes
  - Provides deployment instructions
  - Can check commits or staged changes
- **Usage**: `./scripts/detect-webapp-changes.sh [commit-range]`

#### `scripts/setup-clasp-auth.sh`
- **Purpose**: Authentication setup and management
- **Features**:
  - Local clasp login
  - CI/CD credentials extraction
  - Authentication testing
  - Project validation
- **Usage**: `./scripts/setup-clasp-auth.sh [command]`

#### `scripts/pre-commit-hook.sh`
- **Purpose**: Pre-commit validation
- **Features**:
  - Warns about doGet/doPost changes before commit
  - Allows user to proceed or cancel
  - Provides next-step instructions
- **Installation**: `ln -s ../../GoogleAppsScripts/scripts/pre-commit-hook.sh .git/hooks/pre-commit`

### 🤖 GitHub Actions

#### `.github/workflows/auto-deploy-gas.yml`
- **Triggers**: Push to master, manual dispatch
- **Jobs**:
  1. **detect-changes**: Scans for modified projects and doGet/doPost changes
  2. **deploy-gas-projects**: Deploys changed projects in parallel
  3. **alert-doget-dopost**: Creates alerts/issues for web app changes
  4. **deployment-summary**: Provides overall status

## 🔍 Troubleshooting

### Common Issues

#### ❌ "Not logged in to clasp"
```bash
./scripts/setup-clasp-auth.sh setup-local
```

#### ❌ "Apps Script API not enabled"
1. Go to [Apps Script API Settings](https://script.google.com/home/usersettings)
2. Enable "Google Apps Script API"

#### ❌ "No .clasp.json found"
```bash
cd [project-directory]
clasp create --type standalone --title "Project Name"
# Or clone existing:
clasp clone [script-id]
```

#### ❌ "HTTP 403: Rate Limit Exceeded"
- Wait a few minutes and retry
- The system includes automatic delays to prevent this

#### ❌ "Version limit exceeded"
- The system automatically manages this
- Check logs to see cleanup operations
- Manually clean: `clasp deployments` and `clasp undeploy [id]`

### Debugging

#### Check deployment status:
```bash
cd [project]
clasp deployments
clasp status
```

#### Test authentication:
```bash
./scripts/setup-clasp-auth.sh test-auth
```

#### Validate all projects:
```bash
./scripts/setup-clasp-auth.sh validate-projects
```

## ⚙️ Advanced Configuration

### Customizing Version Limits
Edit `scripts/manage-versions-and-deploy.js`:
```javascript
const MAX_VERSIONS = 200;           // Apps Script limit
const CLEANUP_THRESHOLD = 190;      // When to start cleanup
const KEEP_RECENT_VERSIONS = 10;    // Always keep N recent versions
```

### Adding New Projects
1. Add project directory name to `GAS_PROJECTS` array in:
   - `.github/workflows/auto-deploy-gas.yml`
   - `scripts/detect-webapp-changes.sh`
   - `scripts/setup-clasp-auth.sh`

2. Ensure project has `.clasp.json` file

### Customizing Deployment Descriptions
Edit `scripts/manage-versions-and-deploy.js`:
```javascript
const description = `Auto-deploy ${timestamp} (${gitCommit})`;
```

### Environment Variables

#### CI/CD Environment
- `CLASP_CREDENTIALS`: JSON credentials from `~/.clasprc.json`
- `PROJECT_NAME`: Current project being deployed
- `GITHUB_SHA`: Git commit hash (auto-provided)

#### Local Development
- No special environment variables needed
- Uses `~/.clasprc.json` for authentication

## 🎯 Best Practices

### Development Workflow
1. Make changes to Google Apps Script files
2. Test locally using Google Apps Script editor
3. Commit changes with descriptive messages
4. Push to master for automatic deployment
5. Monitor GitHub Actions for deployment status

### doGet/doPost Functions
- Always test web app endpoints after deployment
- Use the pre-commit hook to get early warnings
- Check GitHub issues for deployment alerts
- Remember: changes won't be active until deployed!

### Version Management
- The system handles version cleanup automatically
- Keep important versions by creating meaningful deployment descriptions
- Monitor cleanup logs in GitHub Actions

### Security
- Never commit `.clasprc.json` to version control
- Store `CLASP_CREDENTIALS` securely in GitHub Secrets
- Regularly rotate Google API credentials
- Use separate Google accounts for production vs development

## 📞 Support

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review GitHub Actions logs
3. Test authentication locally
4. Validate project configuration
5. Check Google Apps Script API quotas

## 🔗 Related Documentation

- [Google Apps Script CLI (clasp)](https://github.com/google/clasp)
- [Google Apps Script API](https://developers.google.com/apps-script/api)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Project Testing Guide](./TESTING_GUIDE.md)
