# Waitlist New - Embeddable Signup Form

Advanced Google Apps Script web app for waitlist management with position tracking, multi-product support, and embeddable signup forms.

## Features

- **Multi-Product Waitlist Management**: Support for multiple products with static tab mapping
- **Position Tracking**: Shows user's position across all waitlists they've joined
- **Responsive Design**: Clean, mobile-optimized forms that work in iframes
- **Two-Phase Loading**: Immediate loading spinner with async data fetching for better UX
- **Data Collection**: First Name, Last Name, Email, Phone, Product ID, League info
- **Slack Notifications**: Comprehensive logging and error reporting
- **Gmail Integration**: Branded email confirmations using sendBarsEmail utility

## Setup

### 1. Build and Deploy

```bash
cd GoogleAppsScripts/projects/waitlist-new
node build.js
clasp push
```

### 2. Deploy as Web App

1. Open the script in Apps Script Editor
2. Click **Deploy** → **New deployment**
3. Select type: **Web app**
4. Execute as: **Me**
5. Who has access: **Anyone**
6. Click **Deploy**
7. Copy the web app URL

### 3. Configure Google Sheet

The script writes to:
- **Spreadsheet ID**: `1EatkTwZHJ28dPUH2YrTIN_fYi9m1h7s2zKCPbCMTgHo`
- **Product-Specific Tabs**: Uses static PRODUCT_TAB_MAPPING in config.js

Each tab has these columns:
1. Timestamp, 2. First Name, 3. Last Name, 4. Email, 5. Phone, 6. Product ID, 7. League, 8. Processed

## Usage

### Embed in Shopify (Locksmith Integration)

```html
<iframe
  src="https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec?productId=7590193332318&email={{ customer.email | default: '' }}&customerId={{ customer.id | default: '' }}&source=shopify"
  width="100%"
  height="600"
  frameborder="0">
</iframe>
```

### Query Parameters

- `productId` - Shopify product ID (required, used for tab mapping)
- `email` - User's email (shows position if already on waitlist)
- `customerId` - Shopify customer ID (alternative to email)
- `source` - Set to "shopify" for iframe optimization
- `league` - Product/league display name

### Example URLs

```
# Position check (existing user)
https://script.google.com/macros/s/YOUR_ID/exec?productId=7590193332318&email=user@example.com&source=shopify

# New signup form
https://script.google.com/macros/s/YOUR_ID/exec?productId=7590193332318&source=shopify
```

## Architecture

### Project Structure

```
src/
├── controllers/          # Entry points that route requests
│   ├── processRequest.js      # Main doGet/doPost with SheetsClient initialization
│   ├── handleDoGet.js         # GET logic with loading page + async data fetching
│   └── handleDoPost.js        # POST signup processing
│
├── integrations/         # External service clients
│   ├── SheetsClient.js        # Google Sheets operations with direct column access
│   ├── SlackClient.js         # Slack client class
│   ├── slackNotifications.js  # Slack webhook notifications
│   └── emailUtils.js          # Gmail client with BARS branding
│
├── services/             # Core business logic
│   ├── calculateWaitlistPositions.js  # Position calculation across products
│   ├── handleSignups.js              # Signup processing and validation
│   └── validateInputs.js             # Input validation functions
│
├── ui/                   # User interface rendering
│   ├── generateStyles.js      # CSS generation and utility scripts
│   ├── renderPages.js         # Page rendering with loading spinner support
│   └── templates/components/  # HTML component templates
│       ├── backButton.html
│       ├── baseLayout.html
│       ├── checkForm.html
│       ├── formInteractions.html
│       ├── formStyles.html
│       ├── joinForm.html
│       ├── mainButtons.html
│       ├── noPositionsMessage.html
│       ├── noPositionsStyles.html
│       ├── otherPositions.html
│       ├── positionCard.html
│       ├── positionStyles.html
│       ├── redirectScript.html
│       ├── successMessage.html
│       └── suggestionBox.html
│
└── config.js            # Static product mapping + spreadsheet config
```

### Request Flows

#### GET Flows
1. **Position Display**: `email/customerId + productId`
   ```
   doGet → handleDoGet → renderLoadingPage → getPositionData → calculateWaitlistPositions → renderPositionsPage
   ```

2. **New User Form**: `productId only`
   ```
   doGet → handleDoGet → renderLoadingPage → getPositionData → renderLockedProductPage
   ```

#### POST Flows
1. **Waitlist Signup**: `form submission`
   ```
   doPost → handleDoPost → handleSignups → SheetsClient.appendRow → emailUtils → renderSuccessPage
   ```

### Active Files

- **Controllers**: `processRequest.js`, `handleDoGet.js`, `handleDoPost.js` - Request routing and handling
- **Integrations**: `SheetsClient.js`, `SlackClient.js`, `slackNotifications.js`, `emailUtils.js` - External service clients
- **Services**: `calculateWaitlistPositions.js`, `handleSignups.js`, `validateInputs.js` - Business logic
- **UI**: `generateStyles.js`, `renderPages.js` - Styling and page rendering
- **UI Templates**: 14 HTML component files in `templates/components/` - Modular UI components
- **Core**: `config.js` - Configuration and static product mapping

### Key Features

- **Static Product Mapping**: PRODUCT_TAB_MAPPING in config.js maps Shopify product IDs to sheet tab names
- **Loading Spinner System**: Two-phase loading with immediate HTML + async google.script.run calls
- **CORS Solution**: Uses google.script.run instead of fetch to avoid iframe restrictions
- **Position Prioritization**: Shows specified product first, others in "also on waitlist" section
- **Smart Slack Filtering**: Only sends failure notifications and final results to avoid spam
- **Mobile Responsive**: CSS adapts for mobile + iframe contexts

## Development

### Local Development

1. Make changes in `src/`
2. Run `node build.js` to build into `deploy_temp/`
3. Run `clasp push` to deploy
4. Test in browser

### Configuration

Edit `src/config.js`:
- **SPREADSHEET_ID**: Target Google Sheet
- **PRODUCT_TAB_MAPPING**: Static mapping of Shopify product IDs to tab names
- **COLUMNS**: Column definitions for sheet operations
- **WEBHOOK_URL**: Slack notifications endpoint

### Permissions

Required OAuth scopes:
- `https://www.googleapis.com/auth/spreadsheets` - Read/write Google Sheets
- `https://www.googleapis.com/auth/gmail.send` - Send branded emails
- `https://www.googleapis.com/auth/script.external_request` - Slack webhooks

## Testing

Use the test script to generate realistic test data:

```bash
python read_waitlist_data.py
```

This reads actual sheet data and generates test URLs showing:
- ✅ Existing users (should show positions)
- 🟡 Processed users (should show signup form)
- 🔴 New users (should show signup form)
