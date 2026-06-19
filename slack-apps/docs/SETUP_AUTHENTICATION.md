# Firebase & Google API Setup with Domain-Wide Delegation

This guide explains how to configure **shared** Firebase and Google API authentication with service account domain-wide delegation for **multiple** Slack apps.

## Overview

Your Slack apps will use:
- **Shared Authentication**: One set of credentials for all bots (registrations-bot, marketing-bot, etc.)
- **Firebase Firestore** for data persistence (waitlists, registrations, marketing campaigns)
- **Google APIs** (Sheets, Drive, Gmail, Calendar) with domain-wide delegation
- **Service Account Authentication** to act on behalf of domain users without individual auth
- **Centralized Management**: All bots import from `@bars/shared/` directory

## 1. Prerequisites

You need:
- ✅ **Existing service account credentials** (you already have these in .env)
- ✅ **Google Workspace admin access** for domain-wide delegation
- ✅ **Firebase project** (optional - can use existing Google Cloud project)

## 2. Configure Domain-Wide Delegation

From your existing service account credentials JSON file, get the `client_id` value:

```bash
# If credentials are in a file
cat your-service-account.json | grep -o '"client_id": "[^"]*"'

# If credentials are in environment variable
echo $GOOGLE_SERVICE_ACCOUNT_CREDENTIALS | grep -o '"client_id": "[^"]*"'
```

### Configure Google Admin Console

1. Go to [Google Admin Console](https://admin.google.com)
2. Navigate to **Security** > **API Controls** > **Domain-wide delegation**
3. Click **Add new** and enter:
   - **Client ID**: `{your_client_id_from_above}`
   - **OAuth Scopes**:
     ```
     https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/admin.directory.user,https://www.googleapis.com/auth/gmail.send,https://www.googleapis.com/auth/calendar
     ```
4. Click **Authorize**

## 3. Firebase Setup (Optional)

If you want to use Firestore for data persistence:

### Option A: Use Existing Google Cloud Project
Your service account likely already has access to a Google Cloud project. Just enable Firestore:

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Add your existing Google Cloud project to Firebase
3. Enable Firestore Database in Native mode

### Option B: Create New Firebase Project
1. Go to [Firebase Console](https://console.firebase.google.com)
2. Create new project or import existing Google Cloud project
3. Enable Firestore Database

### Firestore Security Rules
Set these rules for service account access:
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Allow service account full access
    match /{document=**} {
      allow read, write: if request.auth != null;
    }
  }
}
```

## 7. Shared Authentication Structure

### Directory Layout
```
slack-apps/
├── shared/                     # Shared authentication & clients
│   ├── auth/
│   │   ├── firebase_client.ts  # Firebase Admin SDK implementation
│   │   └── google_auth.ts      # Google APIs with domain delegation
│   ├── config/
│   │   └── environment.ts      # Shared environment config
│   ├── firebase_client.ts      # Firebase client (exposed)
│   └── google_client.ts        # Google API client (exposed)
├── registrations-bot/          # Uses @bars/firebase and @bars/google
├── marketing-bot/              # Uses @bars/firebase and @bars/google
├── deno.json                   # Root config with shared imports
└── test_shared_auth.ts         # Test script for shared auth
```

### Import Path Mapping
All bots use **two clear clients** via import mapping:
```typescript
// In any bot function - clear separation of concerns
import { firebaseClient } from "@bars/firebase";  // For Firestore operations
import { googleClient } from "@bars/google";      // For Google API operations
import { getAdminUserEmail } from "@bars/shared/config/environment.ts";
```

## 4. Environment Configuration (Set Once for All Bots)

### Set Environment Variables for Slack CLI

Use your existing service account credentials:

```bash
# Use your existing service account credentials
slack env add GOOGLE_SERVICE_ACCOUNT_CREDENTIALS "$(cat path/to/your/service-account.json | tr -d '\n')"

# Or if already in environment variable
slack env add GOOGLE_SERVICE_ACCOUNT_CREDENTIALS "$GOOGLE_SERVICE_ACCOUNT_CREDENTIALS"

# Domain Configuration
slack env add DEFAULT_USER_DOMAIN "bigapplerecsports.com"
slack env add ADMIN_USER_EMAIL "admin@bigapplerecsports.com"

# Optional: Master spreadsheet for data sync
slack env add MASTER_SPREADSHEET_ID "your-google-sheets-id"

# Development mode
slack env add DENO_ENV "development"
```

### Local Development (.env file)
You can use your existing `.env` file - just ensure these variables are set:

```bash
# Your existing credentials
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS='{"type": "service_account", "project_id": "...", ...}'
DEFAULT_USER_DOMAIN=bigapplerecsports.com
ADMIN_USER_EMAIL=admin@bigapplerecsports.com
MASTER_SPREADSHEET_ID=your-google-sheets-id  # optional
DENO_ENV=development
```

## 5. Test Shared Authentication

### Shared Test Script
The `test_shared_auth.ts` script validates that all bots can use the same credentials:

### Run Shared Test
```bash
cd slack-apps
deno run --allow-net --allow-env --allow-read test_shared_auth.ts
```

Expected output:
```
🎉 All Shared Authentication Tests Passed!

