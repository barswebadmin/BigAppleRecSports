# Quick Start Guide - BARS Slack Apps

This guide gets your **shared** Firebase + Google API integrated Slack apps up and running quickly with **one set of credentials** for all bots.

## Prerequisites

- [Deno](https://deno.land/manual/getting_started/installation) installed
- [Slack CLI](https://api.slack.com/automation/cli/install) installed
- Google Workspace admin access for domain-wide delegation
- Firebase project (or Google Cloud project with Firebase enabled)

## 1. One-Time Setup (15 minutes)

Follow the detailed setup in [`SETUP_AUTHENTICATION.md`](./SETUP_AUTHENTICATION.md) to:
- Create service account with domain-wide delegation
- Configure Google Admin Console OAuth scopes
- Set up Firebase/Firestore
- Configure environment variables

## 2. Test Shared Authentication (2 minutes)

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

## 3. Start Development (1 minute)

### For Registrations Bot
```bash
cd slack-apps/registrations-bot
slack create registrations-app --template=blank
slack run
```

### For Marketing Bot
```bash
cd slack-apps/marketing-bot
slack create marketing-app --template=blank
slack run
```

## 4. Using the Shared Clients

**Two clear clients** provide access to all services **from any bot**:

```typescript
import { firebaseClient } from "@bars/firebase";       // For all Firestore operations
import { googleClient } from "@bars/google";           // For all Google API operations
import { getAdminUserEmail } from "@bars/shared/config/environment.ts";

// Same imports work in registrations-bot, marketing-bot, or any future bot
export default SlackFunction(YourFunction, async ({ inputs }) => {
  const adminEmail = getAdminUserEmail();

  // Firebase/Firestore operations
  await firebaseClient.addDoc("waitlists", {
    player_name: inputs.player_name,
    league_id: inputs.league_id,
    position: 1
  });

  // Google Sheets operations
  const sheets = await googleClient.sheets(adminEmail);
  const response = await sheets.spreadsheets.values.get({
    spreadsheetId: "your-spreadsheet-id",
    range: "Sheet1!A:Z"
  });
  const data = response.data.values || [];

  // Gmail operations
  const gmail = await googleClient.gmail("registrations@bigapplerecsports.com");
  const emailBody = [
    `To: player@example.com`,
    `Subject: Notification`,
    `Content-Type: text/plain; charset=utf-8`,
    '',
    `Body content`
  ].join('\n');

  await gmail.users.messages.send({
    userId: 'me',
    requestBody: {
      raw: btoa(emailBody).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
    }
  });

  return { outputs: { message: "Success!" } };
});
```

## 5. Project Structure (Shared Authentication)

```
slack-apps/
├── SETUP_AUTHENTICATION.md    # Detailed setup guide
├── QUICK_START.md             # This file
├── deno.json                  # Root config with shared imports
├── test_shared_auth.ts        # Test shared authentication
├── shared/                    # ⭐ Shared authentication for all bots
│   ├── auth/
│   │   ├── firebase_client.ts # Firebase Admin SDK implementation
│   │   └── google_auth.ts     # Google APIs with domain delegation
│   ├── config/
│   │   └── environment.ts     # Shared environment configuration
│   ├── firebase_client.ts     # Firebase client (exposed)
│   └── google_client.ts       # Google API client (exposed)
├── registrations-bot/
│   ├── deno.json              # Imports from @bars/shared/
│   ├── test_auth.ts           # Bot-specific test
│   └── functions/             # Slack functions
│       └── waitlist/
│           └── example_function.ts
└── marketing-bot/
    ├── deno.json              # Imports from @bars/shared/
    ├── test_auth.ts           # Bot-specific test
    └── functions/             # Slack functions
        └── campaigns/
            └── example_function.ts
```

## 6. Key Features

### Firebase Integration
- ✅ Firestore for persistent data storage
- ✅ Real-time data synchronization
- ✅ Scalable NoSQL database
- ✅ Built-in security rules

### Google APIs with Domain-Wide Delegation
- ✅ **Sheets API**: Read/write spreadsheet data
- ✅ **Drive API**: Access and manage files
- ✅ **Gmail API**: Send emails on behalf of domain users
- ✅ **Calendar API**: Schedule and manage events
- ✅ **No user authentication required**

### Deno + Slack Integration
- ✅ Modern TypeScript runtime
- ✅ Built-in permission system
- ✅ NPM package support for Firebase/Google APIs
- ✅ Slack Deno SDK integration

## 7. Common Use Cases

### Waitlist Management (Registrations Bot)
```typescript
// Add to waitlist in Firestore
await firebaseClient.addDoc("waitlists", waitlistEntry);

// Update Google Sheets for admin visibility
const sheets = await googleClient.sheets(adminEmail);
await sheets.spreadsheets.values.append({
  spreadsheetId,
  range: "Waitlist!A:C",
  valueInputOption: 'RAW',
  requestBody: {
    values: [[player_name, position, timestamp]]
  }
});

// Send confirmation email
const gmail = await googleClient.gmail("registrations@bigapplerecsports.com");
const emailBody = [
  `To: ${player_email}`,
  `Subject: Waitlist Confirmation`,
  `Content-Type: text/plain; charset=utf-8`,
  '',
  `You've been added to the waitlist...`
].join('\n');

await gmail.users.messages.send({
  userId: 'me',
  requestBody: {
    raw: btoa(emailBody).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
  }
});
```

### Campaign Management (Marketing Bot)
```typescript
// Store campaign in Firestore
await firebaseClient.addDoc("campaigns", campaignData);

// Create shared Drive folder for assets
const drive = await googleClient.drive(adminEmail);
await drive.files.create({
  requestBody: {
    name: `Campaign: ${campaign_name}`,
    mimeType: 'application/vnd.google-apps.folder'
  }
});
```

## 8. Development Tips

### Environment Variables
```bash
# Required
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS='{"type":"service_account",...}'
ADMIN_USER_EMAIL="admin@bigapplerecsports.com"
DEFAULT_USER_DOMAIN="bigapplerecsports.com"

# Optional
MASTER_SPREADSHEET_ID="your-google-sheets-id"
DENO_ENV="development"
```

### Error Handling
Always wrap API calls in try-catch blocks:
```typescript
try {
  const result = await firebaseClient.getDoc("collection", "docId");
  const sheets = await googleClient.sheets(userEmail);
} catch (error) {
  console.error("API call failed:", error);
  return { error: "Operation failed" };
}
```

### Testing
Run the authentication test after any configuration changes:
```bash
deno run --allow-net --allow-env --allow-read test_auth.ts
```

## 9. Troubleshooting

### "Domain-wide delegation not enabled"
- Check Google Admin Console > Security > API Controls > Domain-wide delegation
- Verify client ID and OAuth scopes are correct

### "Firebase project not found"
- Verify project ID in service account credentials
- Ensure Firebase is initialized: `firebase init firestore`

### "Insufficient permissions"
- Check service account has required OAuth scopes
- Verify user exists in Google Workspace domain

### Authentication test fails
- Double-check environment variables are set correctly
- Validate service account JSON is properly formatted
- Ensure all required APIs are enabled in Google Cloud Console

## 10. Benefits of Shared Authentication Setup

### 🔧 Single Configuration
- ✅ **One credential setup** for all bots (registrations, marketing, future bots)
- ✅ **Centralized management** - update credentials in one place
- ✅ **Consistent behavior** across all applications

### 🚀 Technical Advantages
- ✅ **No user authentication required** (domain-wide delegation)
- ✅ **Unified access** to Firebase + Google APIs from any bot
- ✅ **Cross-bot data sharing** via shared Firestore collections
- ✅ **Type-safe operations** with comprehensive error handling
- ✅ **Development and production ready** with environment validation

### 📈 Scalability & Maintenance
- ✅ **Easy bot expansion** - new bots just import `@bars/firebase` and `@bars/google`
- ✅ **Clear separation of concerns** - Firebase for data, Google for APIs
- ✅ **Shared authentication logic** - no code duplication
- ✅ **Firebase scalability** for data persistence
- ✅ **Google Workspace integration** with domain-wide delegation

The service account will impersonate any user in your domain for Google API operations, while all bots share the same Firebase project for data persistence and real-time updates.

## 11. Next Steps

1. ✅ Complete authentication setup
2. ✅ Run test script successfully
3. 🏗️ Implement your first Slack function using the example
4. 🚀 Deploy to production Slack workspace
5. 📊 Monitor usage and performance

For detailed implementation examples, see the `functions/waitlist/example_function.ts` file.

Need help? Check the full setup guide in `SETUP_AUTHENTICATION.md` or the troubleshooting section above.