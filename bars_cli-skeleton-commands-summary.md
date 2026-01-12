# BARS CLI Skeleton Commands Summary

## Overview

Created skeleton commands for all missing bars-scripts functionality. All commands compile and are registered, but contain pseudocode for planned implementation.

---

## ✅ Enhanced Customer Get Command

**File:** `bars_cli/commands/shopify/customers/get_customer_cmd.py`

**Change:** Added `--enhance` flag to show birthday and pronouns from order properties.

**Implementation Status:**
- ✅ Flag added and registered
- ✅ Uses existing `process_customer_birthday()` and `process_customer_pronouns()` functions
- ✅ Displays enhanced info after standard customer details

**Usage:**
```bash
bars shopify customer get customer@example.com --enhance
```

**Backend:** Uses existing functions in `bars_cli/commands/shopify/_shared/customer_properties.py`

---

## 📝 Skeleton Commands Created

### 1. Cancel and Refund (`bars shopify order cancel-and-refund`)

**File:** `bars_cli/commands/shopify/orders/cancel_and_refund_cmd.py`

**Status:** ✅ Compiles, contains pseudocode

**Backend Service:**
- ✅ EXISTS: `shopify_service.cancel_order()` - Cancels order with options
- ✅ EXISTS: `shopify_service.create_refund()` - Creates refund (needs verification)
- ⚠️  NEEDS: Combined workflow logic (orchestration)

**CLI Responsibilities:**
- Orchestrate workflow: cancel → restock prompt → refund
- Display order info before cancellation
- Always prompt for restock (even if already cancelled)
- Prompt for refund amount and type
- Display progress and results

**Backend Responsibilities:**
- Execute `orderCancel` mutation
- Execute `refundCreate` mutation
- Handle error responses
- Return structured success/error responses

---

### 2. Product Orders (`bars shopify product orders`)

**File:** `bars_cli/commands/shopify/products/orders_cmd.py`

**Status:** ✅ Compiles, contains pseudocode

**Backend Service:**
- ❌ MISSING: `shopify_service.get_orders_by_product()` - Needs to be created
- ✅ EXISTS: `shopify_service.get_order_by_identifier()` - Can get individual orders
- ✅ EXISTS: GraphQL `orders` query with product filtering

**CLI Responsibilities:**
- Accept product identifier (ID or handle)
- Display list of orders containing the product
- Support pagination (if many orders)
- Support CSV export (`--csv`, `--csv-file` flags)
- Format order list with key details

**Backend Responsibilities:**
- Build GraphQL query: `orders(query: "product_id:123456789")`
- Handle pagination (cursor-based)
- Return list of order objects
- Support filtering/sorting options

---

### 3. Analyze Refunds (`bars shopify order analyze-refunds`)

**File:** `bars_cli/commands/shopify/orders/analyze_refunds_cmd.py`

**Status:** ✅ Compiles, contains pseudocode

**Backend Service:**
- ❌ MISSING: Refund analysis logic - Needs to be created
- ✅ EXISTS: `shared-utilities/discount_calculator.py` - Has discount calculation logic
- ✅ EXISTS: `bars-scripts/analyze_order_refunds.py` - Has reference implementation

**CLI Responsibilities:**
- Accept CSV file path
- Parse CSV and extract order data
- Display analysis results (refund amounts, eligibility)
- Support output formats (formatted table, JSON, CSV)
- Show calculation details for each order

**Backend Responsibilities:**
- Parse CSV file
- For each order:
  - Get order details (submission timestamp, amount, etc.)
  - Calculate refund amount based on season dates and discount rules
  - Determine refund eligibility
- Return structured analysis results
- **Note:** This is BARS domain logic (not Shopify API), may belong in separate service

---

### 4. Get Page (`bars shopify page get`)

**File:** `bars_cli/commands/shopify/pages/get_page_cmd.py`

**Status:** ✅ Compiles, contains pseudocode

**Backend Service:**
- ❌ MISSING: `shopify_service.get_page()` - Needs to be created
- ❌ MISSING: `shopify_service.get_theme_asset()` - Needs to be created
- ❌ MISSING: `shopify_service.list_theme_assets()` - Needs to be created
- ✅ EXISTS: Shopify Admin API supports pages and theme assets
- ✅ EXISTS: `bars-scripts/shopify_get_page.py` - Has reference implementation

**CLI Responsibilities:**
- Accept page handle or theme ID + asset path
- Support multiple output formats (text, JSON, HTML)
- List theme assets (`--list` flag)
- Extract leadership positions from About page (`--extract-positions` flag)
- Display formatted output

