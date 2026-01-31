# Backend Deployment Guide

## Render Deployment

### Files
- `render.yaml` (repository root) - Single source of truth for Render deployment

**Important:** 
- `render.yaml` must be at the repository root (Render requirement)
- Backend depends on `shared_utilities/` from the monorepo
- Render deploys the entire repository but sets `rootDir: backend`

### Automatic Deployment (Infrastructure as Code)

1. **Connect Repository to Render:**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Render automatically detects `render.yaml` at the repository root

2. **Render will automatically:**
   - Detect the `render.yaml` configuration at repository root
   - Install shared_utilities and dependencies
   - Start the service with `uvicorn main:app`
   - Set environment variables

### Manual Deployment

1. **Create Web Service:**
   - Go to Render Dashboard
   - Click "New +" → "Web Service"
   - Connect repository
   - Set root directory: `backend`
   - Build command: `pip install -e ../shared_utilities && pip install -r requirements.txt`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

2. **Environment Variables:**
   Set these in Render dashboard:
   ```
   ENVIRONMENT=production
   GOOGLE.SERVICE_ACCOUNT.PRIVATE_KEY=-----BEGIN PRIVATE KEY-----...
   SHOPIFY.TOKEN.ADMIN=shpat_...
   SLACK.DEV_BOT.TOKEN=xoxb-...
   # ... all other secrets from .config.toml
   ```

### Configuration

**render.yaml (at repository root):**
```yaml
services:
  - type: web
    name: bars-backend
    env: python
    rootDir: backend
    buildCommand: pip install -e ../shared_utilities && pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: RENDER
        value: "true"
      - key: ENVIRONMENT
        value: "production"
```

**Key points:**
- `render.yaml` must be at repository root (Render requirement)
- `rootDir: backend` - Render runs commands from the backend directory
- `buildCommand` installs shared_utilities and dependencies inline
- Render clones the entire monorepo, so `../shared_utilities` is accessible during build

### Environment Variables

Render injects environment variables at runtime. Your `config.py` automatically loads them:

```python
from config.config import config

# Works automatically on Render
config.google.service_account.private_key
config.shopify.token.admin
```

### Syncing Secrets

**Option 1: Manual (Render Dashboard)**
- Copy values from `.config.toml`
- Paste into Render environment variables

**Option 2: Automated (AWS Parameter Store → Render)**
Create a script to sync:
```python
# Fetch from AWS Parameter Store
params = ssm.describe_parameters()

# Push to Render API
for param in params:
    render_api.update_env_var(
        service_id='srv-xxx',
        key=param['Name'].upper(),
        value=param['Value']
    )
```

### Health Check

Render automatically checks: `https://your-app.onrender.com/health`

Your FastAPI app should have:
```python
@app.get("/health")
async def health():
    return {"status": "healthy"}
```

### Logs

View logs in Render Dashboard or via CLI:
```bash
render logs -s bars-backend
```

### Deployment Workflow

1. **Push to GitHub:**
   ```bash
   git push origin main
   ```

2. **Render auto-deploys:**
   - Detects changes
   - Runs build command
   - Restarts service
   - Zero-downtime deployment

### Troubleshooting

**Build fails:**
- Check `requirements.txt` is in `backend/`
- Verify Python version (3.11+)
- Check build logs in Render dashboard

**Service won't start:**
- Check start command uses `$PORT` variable
- Verify environment variables are set
- Check application logs

**Import errors from shared_utilities:**
- Render clones the entire monorepo, so `../shared_utilities` should be accessible
- Verify `pip install -e ../shared_utilities` runs in build command
- Check that `shared_utilities/pyproject.toml` exists
- If still failing, check Render build logs for the exact error

**How shared_utilities works on Render:**
1. Render clones your entire GitHub repository
2. Sets working directory to `backend/` (via `rootDir: backend`)
3. Runs build command: `pip install -e ../shared_utilities` installs from parent directory
4. Backend can now import: `from shared_utilities.api_clients.http_client import AsyncHTTPClient`
5. No `sys.path.append()` needed!

### Local Testing (Production-like)

Test deployment setup locally:
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Start with production settings
ENVIRONMENT=production uvicorn main:app --host 0.0.0.0 --port 8000
```

### Rollback

If deployment fails, Render keeps previous version running. Rollback via:
- Render Dashboard → Deployments → Rollback
- Or redeploy previous commit

## Summary

- ✅ `render.yaml` at repository root (single source of truth)
- ✅ `requirements.txt` for dependencies
- ✅ Environment variables set in Render dashboard
- ✅ Auto-deploy on git push
- ✅ Zero-downtime deployments
