# Shared Build Tools for Google Apps Script Projects

Generic, reusable build and deployment scripts for GAS projects using ES6 modules and esbuild.

---

## **Scripts**

### **gas-esbuild.js**
Bundles ES6 modules into a single GAS-compatible file.

**Features:**
- Bundles all ES6 imports into single file
- Strips `import`/`export` statements
- Preserves GAS trigger functions
- Configurable via `esbuild.config.js`

### **gas-clasp-push.sh** and **gas-clasp-pull.sh**
Push and pull scripts for Google Apps Script using clasp.

**Features:**
- Build detection and execution
- Change comparison with remote
- User prompts for confirmation
- Automatic cleanup of temp files

---

## **Setup for New Projects**

### **1. Create esbuild.config.js**

```javascript
module.exports = {
  entryPoints: ['src/index.js'],
  buildDir: 'build',
  outputFile: 'Code.js',
  srcDir: 'src',
  target: 'es2020',
  keepNames: true,
  minify: false,
};
```

### **2. Create build.js wrapper**

```javascript
/**
 * Build script for [project-name]
 * Delegates to shared GAS esbuild tool
 */

require('../../remote-sync-tools/build.js');
```

### **3. Create clasp-deploy.config.sh (optional)**

```bash
#!/bin/bash

# Project-specific configuration for clasp deployment

export PACKAGE_MANAGER="pnpm"  # or npm, yarn
export BUILD_DIR="build"
export OUTPUT_FILE="Code.js"
export DEPLOY_TEMP="deploy_temp"
```

### **4. Deploy using Makefile**

Use the centralized Makefile commands from the repository root:

```bash
# Push to GAS
make clasp push <project-name>

# Pull from GAS
make clasp pull <project-name>

# Full deployment (push + version management)
make clasp deploy <project-name>
```

Or call the scripts directly:

```bash
# From repository root
bash GoogleAppsScripts/remote-sync-tools/push.sh <project-name>
bash GoogleAppsScripts/remote-sync-tools/pull.sh <project-name>
bash GoogleAppsScripts/remote-sync-tools/deploy.sh <project-name>
```

---

## **Usage**

### **Build only**
```bash
pnpm build
```

### **Deploy to GAS**
```bash
make clasp push <project-name>
# or for full deployment with version management:
make clasp deploy <project-name>
```

### **Clean build artifacts**
```bash
pnpm clean
# or
pnpm clean <project-name>
```

---

## **Configuration Options**

### **esbuild.config.js**

| Option | Default | Description |
|--------|---------|-------------|
| `entryPoints` | `['src/index.js']` | Entry point files |
| `buildDir` | `'build'` | Output directory |
| `outputFile` | `'Code.js'` | Output filename |
| `srcDir` | `'src'` | Source directory |
| `target` | `'es2020'` | ES target version |
| `keepNames` | `true` | Preserve function names |
| `minify` | `false` | Minify output |

### **clasp-deploy.config.sh**

| Variable | Default | Description |
|----------|---------|-------------|
| `PACKAGE_MANAGER` | `pnpm` | Package manager (npm/pnpm/yarn) |
| `BUILD_DIR` | `build` | Build output directory |
| `OUTPUT_FILE` | `Code.js` | Output filename |
| `DEPLOY_TEMP` | `deploy_temp` | Temp deployment directory |
| `PROJECT_NAME` | Directory name | Project name for logging |

---

## **File Structure**

```
GoogleAppsScripts/
├── remote-sync-tools/
│   ├── README.md                    # This file
│   ├── build.js                     # Generic build script
│   ├── push.sh                      # Push to GAS
│   ├── pull.sh                      # Pull from GAS
│   ├── deploy.sh                     # Full deployment (push + version management)
│   ├── clean.sh                      # Clean build artifacts
│   └── shared-helpers.sh             # Shared helper functions
└── projects/
    └── your-project/
        ├── src/
        │   ├── index.js            # Entry point
        │   ├── appsscript.json     # GAS config
        │   └── ...                 # Your source files
        ├── build.js                # Wrapper (3 lines)
        ├── (no clasp_helpers.sh - use centralized scripts)
        ├── esbuild.config.js       # Build config
        ├── clasp-deploy.config.sh  # Deploy config (optional)
        ├── .clasp.json             # Clasp config
        └── package.json            # Dependencies
```

---

## **Troubleshooting**

### **"No esbuild.config.js found"**
Create `esbuild.config.js` in your project root with required configuration.

### **"clasp command not found"**
Install clasp globally: `npm install -g @google/clasp`

### **"already up to date" on push**
The script automatically clears cache and retries. If it persists, check the GAS editor.

### **Syntax errors in GAS**
Check `build/Code.js` - ensure no `import`/`export` statements remain.

---

## **Example Project**

See `projects/waitlist-script-comprehensive/` for a complete working example.

