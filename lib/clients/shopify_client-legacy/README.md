# Shopify Client

Python client for Shopify Admin GraphQL API with typed queries and webhook processors.

## Overview

**Components:**
- `ShopifyClient` - Main GraphQL client with query execution
- Pre-built queries - Typed query builders for common operations
- Webhook processors - Parse and validate Shopify webhook payloads
- Schema management - Tools for fetching and filtering GraphQL schema

## Environment Setup

**Required:**
```bash
SHOPIFY__STORE_ID=09fe59-3
SHOPIFY__TOKEN__ADMIN=shpat_xxxxxxxxxxxxx
SHOPIFY__API_VERSION=2025-10
```

**Optional (for development/staging):**
```bash
SHOPIFY_DEV_STORE_ID=dev-store
SHOPIFY_DEV_TOKEN=shpat_xxxxxxxxxxxxx
```

## Quick Start

```python
from shared_utilities.clients.shopify_client import ShopifyClient, GetProduct

client = ShopifyClient()

# Execute pre-built query
product = client.execute(GetProduct(product_id="gid://shopify/Product/123"))

# Raw GraphQL
result = client.execute_raw("""
  query ($id: ID!) {
    product(id: $id) { title handle }
  }
""", {"id": "gid://shopify/Product/123"})
```

## GraphQL Schema Management

### Overview

The full Shopify GraphQL schema generates a **27,416-line Python file** with hundreds of unused types (blogs, abandoned checkouts, app development, etc.). Use filtered schema generation to reduce this by 80-90%.

### Fetching Schema

**Filtered (recommended):**
```bash
# Fetch filtered schema (default)
python scripts/shopify/fetch_shopify_gql_schema_filtered.py --env production

# Output: shared_utilities/clients/shopify_client/shopify_schema_filtered.json
```

**Full unfiltered:**
```bash
python scripts/shopify/fetch_shopify_gql_schema_filtered.py --env production --no-filter
```

**With explicit credentials:**
```bash
python scripts/shopify/fetch_shopify_gql_schema_filtered.py \
  --store my-store \
  --token shpat_xxxxx
```

**Custom filter:**
```bash
python scripts/shopify/fetch_shopify_gql_schema_filtered.py \
  --env production \
  --filter-config custom_filters.json \
  --output custom_schema.json
```

### Generating Python Types

```bash
# Generate typed Python code from schema
sgqlc-codegen schema \
  shared_utilities/clients/shopify_client/shopify_schema_filtered.json \
  shared_utilities/clients/shopify_client/shopify_schema_filtered.py

# Result: ~2,000-5,000 lines (vs 27,416 unfiltered)
```

### Customizing Filters

**Option 1: Edit config file (recommended)**

Edit `scripts/shopify/schema_filter_config.json`:
```json
{
  "exclude_types": [
    "Blog",
    "GiftCard",
    "Market",
    "AbandonedCheckout"
  ]
}
```

**Option 2: Edit script directly**

Modify `DEFAULT_EXCLUDE_TYPES` in `scripts/shopify/fetch_shopify_gql_schema_filtered.py`.

### Default Exclusions

**Excluded by default:**
- App development (AppInstallation, AppSubscription, WebhookSubscription)
- Blog/CMS (Blog, Article, Comment, Page)
- Gift cards (GiftCard, GiftCardTransaction)
- Markets & internationalization (Market, MarketLocalization)
- B2B (Company, CompanyLocation, CompanyContact)
- Shopify Functions (Function, ShopifyFunction, Validation)
- Disputes (ShopifyPaymentsDispute)
- Bulk operations (BulkOperation, BulkMutation)
- Themes (OnlineStoreTheme, ThemeFile)
- Subscriptions (SellingPlan, SubscriptionContract)
- Metaobjects (Metaobject, MetaobjectDefinition)
- Admin misc (Domain, ShopFeatures, ShopPlan, ScriptTag, Translation)

