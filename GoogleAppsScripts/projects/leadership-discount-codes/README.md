# Leadership Discount Codes - Organized Structure

This Google Apps Script project uses an organized directory structure locally while flattening files for Google Apps Script deployment.

## 📁 Directory Structure

```
leadership-discount-codes/
├── processors/
│   └── leadershipProcessor.gs       # Main processing logic
├── shared-utilities/
│   ├── apiUtils.gs                  # API helper functions
│   ├── dateUtils.gs                 # Date utility functions
│   └── secretsUtils.gs              # Secret management
├── appsscript.json                  # GAS manifest
├── clasp_helpers.sh                 # Clasp management helpers
└── README.md                        # This file
```

## 🚀 Deployment Workflow

### Local Development
- Organize your code in directories for better structure
- Edit files in their respective directories
- Use meaningful directory names (processors/, shared-utilities/, etc.)

### Deployment to Google Apps Script
- Files are automatically flattened with directory prefixes
- Example: `shared-utilities/apiUtils.gs` → `shared-utilities_apiUtils.gs` in GAS

## 🛠️ Commands

```bash
# Push organized code to Google Apps Script
./clasp_helpers.sh push

# Pull from Google Apps Script and organize locally
./clasp_helpers.sh pull

# Check clasp status
./clasp_helpers.sh status

# Deploy a new version
./clasp_helpers.sh deploy

# Clean up temporary files
./clasp_helpers.sh cleanup

# Show help
./clasp_helpers.sh help
```

## 📝 File Mapping

| Local File | Google Apps Script File |
|------------|------------------------|
| `processors/leadershipProcessor.gs` | `processors_leadershipProcessor.gs` |
| `shared-utilities/apiUtils.gs` | `shared-utilities_apiUtils.gs` |
| `shared-utilities/dateUtils.gs` | `shared-utilities_dateUtils.gs` |
| `shared-utilities/secretsUtils.gs` | `shared-utilities_secretsUtils.gs` |
| `appsscript.json` | `appsscript.json` (unchanged) |

## ✨ Benefits

1. **Better Organization**: Logical directory structure for local development
2. **GAS Compatibility**: Automatically flattened for Google Apps Script
3. **Clear Separation**: Processors, utilities, and shared code in separate folders
4. **Easy Navigation**: VS Code can treat .gs files as JavaScript with proper directory structure
5. **Version Control**: Git-friendly organized structure

## 🔧 Setup

1. Make sure you have `clasp` installed and authenticated
2. Run `./clasp_helpers.sh push` to deploy organized code to Google Apps Script
3. Your local directory structure is preserved while GAS gets flattened files

## 🔄 Workflow

1. **Edit** files in organized directories locally
2. **Test** changes using `./clasp_helpers.sh push`
3. **Commit** organized structure to Git
4. **Deploy** production versions using `./clasp_helpers.sh deploy`

This setup gives you the best of both worlds: organized local development and Google Apps Script compatibility!