📋 What this means:
  ✅ Both registrations-bot and marketing-bot can use the same credentials
  ✅ No need to duplicate environment variables
  ✅ Centralized authentication management
  ✅ Consistent API access across all bots
```

### Individual Bot Tests
Each bot also has its own test script:
```bash
# Test registrations bot specifically
cd registrations-bot
deno run test-auth

# Test marketing bot specifically
cd marketing-bot
deno run test-auth
```

## 6. Usage Examples (Same Code for All Bots)

### Firebase Operations
```typescript
import { firebaseClient } from "@bars/firebase";

// Registrations bot: Store waitlist entry
await firebaseClient.addDoc("waitlists", {
  player_name: "John Doe",
  league_id: "spring-2026-basketball",
  position: 1,
  created_at: new Date(),
  notified: false
});

// Marketing bot: Store campaign data (same client!)
await firebaseClient.addDoc("campaigns", {
  name: "Spring Registration Drive",
  status: "pending",
  created_at: new Date(),
  requested_by: "team@bigapplerecsports.com"
});

// Query operations
const waitlistData = await firebaseClient.queryCollection(
  "waitlists",
  "league_id",
  "==",
  "spring-2026-basketball"
);
```

### Google Sheets Operations
```typescript
import { googleClient } from "@bars/google";
import { getAdminUserEmail } from "@bars/shared/config/environment.ts";

// Read waitlist data from Google Sheets (works in any bot)
const adminEmail = getAdminUserEmail();
const sheets = await googleClient.sheets(adminEmail);

const response = await sheets.spreadsheets.values.get({
  spreadsheetId: "your-spreadsheet-id",
  range: "Waitlist!A1:Z1000"
});
const waitlistData = response.data.values || [];

// Write to Google Sheets
await sheets.spreadsheets.values.update({
  spreadsheetId: "your-spreadsheet-id",
  range: "Waitlist!A1:C1",
  valueInputOption: 'RAW',
  requestBody: {
    values: [["Name", "League", "Position"]]
  }
});

// Append to Google Sheets
await sheets.spreadsheets.values.append({
  spreadsheetId: "your-spreadsheet-id",
  range: "Waitlist!A:C",
  valueInputOption: 'RAW',
  requestBody: {
    values: [["John Doe", "Spring Basketball", "1"]]
  }
});
```

### Gmail Operations
```typescript
import { googleClient } from "@bars/google";

// Works from any bot - registrations bot example
const gmail = await googleClient.gmail("registrations@bigapplerecsports.com");
const emailBody = [
  `To: player@example.com`,
  `Subject: You're off the waitlist!`,
  `Content-Type: text/plain; charset=utf-8`,
  '',
  `Great news! A spot opened up in your league.`
].join('\n');

await gmail.users.messages.send({
  userId: 'me',
  requestBody: {
    raw: btoa(emailBody).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
  }
});

// Works from any bot - marketing bot example
const marketingGmail = await googleClient.gmail("marketing@bigapplerecsports.com");
const campaignEmailBody = [
  `To: team@bigapplerecsports.com`,
  `Subject: New Campaign Request`,
  `Content-Type: text/plain; charset=utf-8`,
  '',
  `A new marketing campaign has been created.`
].join('\n');

await marketingGmail.users.messages.send({
  userId: 'me',
  requestBody: {
    raw: btoa(campaignEmailBody).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
  }
});
```

## 8. Security Best Practices

### Service Account Permissions
- Use least privilege principle
- Keep your existing service account secure
- Consider rotating service account keys periodically

### Environment Variables
- Never commit service account keys to Git
- Use Slack CLI's environment variable system
- Validate environment configuration on startup

### Error Handling
- Implement proper error handling for authentication failures
- Log authentication events for monitoring
- Provide fallback mechanisms for critical operations

## 9. Troubleshooting

### Common Issues

**"Error: Domain-wide delegation not enabled"**
- Verify domain-wide delegation is enabled for the service account
- Check that the client ID is correctly configured in Google Admin Console

**"Error: Insufficient permissions"**
- Verify OAuth scopes are correctly configured in Admin Console
- Ensure the service account has necessary IAM roles

**"Error: Firebase project not found"**
- Verify the project ID in your existing service account credentials
- Ensure Firestore is enabled for your project (see Firebase Console)

**"Error: User not found for impersonation"**
- Verify the user email exists in your Google Workspace domain
- Check that domain-wide delegation includes the necessary scopes

**"Error: Invalid credentials"**
- Double-check your service account JSON is properly formatted
- Ensure credentials aren't missing quotes or have extra characters

### Debug Mode
Set `DENO_ENV=development` to enable verbose logging and error details.

## 10. Next Steps

1. **Test your setup**: Run `deno run --allow-net --allow-env --allow-read test_shared_auth.ts`
2. **Create your first bot function** using the example patterns
3. **Deploy when ready**: Both bots use the same credentials automatically
4. **Add more bots**: Use the `create_new_bot.ts` script

This simplified setup uses your existing service account to provide robust authentication for all your Slack apps without needing gcloud CLI or creating new credentials.