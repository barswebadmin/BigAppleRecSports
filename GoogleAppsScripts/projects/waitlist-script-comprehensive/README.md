# Unified Waitlist System

Consolidated waitlist management system for BARS combining form management, customer workflows, and API integrations.

## 🎯 Current Status: PULL OFF WAITLIST READY

### ✅ Implemented Features
- **Pull Off Waitlist Workflow** - Admin can tag customers in Shopify and email them
- Core infrastructure (routing, utilities, Shopify integration)
- Configuration management

### 🚧 Pending Features
- Form submission processing
- Waitlist position checking
- Shopify webhook handling
- Add product to form automation

---

## 📁 Project Structure

```
waitlist-template/
├── appsscript.json          # GAS configuration
├── config/
│   └── constants.js         # All constants and configuration
├── core/
│   ├── doPost.js           # POST endpoint router
│   └── onOpen.js           # Spreadsheet menu
├── workflows/
│   └── pullOffWaitlist.js  # Pull player off waitlist
├── helpers/
│   ├── emailHelpers.js     # Email sending
│   ├── productHandleHelpers.js  # Product handle parsing
│   └── utils.js            # General utilities
└── shared-utilities/
    ├── sheetUtils.js       # Google Sheets helpers
    ├── SlackUtils.js       # Slack integration
    ├── secretsUtils.js     # Secrets management
    └── ShopifyUtils.js     # Shopify API calls
```

---

## 🚀 Deployment Instructions

### Step 1: Push to Google Apps Script

```bash
cd /path/to/GoogleAppsScripts/projects/waitlist-template
clasp push
```

### Step 2: Configure Secrets

In Google Apps Script Editor, go to **Project Settings** → **Script Properties** and add:

```
SHOPIFY_ACCESS_TOKEN_ADMIN = your_shopify_admin_token
SLACK_BOT_TOKEN_WAITLIST = your_slack_bot_token (optional)
SLACK_CHANNEL_JOE_TEST = your_slack_channel_id (optional)
```

### Step 3: Link to Spreadsheet

1. Open your waitlist spreadsheet
2. Go to **Extensions** → **Apps Script**
3. Paste the script ID from `.clasp.json`
4. Or deploy directly from the script editor

### Step 4: Test the Workflow

1. Open the waitlist spreadsheet
2. You should see "🏳️‍🌈 BARS Workflows" menu appear (if not, refresh)
3. Click **BARS Workflows** → **Pull Someone Off Waitlist**
4. Enter a test row number
5. Verify:
   - Customer is tagged in Shopify
   - Email is sent (if you chose to send)
   - Row is marked "Processed"

---

## 📖 Usage Guide

### Pull Someone Off Waitlist

**Purpose:** Tag a customer in Shopify with a product-specific waitlist tag and optionally email them registration instructions.

**Steps:**
1. Open the waitlist spreadsheet
2. Find the row of the person to pull off
3. Click **BARS Workflows** → **Pull Someone Off Waitlist**
4. Enter the row number (the number before column A)
5. The system will:
   - Look up or create the customer in Shopify by email
   - Add a waitlist tag: `{product-handle}-waitlist`
   - Update their phone number
   - Mark the row as "Processed"
6. You'll be prompted to email the player
7. If emailing, you'll be asked if multiple players were pulled (adds urgency text)

**Example:**
- Row 5 has `john@example.com` for "Kickball - Sunday - Open Division"
- Tag added: `2025-fall-kickball-sunday-opendiv-waitlist`
- Customer can now access the product page when signed in

---

## 🔧 Configuration

### Spreadsheet Requirements

The spreadsheet must have these columns:
- **Timestamp** - When they joined waitlist
- **Email Address** - Customer email
- **First Name** - Customer first name
- **Last Name** - Customer last name (optional)
- **Phone Number** - Customer phone (optional)
- **Please select the league you want to sign up for** - League name
- **Notes** - For marking "Processed" or "Canceled"

### Spreadsheet Naming Convention

The spreadsheet name must include the season and year:
- ✅ "Fall 2025 Waitlist (Responses)"
- ✅ "Spring 2024 Waitlist"
- ❌ "Waitlist Form" (missing season/year)

This is used to construct product handles automatically.

### Product Handle Construction

Handles are constructed as:
```
{year}-{season}-{sport}-{day}-{division}div
```

Examples:
- `2025-fall-kickball-sunday-opendiv`
- `2024-spring-dodgeball-tuesday-wtnbdiv`

If auto-construction fails, you'll be prompted to enter it manually.

---

## 🔐 Security

### Secrets Management

Never commit secrets. Always use PropertiesService:

```javascript
// To set a secret:
PropertiesService.getScriptProperties()
  .setProperty('SHOPIFY_ACCESS_TOKEN_ADMIN', 'your_token');

// To get a secret:
const token = getSecret('SHOPIFY_ACCESS_TOKEN_ADMIN');
```

### Shopify Permissions

The Shopify access token needs:
- `read_customers`
- `write_customers`
- `read_products`

---

## 🐛 Troubleshooting

### Menu doesn't appear
1. Refresh the spreadsheet
2. Check that `onOpen()` trigger is installed
3. Run `onOpen()` manually from script editor

### "Customer not found" error
- Verify Shopify token is set correctly
- Check token has `read_customers` permission
- Ensure email is valid

### "Invalid handle" error
- Check spreadsheet name includes season and year
- Verify league format is correct: "Sport - Day - Division"
- Enter handle manually when prompted

### Email not sending
- Check MailApp permissions are granted
- Verify BARS_LOGO_URL is accessible
- Check leadership email mapping in `utils.js`

---

## 📝 Development Notes

### Adding New Sports

Update `config/constants.js`:
```javascript
const SPORTS = ['Dodgeball', 'Kickball', 'YourNewSport', ...];
```

### Adding New Leagues

Update `helpers/utils.js` → `getLeadershipEmailForLeague()`:
```javascript
'YourNewSport - Sunday - Open Division': 'newsport@bigapplerecsports.com'
```

### Testing Locally

```javascript
// In Apps Script Editor
function testPullOffWaitlist() {
  // Manually set up test data
  pullOffWaitlist();
}
```

---

## 🔄 Next Steps

To enable remaining features:
1. Implement form submission processing
2. Implement waitlist position checking (GET endpoint)
3. Implement Shopify webhook handler
4. Implement add product to form handler

See `MERGE_PLAN.md` for full implementation roadmap.

---

## 📞 Support

For issues or questions:
- Technical: `web@bigapplerecsports.com`
- Operations: `executive-board@bigapplerecsports.com`

---

## 📜 License

Internal BARS system - Not for external use



