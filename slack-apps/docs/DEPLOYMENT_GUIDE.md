# Deno Deployment Guide for Slack Integration Bots

## 🦕 Deno Apps (Not Slack CLI Apps)

**Important:** You're building **Deno applications** that integrate with Slack APIs, not using Slack's own hosting platform.

## 🚀 Deployment Options

### Option 1: Deno Deploy (Recommended for Production)

**Set credentials via Deno Deploy CLI:**
```bash
# Install deployctl if needed
deno install -A --global https://deno.land/x/deploy/deployctl.ts

# Set environment variables
deployctl env add --project=registrations-bot GOOGLE_SERVICE_ACCOUNT_CREDENTIALS '{"type":"service_account",...}'
deployctl env add --project=marketing-bot GOOGLE_SERVICE_ACCOUNT_CREDENTIALS '{"type":"service_account",...}'

# Deploy
deployctl deploy --project=registrations-bot registrations-bot/main.ts
deployctl deploy --project=marketing-bot marketing-bot/main.ts
```

### Option 2: Programmatic Setup (Development/Simple)

**In your main bot file:**
```typescript
// registrations-bot/main.ts or marketing-bot/main.ts

// Set up credentials if not already available (for local development)
if (!Deno.env.get("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS")) {
  Deno.env.set("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS", JSON.stringify({
    "type": "service_account",
    "project_id": "bars-backend-services",
    // ... rest of credentials
  }));
}

// Import Firebase client (will use environment variable automatically)
import { firebaseClient } from '../shared/firebase_client.ts';
```

### Option 3: Local .env File (Development)

**Use local .env with --env flag:**
```bash
# From slack-apps directory
deno run --env --allow-net --allow-env --cert=/usr/local/ca_certs/combined.pem registrations-bot/main.ts
```

## 📋 Deployment Commands

### Local Development
```bash
# Use .env file in slack-apps directory
deno run --env --allow-net --allow-env --cert=/usr/local/ca_certs/combined.pem main.ts

# Or set programmatically in code
deno run --allow-env --allow-net --cert=/usr/local/ca_certs/combined.pem main.ts
```

### Deno Deploy (Production)
```bash
# Deploy to Deno Deploy
deployctl deploy --project=your-project main.ts
```

### Other Deno Hosting Platforms
```bash
# Most Deno hosting platforms support environment variables
# Set GOOGLE_SERVICE_ACCOUNT_CREDENTIALS via their dashboard/CLI
```

## ✅ Current Setup Status

**Your Firebase client is already deployment-ready:**
- ✅ Automatically reads from `GOOGLE_SERVICE_ACCOUNT_CREDENTIALS` environment variable
- ✅ Works with Deno Deploy environment variables
- ✅ Works with local `.env` files using `--env` flag
- ✅ Works with programmatic `Deno.env.set()`
- ✅ No manual credential export needed

## 🎯 Recommended Workflow

1. **Development:** Use `--env` flag or programmatic setup
2. **Production:** Use Deno Deploy environment variables
3. **Deploy:** Use `deployctl deploy` or your chosen Deno hosting platform

**Your Deno Slack bots are ready to deploy! 🚀**