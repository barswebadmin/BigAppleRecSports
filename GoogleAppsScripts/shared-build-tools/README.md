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

### **gas-clasp-deploy.sh**
Builds and deploys to Google Apps Script using clasp.

**Features:**
- Runs clean + build before deployment
- Handles clasp caching issues
- Configurable via `clasp-deploy.config.sh`
- Automatic retry on "already up to date" errors

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

require('../../shared-build-tools/gas-esbuild.js');
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

### **4. Create clasp_helpers.sh wrapper**

```bash
#!/bin/bash

# Project-specific clasp deployment wrapper
# Delegates to shared GAS clasp deployment script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/../../shared-build-tools/gas-clasp-deploy.sh" "$@"
```

### **5. Add package.json scripts**

```json
{
  "scripts": {
    "build": "node build.js",
    "clean": "rm -rf build/",
    "deploy": "./clasp_helpers.sh push"
  },
  "devDependencies": {
    "esbuild": "^0.27.2"
  }
}
```

---

## **Usage**

### **Build only**
```bash
pnpm build
```

### **Deploy to GAS**
```bash
./clasp_helpers.sh push
```

### **Clean build artifacts**
```bash
pnpm clean
# or
./clasp_helpers.sh clean
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
├── shared-build-tools/
│   ├── README.md                    # This file
│   ├── gas-esbuild.js              # Generic build script
│   └── gas-clasp-deploy.sh         # Generic deployment script
└── projects/
    └── your-project/
        ├── src/
        │   ├── index.js            # Entry point
        │   ├── appsscript.json     # GAS config
        │   └── ...                 # Your source files
        ├── build.js                # Wrapper (3 lines)
        ├── clasp_helpers.sh        # Wrapper (6 lines)
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