**Included automatically:**
- Orders, LineItems, Transactions, Refunds, FulfillmentOrders
- Products, ProductVariants, ProductImages, Collections, Inventory
- Customers, CustomerSegments, MailingAddress
- Discounts, DiscountCodes, AutomaticDiscounts, PriceRules
- Media, Images, Videos, Files
- Staff, ShopPolicies
- Money types (Money, MoneyV2, CurrencyCode)
- All dependencies of included types

### Workflow

**Initial setup:**
```bash
# 1. Fetch filtered schema
python scripts/shopify/fetch_shopify_gql_schema_filtered.py --env production

# 2. Generate Python types
sgqlc-codegen schema \
  shared_utilities/clients/shopify_client/shopify_schema_filtered.json \
  shared_utilities/clients/shopify_client/shopify_schema_filtered.py

# 3. Verify
wc -l shared_utilities/clients/shopify_client/shopify_schema_filtered.py
# Expected: ~2,000-5,000 lines
```

**Update schema (when Shopify API changes):**
```bash
# Re-run same commands
python scripts/shopify/fetch_shopify_gql_schema_filtered.py --env production
sgqlc-codegen schema shopify_schema_filtered.json shopify_schema_filtered.py
```

**Add new types:**
```bash
# 1. Edit filter config to include new patterns
vim scripts/shopify/schema_filter_config.json

# 2. Regenerate
python scripts/shopify/fetch_shopify_gql_schema_filtered.py --env production
sgqlc-codegen schema shopify_schema_filtered.json shopify_schema_filtered.py
```

### Troubleshooting

**"Type X not found" error:**
1. Check if type is in `exclude_types`
2. Remove from exclusions or add pattern to keep it
3. Regenerate schema

**Schema too large:**
1. Review what types you actually use in code
2. Add more patterns to `exclude_types`
3. Regenerate

**Schema too small:**
1. Add broader patterns (e.g., "Discount" includes all discount-related types)
2. Remove patterns from `exclude_types`
3. Dependencies are automatically included

## Client API Reference

### ShopifyClient

**Methods:**
- `execute(query)` - Execute pre-built typed query
- `execute_raw(query_string, variables)` - Execute raw GraphQL
- `search_customers_by_emails(emails)` - Batch customer search
- `batch_update_customer_tags(updates)` - Batch tag updates

**Pre-built Queries:**
- `GetProduct(product_id)` - Fetch product with variants, images, metafields
- `GetOrdersByProduct(product_id, limit)` - Orders for specific product
- `GetAllOrdersForExport(created_at_min, first, after)` - All orders with full line item details
- `GetCustomer(customer_id)` - Customer with addresses, orders
- `SearchCustomerByEmail(email)` - Find customer by email
- `UpdateCustomerTags(customer_id, tags)` - Update customer tags
- `UpdateProduct(product_id, input)` - Update product fields
- `GetInventoryInfo(location_id, product_ids)` - Inventory levels
- `AdjustInventory(inventory_item_id, location_id, delta)` - Adjust stock
- `AttachProductMedia(product_id, media)` - Add product images/videos
- `DeleteProductMedia(product_id, media_ids)` - Remove media
- `BulkUpdateVariantPrices(updates)` - Batch price updates

### Webhook Processors

```python
from shared_utilities.clients.shopify_client import (
    OrderCreateWebhook,
    ProductUpdateWebhook,
    process_order_create,
    process_product_update,
)

# Parse webhook payload
payload = request.json
order_data = process_order_create(payload)  # Returns OrderCreateResult
product_data = process_product_update(payload)  # Returns ProductUpdateResult
```

## Development Workflow

### Adding New Queries

1. Create query class in `queries/` directory
2. Implement `build()` method returning GraphQL string
3. Export from `queries/__init__.py`
4. Add to `__init__.py` exports

