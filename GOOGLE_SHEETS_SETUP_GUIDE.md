# Google Sheets API Setup Guide

## 🚀 **Quick Setup Steps**

### **Step 1: Google Cloud Console** (5 minutes)

1. **Go to Google Cloud Console:**
   - Visit: https://console.cloud.google.com/
   - Sign in with your BARS Google account

2. **Create or Select Project:**
   - If no project exists, click "Create Project"
   - Name: `BARS Backend Services`
   - Note your Project ID

3. **Enable Google Sheets API:**
   - Navigate to: https://console.cloud.google.com/apis/library
   - Search: "Google Sheets API"
   - Click **"Enable"**

4. **Create Service Account:**
   - Go to: https://console.cloud.google.com/iam-admin/serviceaccounts
   - Click **"Create Service Account"**
   - **Name:** `bars-backend-service`
   - **Description:** `Backend service for BARS leadership automation`
   - Click **"Create and Continue"**
   - **Skip** granting roles (not needed)
   - Click **"Done"**

5. **Create Service Account Key:**
   - Click on the service account you just created
   - Go to **"Keys"** tab
   - Click **"Add Key"** → **"Create New Key"**
   - Choose **"JSON"**
   - Click **"Create"**
   - **Download the JSON file** (you'll use this next)

---

### **Step 2: Store Credentials Locally** (2 minutes)

1. **Save the JSON file:**
   ```bash
   # Save it as:
   backend/google-service-account.json
   ```

2. **Add to .env:**
   ```bash
   # In backend/.env, add:
   GOOGLE_SERVICE_ACCOUNT_FILE=google-service-account.json
   ```

3. **Verify .gitignore:**
   - The file should already be ignored (contains `*.json` pattern)
   - Double-check it's NOT staged in git

---

### **Step 3: Share Your Google Sheet** (1 minute)

1. **Get Service Account Email:**
   - Open `backend/google-service-account.json`
   - Find the `client_email` field
   - It looks like: `bars-backend-service@PROJECT-ID.iam.gserviceaccount.com`

2. **Share the Sheet:**
   - Open your Leadership Google Sheet
   - Click **"Share"** button
   - Add the service account email
   - Set permission to **"Viewer"**
   - Click **"Send"** (uncheck "Notify people")

---

### **Step 4: Get Your Sheet ID** (1 minute)

Your Google Sheet URL looks like:
```
https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid=0
```

**Copy the SHEET_ID part** - you'll need this for testing.

Example:
- URL: `https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit`
- Sheet ID: `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms`

---

## ✅ **Verification**

After setup, test authentication:

```bash
cd backend
python -c "
from modules.integrations.google.sheets_client import GoogleSheetsClient
client = GoogleSheetsClient()
print('✅ Authentication successful!')
print(f'Service account: {client.service_account_email}')
"
```

---

## 🔒 **Security Checklist**

- [ ] JSON file is in `backend/` directory
- [ ] JSON file is in `.gitignore`
- [ ] JSON file is NOT committed to git
- [ ] Environment variable is in `.env`
- [ ] Google Sheet is shared with service account
- [ ] Service account has "Viewer" permission (not "Editor")

---

## 💰 **Cost Confirmation**

- ✅ **Service Account:** FREE
- ✅ **Google Sheets API:** FREE (100M reads/day quota)
- ✅ **Your Usage:** <0.01% of quota

**Total Monthly Cost:** $0.00

---

## 📚 **API Reference**

- [Google Sheets API Documentation](https://developers.google.com/sheets/api/guides/concepts)
- [Service Account Authentication](https://developers.google.com/identity/protocols/oauth2/service-account)
- [Python Client Library](https://github.com/googleapis/google-api-python-client)

