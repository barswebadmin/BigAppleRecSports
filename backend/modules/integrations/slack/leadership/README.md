# Leadership Slack Bot - User ID Lookup

## Overview

The Leadership Slack bot provides a `/get-user-ids` slash command that allows users to paste CSV data and look up Slack user IDs from email addresses.

## Features

### Method 1: Slash Command (Manual Paste)
- **Slash Command:** `/get-user-ids` opens a modal
- **Modal Input:** Paste CSV content and select email column
- **Column Selection:** Choose which column contains emails (defaults to Column F)
- **Ephemeral Response:** Results posted only to the user who ran the command

### Method 2: File Upload (Auto-Detect)
- **Upload CSV:** Upload a CSV file containing "contact sheet" in the filename to `#joe-test`
- **Auto-Detection:** Bot automatically detects "Position" and "BARS Email" columns
- **Confirmation:** Ephemeral prompt asks if you want to process
- **Smart Parsing:** Finds header row automatically based on column presence

### Common Features
- **Concurrent Lookup:** Efficiently processes multiple emails in parallel
- **Private Results:** All responses are ephemeral (only you can see them)

## Slack App Configuration

### Prerequisites

Your Slack app must have these OAuth scopes:
- `commands` - For slash commands
- `users:read` - For user lookups
- `users:read.email` - For email-based lookups
- `files:read` - For reading uploaded CSV files
- `chat:write` - For posting messages

### Configuration Steps

1. **Go to Slack App Settings**
   - Visit: `https://api.slack.com/apps/<YOUR_APP_ID>`
   - Replace `<YOUR_APP_ID>` with your Leadership app ID

2. **Create Slash Command**
   - Navigate to: **Slash Commands** → **Create New Command**
   - **Command:** `/get-user-ids`
   - **Request URL:** `https://your-render-url.onrender.com/slack/leadership/commands`
   - **Short Description:** "Get Slack user IDs from CSV emails"
   - **Usage Hint:** (leave blank)
   - Click **Save**

3. **Enable Interactivity**
   - Navigate to: **Interactivity & Shortcuts**
   - Toggle **On**
   - **Request URL:** `https://your-render-url.onrender.com/slack/leadership/interactions`
   - Click **Save Changes**

4. **Enable Event Subscriptions** (for file upload feature)
   - Navigate to: **Event Subscriptions**
   - Toggle **On**
   - **Request URL:** `https://your-render-url.onrender.com/slack/leadership/interactions`
   - Under **Subscribe to bot events**, add:
     - `file_shared` - When a file is shared in a channel
   - Click **Save Changes**

5. **Reinstall App (if needed)**
   - If you added new scopes or made major changes
   - Navigate to: **Install App**
   - Click **Reinstall to Workspace**

## Environment Variables

Ensure these are set in your `.env` file:

```bash
SLACK_BOT_TOKEN_LEADERSHIP=xoxb-...
SLACK_SIGNING_SECRET_LEADERSHIP=...
```

## Usage

### Method 1: Slash Command (Manual CSV Paste)

1. In any Slack channel, type: `/get-user-ids`
2. A modal will open with:
   - **CSV Input:** Paste your CSV content
   - **Column Selector:** Choose which column has emails (default: Column F)
3. Click **Look Up**
4. Results will be posted ephemerally (only you can see them)

### Method 2: File Upload (Auto-Detect)

1. Go to `#joe-test` channel
2. Upload a CSV file with "contact sheet" in the filename (e.g., `2026 Leadership Contact Sheet.csv`)
3. An ephemeral message will appear showing:
   - Auto-detected Position and BARS Email columns
   - Total rows
   - Header row location
4. Click **Yes, Get User IDs**
5. Results will be posted ephemerally

### Example Results

```
✅ Found 63 users:
joe@bigapplerecsports.com → U0278M72535
chase@bigapplerecsports.com → U03MYT4D1FY
...

❌ Not found (2):
notfound@bigapplerecsports.com
inactive@bigapplerecsports.com

Total processed: 65 email(s)
```

## Architecture

```
User types: /get-user-ids
    ↓
POST /slack/leadership/commands
    ↓
handlers.py: Opens modal
    ↓
User submits CSV
    ↓
POST /slack/leadership/interactions
    ↓
handlers.py: Modal submission
    ↓
CSVProcessor.extract_column_values()
    ↓
UserLookupService.lookup_user_ids_by_emails()
    ↓
users_client.lookup_by_email() (concurrent)
    ↓
Post ephemeral results
```

## Files

- `bolt_app.py` - Bolt app initialization
- `handlers.py` - Command and modal handlers
- `../services/user_lookup_service.py` - User lookup logic
- `../client/users_client.py` - Slack API client
- `../../../../shared/csv/csv_processor.py` - CSV parsing utilities

## Testing

After deployment:

1. Test the slash command: `/get-user-ids`
2. Verify modal opens correctly
3. Paste sample CSV data
4. Verify user IDs are returned correctly
5. Test with invalid emails to ensure error handling works

## Troubleshooting

### Modal doesn't open
- Check that Request URL in Slack app settings is correct
- Verify bot token is valid
- Check logs for errors

### User lookups fail
- Verify `users:read.email` scope is enabled
- Check that emails exist in your Slack workspace
- Ensure bot token has workspace-wide access

### "Not found" for valid emails
- Email addresses must exactly match Slack profile emails
- User must be in the same workspace as the bot

