# Security Policy

## Environment Variables

### Sensitive Data
The following environment variables contain sensitive information and should **NEVER** be committed to version control:

- `SHOPIFY_TOKEN` - Shopify Admin API access token

### Safe Defaults
These variables have safe defaults and can be committed:
- `SHOPIFY_STORE` - Store domain (publicly visible anyway)
- `ENVIRONMENT` - Application environment setting

## Development

1. Copy `backend/env.example` to `backend/.env`
2. Fill in your actual Shopify token
3. Never commit the `.env` file (it's in `.gitignore`)

## Production Deployment (Render)

1. Set `SHOPIFY_TOKEN` in Render dashboard environment variables
2. `ENVIRONMENT` is automatically set to `production`
3. `SHOPIFY_STORE` defaults to the correct store

## CI/CD (GitHub Actions)

Tests use mock/test tokens that don't access real Shopify data:
- `SHOPIFY_TOKEN=test_token`
- `ENVIRONMENT=test`

## Token Security Checklist

- [ ] Removed hardcoded tokens from all source files
- [ ] Added `.env` to `.gitignore`
- [ ] Created `env.example` with safe placeholder values
- [ ] Set real tokens only in production environment variables
- [ ] Verified no tokens appear in git history

## Reporting Security Issues

If you find security vulnerabilities, please report them privately to the maintainers. 