**Example:**
```python
class GetProductMetafields:
    def __init__(self, product_id: str):
        self.product_id = product_id
    
    def build(self) -> tuple[str, dict]:
        query = """
          query ($id: ID!) {
            product(id: $id) {
              metafields(first: 100) {
                edges { node { namespace key value } }
              }
            }
          }
        """
        return query, {"id": self.product_id}
```

### Updating Schema Types

When Shopify API version changes or you need new types:

```bash
# 1. Update API version in .env
SHOPIFY__API_VERSION=2025-10

# 2. Fetch new schema
python scripts/shopify/fetch_shopify_gql_schema_filtered.py --env production

# 3. Regenerate Python types
sgqlc-codegen schema shopify_schema_filtered.json shopify_schema_filtered.py

# 4. Update queries if breaking changes
# (Check Shopify's API changelog)
```

### Testing Queries

```python
# Use client directly for ad-hoc testing
from shared_utilities.clients.shopify_client import ShopifyClient

client = ShopifyClient()

result = client.execute_raw("""
  query {
    shop {
      name
      email
      currencyCode
    }
  }
""")

print(result)
```

## Standalone Scripts

### Export Sport Orders

Export all orders for sport products (dodgeball, kickball, bowling, pickleball) to CSV with flattened custom form fields.

```bash
# Export since March 15, 2025
uv run --project scripts scripts/shopify/export_sport_orders_to_csv.py --since 2025-03-15

# Custom output path
uv run --project scripts scripts/shopify/export_sport_orders_to_csv.py \
  --since 2025-03-15 \
  --output ~/Desktop/sport_orders.csv

# Limit for testing
uv run --project scripts scripts/shopify/export_sport_orders_to_csv.py --since 2025-03-15 --limit 100
```

**Output columns:**
- Base: order_id, order_name, customer_*, line_item_*, product_*, variant_*, price, discounts
- Custom: magical_form.* (ordered by priority: preferred first name, last name, DOB, email, phone, emergency contact, gender, pronouns, race/ethnicity, buddy fields, then alphabetical)

**Location:** `scripts/shopify/export_sport_orders_to_csv.py`

### Add Customer Tags with Veteran Emails

Tag Shopify customers and optionally send personalized veteran access emails.

```bash
# Standard BCC emails (existing)
uv run --project scripts scripts/shopify/add_tag_to_customers.py veterans.csv

# Personalized hash-based URLs (batched Gmail API)
uv run --project scripts scripts/shopify/add_tag_to_customers_with_hashing.py veterans.csv
```

**Location:** `scripts/shopify/add_tag_to_customers*.py`

## File Structure

```
shared_utilities/clients/shopify_client/
├── __init__.py                      # Package exports
├── README.md                        # This file
├── client.py                        # ShopifyClient core
├── gql.py                           # GraphQL utilities
├── product_image.py                 # Image helpers
├── shopify_url_builder.py          # URL construction
├── shopify_schema.json              # Full schema (reference)
├── shopify_schema.py                # Full schema types (reference)
├── shopify_schema_filtered.json    # Filtered schema (active)
├── shopify_schema_filtered.py      # Filtered schema types (active)
├── webhook_payloads.json            # Webhook payload examples
├── models/                          # Data models
│   ├── order_create.py             # Order webhook processor
│   └── product_update.py           # Product webhook processor
└── queries/                         # Pre-built queries
    ├── customers.py                # Customer queries
    ├── orders.py                   # Order queries
    ├── export_orders.py            # Export query with full details
    ├── products.py                 # Product queries
    └── inventory.py                # Inventory queries
```

## Notes

- **Schema size:** Filtered schema reduces Python file from ~27k to ~2-5k lines
- **Dependencies:** Automatically resolves and includes referenced types
- **Pattern matching:** Substring-based (e.g., "Order" matches OrderConnection, OrderEdge, etc.)
- **Backward compatible:** Existing code works with filtered schema as long as types are included
- **Re-fetch anytime:** Safe to regenerate schema when Shopify API updates