**Backend Responsibilities:**
- Build GraphQL/REST queries for:
  * `pages` query (by handle)
  * Theme assets query (by theme ID and asset key)
  * List all assets in theme
- Parse and return page/asset content
- Extract structured data (e.g., leadership positions from About page JSON)

---

### 5. Update About Page (`bars shopify page update-about`)

**File:** `bars_cli/commands/shopify/pages/update_about_cmd.py`

**Status:** ✅ Compiles, contains pseudocode

**Backend Service:**
- ❌ MISSING: `shopify_service.update_about_page()` - Needs to be created
- ❌ MISSING: `shopify_service.upload_theme_image()` - Needs to be created
- ✅ EXISTS: Shopify Admin API supports theme asset updates
- ✅ EXISTS: `bars-scripts/shopify_update_about_page.py` - Has reference implementation

**CLI Responsibilities:**
- Accept CSV file (`--bulk-update`) or single block ID (`--single-update`) or image folder (`--upload-and-update`)
- Display preview of changes (dry-run mode)
- Prompt for confirmation
- Show progress during updates
- Display results (success/failure for each update)

**Backend Responsibilities:**
- Parse CSV file (name -> image URL mappings)
- Fetch current About page template
- Find blocks by person name
- Update image URLs in blocks
- Upload images to Shopify (if `--upload-and-update`)
- Update theme asset via PUT request
- Return structured success/error responses

---

### 6. Compare CSV (`bars utils compare-csv`)

**File:** `bars_cli/commands/utils/compare_csv_cmd.py`

**Status:** ✅ Compiles, contains pseudocode

**Backend Service:**
- ❌ MISSING: CSV comparison logic - Needs to be created (or use existing library)
- ✅ EXISTS: `bars-scripts/compare_csv.py` - Has reference implementation
- ✅ EXISTS: Python `csv` module - Standard library for CSV parsing

**CLI Responsibilities:**
- Accept two CSV file paths
- Display comparison results (differences, matches)
- Support output formats (formatted table, JSON)
- Show summary statistics

**Backend Responsibilities:**
- Parse both CSV files
- Compare rows/columns
- Identify differences (added, removed, modified rows)
- Return structured comparison results
- **Note:** This is a general utility, not Shopify-specific

---

## Command Registration

All commands are registered in:
- `bars_cli/commands/shopify/__init__.py` - Shopify commands
- `bars_cli/commands/utils/__init__.py` - Utility commands
- `bars_cli/main.py` - Main CLI entry point

---

## Next Steps

1. **Implement backend service methods:**
   - `get_orders_by_product()` in ShopifyService
   - `get_page()`, `get_theme_asset()`, `list_theme_assets()` in ShopifyService
   - `update_about_page()`, `upload_theme_image()` in ShopifyService
   - Refund analysis logic (may be separate service)

2. **Implement CLI logic:**
   - Replace pseudocode with actual implementation
   - Add error handling
   - Add progress indicators
   - Add confirmation prompts

3. **Test each command:**
   - Verify with real data
   - Compare output with bars-scripts equivalents
   - Ensure feature parity

---

## Files Created/Modified

### Modified:
- `bars_cli/commands/shopify/customers/get_customer_cmd.py` - Added `--enhance` flag
- `bars_cli/commands/shopify/__init__.py` - Registered new commands
- `bars_cli/main.py` - Registered utils group

### Created:
- `bars_cli/commands/shopify/orders/cancel_and_refund_cmd.py`
- `bars_cli/commands/shopify/orders/analyze_refunds_cmd.py`
- `bars_cli/commands/shopify/products/orders_cmd.py`
- `bars_cli/commands/shopify/pages/__init__.py`
- `bars_cli/commands/shopify/pages/get_page_cmd.py`
- `bars_cli/commands/shopify/pages/update_about_cmd.py`
- `bars_cli/commands/utils/__init__.py`
- `bars_cli/commands/utils/compare_csv_cmd.py`

---

## Verification

All files compile successfully:
```bash
python3 -m py_compile bars_cli/commands/shopify/orders/cancel_and_refund_cmd.py
python3 -m py_compile bars_cli/commands/shopify/orders/analyze_refunds_cmd.py
python3 -m py_compile bars_cli/commands/shopify/products/orders_cmd.py
python3 -m py_compile bars_cli/commands/shopify/pages/get_page_cmd.py
python3 -m py_compile bars_cli/commands/shopify/pages/update_about_cmd.py
python3 -m py_compile bars_cli/commands/utils/compare_csv_cmd.py
```

✅ All commands are ready for implementation.
