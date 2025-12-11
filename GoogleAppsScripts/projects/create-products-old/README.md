# Old Product Variant Creation Script

This directory contains the current version of the `product-variant-creation` Google Apps Script project, pulled from Google Apps Script using clasp.

## Script Details

- **Script ID**: `1ag91SToLXcAFBIbGY_WSze5gdVlBr9qqaJNwO6e9ie7qOXRAcBo607qK`
- **Script URL**: https://script.google.com/u/0/home/projects/1ag91SToLXcAFBIbGY_WSze5gdVlBr9qqaJNwO6e9ie7qOXRAcBo607qK/edit
- **Last Updated**: December 9, 2024 (pulled via `clasp pull`)
- **Originally From**: commit `ae52481e4027551b92f8290aba92d2e12dc6e31a` (Sep 8, 2025)

## Purpose

This script was used to:
- Create Shopify products for new sports seasons
- Set up registration variants (Veteran, Early, Open, Waitlist)
- Configure pricing, inventory, and scheduling
- Handle product images and sport-specific settings

## Key Features

- Could send requests to local backend (`https://chubby-grapes-trade.loca.lt/api/products`) or AWS backend
- Controlled by `API_DESTINATION` variable ('local' or AWS)
- Created products with full HTML descriptions
- Managed variants with different registration types and pricing

## Files

- `.clasp.json` - Google Apps Script configuration
- `appsscript.json` - Apps Script manifest
- `Create Product From Row.js` - Main product creation logic
- `Create Variants From Row.js` - Variant creation logic
- `Add Menu Buttons to UI.js` - Spreadsheet UI integration
- `Utils.js` - Utility functions
- `instructions.js` - User instructions
- `scheduleInventoryMoves.js` - Inventory scheduling
- `schedulePriceChanges.js` - Price change scheduling
- `createManualScheduledInventoryMoves.js` - Manual inventory moves
- `shared-utilities/` - Shared utility functions:
  - `apiUtils.js` - API request utilities
  - `dateUtils.js` - Date formatting and parsing
  - `secretsUtils.js` - Secrets management
  - `sheetUtils.js` - Spreadsheet manipulation (9.9K)
  - `ShopifyUtils.js` - Shopify GraphQL operations (26K)
  - `SlackUtils.js` - Slack messaging utilities (16K)

## Replacement

This functionality has been replaced by the current `create-products-from-registration-info` project.

