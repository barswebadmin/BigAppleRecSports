# Google Apps Scripts for BARS

> 📚 **Documentation**: See [README.md](../README.md#google-apps-scripts) for overview and [README_EXT/2_DEPLOYMENT.md#google-apps-scripts-deployment](../README_EXT/2_DEPLOYMENT.md#google-apps-scripts-deployment) for deployment

This directory contains all Google Apps Scripts used by Big Apple Rec Sports, with proper version control and deployment capabilities.

## Scripts

1. **BARS Waitlist Script** (`1yL5crj6zjclY7HJPBi6A5owO5mBWoT6kfIHv-MoBHC82h9jmn1Pp9v-4`)
   - Directory: `projects/waitlist-script/`
   - Description: Manages waitlist functionality

2. **BARS Product/Variant Creation Script** (`1ag91SToLXcAFBIbGY_WSze5gdVlBr9qqaJNwO6e9ie7qOXRAcBo607qK`)
   - Directory: `projects/product-variant-creation/`
   - Description: Creates products and variants in Shopify

3. **Parse Registration Information** (`17FMYl1kMlOTpZ3jseg5nmoMmREK7IN1CXHKgKW5A-z8Q__nb8VhBWei-`)
   - Directory: `projects/parse-registration-info/`
   - Description: Parses and processes registration data

4. **BARS - Process Refunds and Exchanges** (`1JQ9qnEIji4E6t2sBnzZ1CErcWZjfj36Qp-rqqJEZxNa0sXIFtRYo54CS`)
   - Directory: `projects/process-refunds-exchanges/`
   - Description: Handles refund and exchange workflows

5. **Process Leadership Discount Codes** (`1V46lPoFAUe5gGb1RL5f3TQJxoYnM29Wt1zcGN4hhgbsxCY578mAi-fzP`)
   - Directory: `projects/leadership-discount-codes/`
   - Description: Manages leadership discount code processing

6. **Process Payment Assistance and Add Customer Tags** (`1Y3JSpgtgxwF7tfBlCAKgbGmc6qjxfsWA_leE56FUT20mOafY12nqFLb7`)
   - Directory: `projects/payment-assistance-tags/`
   - Description: Processes payment assistance requests and manages customer tags

7. **Add Veteran Tags and Email Players** (`REPLACE_WITH_VETERAN_TAGS_SCRIPT_ID`)
   - Directory: `projects/veteran-tags/`
   - Description: Adds veteran tags to customer profiles and sends veteran emails

## Setup Instructions

### 1. Authentication
```bash
clasp login
```

### 2. Clone a script for development
```bash
cd GoogleAppsScripts/projects/[script-directory]
clasp clone [SCRIPT_ID]
```

### 3. Push changes to Google Apps Script
```bash
clasp push
```

### 4. Deploy changes
```bash
clasp deploy
```

### 5. Sync shared utilities (when updated)
```bash
# From GoogleAppsScripts directory
./sync-utilities.sh
```

This copies the latest utilities from `shared-utilities/` to all script directories.

## Secret Management

All secrets should be stored in Google Apps Script's PropertiesService instead of hardcoded values:

### Setting Secrets (run once in Apps Script console):
```javascript
PropertiesService.getScriptProperties().setProperties({
  'SHOPIFY_TOKEN': 'your_shopify_token_here',
  'SLACK_TOKEN': 'your_slack_token_here',
  'API_ENDPOINT': 'your_api_endpoint_here'
});
```

### Using Secrets in Code:
```javascript
const SHOPIFY_TOKEN = PropertiesService.getScriptProperties().getProperty('SHOPIFY_TOKEN');
```

## Development Workflow

1. **Make changes locally** in your preferred editor
2. **Test immediately**: `clasp push` to push to Google Apps Script for testing
3. **Commit to git** when ready for version control
4. **Deploy**: `clasp deploy` when ready for production

## Directory Structure
```
GoogleAppsScripts/
├── projects/                     # All Google Apps Script projects
│   ├── waitlist-script/
│   ├── product-variant-creation/
│   ├── parse-registration-info/
│   ├── process-refunds-exchanges/
│   ├── leadership-discount-codes/
│   ├── payment-assistance-tags/
│   └── veteran-tags/
├── shared-utilities/             # Common utility functions
├── scripts/                      # Deployment and management scripts
└── tests/                        # Test suites
```
