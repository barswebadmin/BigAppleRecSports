# Changelog

All notable changes to the BARS backend will be documented in this file.

## [2.0.0] - 2025-07-15

### 🔧 Other Changes
- c426d9f Merge pull request #17 from barswebadmin/update-main-py-again
- 7dd1a06 Fix Slack webhook invalid_blocks error and add comprehensive test suite
- 0beb17c update Makefile for CI checks
- 345b19b Merge pull request #11 from barswebadmin/backend-production-ready
- c071343 Merge pull request #13 from barswebadmin/fix-render-yaml
- 4555b86 Fix double parentheses in refund calculation messages
- cf05b4f fix tests again to pass CI checks
- 50de248 Merge pull request #10 from barswebadmin/update-lambda-logic
- b04259f Merge pull request #12 from barswebadmin/backend-production-ready-2
- 6c7cd90 Merge pull request #15 from barswebadmin/test-auto-deploy

### 📁 Files Changed
- `backend/.env.example`
- `backend/Makefile`
- `backend/ORDERS_API_README.md`
- `backend/PRODUCTION_DEPLOYMENT.md`
- `backend/REFACTORING_SUMMARY.md`
- `backend/SLACK_TESTING_README.md`
- `backend/SLACK_WEBHOOK_TESTING.md`
- `backend/TESTING_GUIDE.md`
- `backend/config.py`
- `backend/env.example`
- ... and 37 more files



All notable changes to the BARS backend will be documented in this file.

## [1.0.3] - 2025-06-26

### 🐛 Bug Fixes
- resolve double prefix issue in leadership router

### 🔧 Other Changes
- demonstrate automatic version increment system
- 59552dc fix typo
- c5d8536 update main.py again
- 428b706 Merge pull request #16 from barswebadmin/fix-double-prefix

### 📁 Files Changed
- `backend/main.py`



All notable changes to the BARS backend will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2025-06-26

### ✨ Features
- Production-ready deployment configuration with Render
- Enhanced CORS policy for Google Apps Script integration
- Conditional API documentation (disabled in production)
- Environment-aware configuration management

### 🔧 Other Changes
- Added comprehensive security measures
- Improved monitoring endpoints with version information
- Enhanced development experience with hot reload

### 📁 Files Changed
- `backend/main.py`
- `backend/config.py`
- `render.yaml`
- `.github/workflows/backend-tests.yml`

## [1.0.1] - 2024-06-25

### ✨ Features
- CSV data processing with automatic email extraction
- Backend-generated display text for Google Apps Script
- Smart header detection and object-based processing
- Comprehensive error handling and validation

### 🔧 Other Changes
- Batch processing optimization (10x performance improvement)
- Enhanced API response format
- Improved logging and debugging capabilities

### 📁 Files Changed
- `backend/services/csv_service.py`
- `backend/services/leadership_service.py`
- `backend/routers/leadership.py`

## [1.0.0] - 2024-06-25

### ✨ Features
- Initial FastAPI backend implementation
- Leadership discount processing API
- Shopify GraphQL integration
- Customer tagging and segment creation
- Seasonal discount code generation

### 🔧 Other Changes
- RESTful API design with proper error handling
- Environment-based configuration
- Comprehensive test coverage
- Documentation and examples

### 📁 Files Changed
- `backend/main.py`
- `backend/services/shopify_service.py`
- `backend/services/leadership_service.py`
- `backend/routers/leadership.py`
- `backend/models/requests.py` 