# Shopify Schema Filtering Guide

## Problem

The full Shopify GraphQL schema generates a **27,416-line Python file** with hundreds of types you'll never use (blogs, abandoned checkouts, app development, etc.).

## Solution

Use **filtered schema generation** to include only the types you need.

## Quick Start

### 1. Fetch Filtered Schema

```bash
# Fetch only the types you need (configured in schema_filter_config.json)
python scripts/shopify/fetch_schema_filtered.py --env production

# Output: shopify_schema_filtered.json (much smaller!)
```

### 2. Generate Python Types

```bash
# Generate Python code from filtered schema
sgqlc-codegen schema shopify_schema_filtered.json shopify_schema.py

# Result: Much smaller shopify_schema.py file!
```

### 3. Compare Results

```bash
# Before filtering
wc -l shopify_schema.py
# 27416 lines

# After filtering
wc -l shopify_schema.py
# ~2000-5000 lines (depending on your config)
```

## Customization

### Option 1: Edit Configuration File (Recommended)

Edit `scripts/shopify/schema_filter_config.json`:

```json
{
  "keep_type_patterns": [
    "Order",        // Keeps Order, OrderConnection, OrderEdge, etc.
    "Product",      // Keeps Product, ProductVariant, ProductImage, etc.
    "Customer",     // Keeps Customer, CustomerSegment, etc.
    "Discount",     // Keeps Discount, DiscountCode, etc.
    "Refund",       // Keeps Refund, RefundLineItem, etc.
    "Media"         // Keeps Media, MediaImage, etc.
  ],
  
  "exclude_types": [
    "Blog",         // Excludes Blog, BlogPost, etc.
    "GiftCard",     // Excludes GiftCard types
    "Market"        // Excludes Market/internationalization types
  ]
}
```

### Option 2: Edit Script Directly

Edit `scripts/shopify/fetch_schema_filtered.py` and modify:

```python
KEEP_TYPE_PATTERNS = {
    'Order', 'Product', 'Customer',  # Add/remove patterns here
}

EXCLUDE_TYPES = {
    'Blog', 'GiftCard', 'Market',    # Add/remove exclusions here
}
```

## What Gets Included?

### Automatic Dependency Resolution

The script automatically includes:
- ✅ Types you explicitly keep
- ✅ All types referenced by kept types (fields, arguments, interfaces)
- ✅ Built-in GraphQL types (`__Schema`, `__Type`, etc.)

### Pattern Matching

Pattern matching is **substring-based**:
- `"Order"` matches: `Order`, `OrderConnection`, `OrderEdge`, `OrderCancelReason`, etc.
- `"Product"` matches: `Product`, `ProductVariant`, `ProductImage`, `ProductStatus`, etc.

## Current Configuration

Based on your use cases (orders, products, customers, discounts, refunds, media), the default config includes:

### Core Types (Always Included)
- **Orders**: Order, LineItem, Transaction, Refund, FulfillmentOrder, DraftOrder
- **Products**: Product, ProductVariant, ProductImage, ProductMedia, Collection, Inventory
- **Customers**: Customer, CustomerSegment, CustomerPaymentMethod, MailingAddress
- **Discounts**: Discount, DiscountCode, AutomaticDiscount, PriceRule
- **Media**: Media, Image, Video, File, GenericFile
- **Staff**: StaffMember, ShopPolicy
- **Money**: Money, MoneyV2, MoneyBag, CurrencyCode
- **Locations**: Location

### Excluded Types (Never Included)
- **App Development**: App, AppInstallation, AppSubscription, WebhookSubscription
- **Abandoned Checkouts**: AbandonedCheckout, Abandonment
- **Blog/CMS**: Blog, Article, Comment, Page
- **Gift Cards**: GiftCard, GiftCardTransaction
- **Markets**: Market, MarketLocalization, CompanyLocation
- **Shopify Functions**: Function, ShopifyFunction
- **Disputes**: ShopifyPaymentsDispute
- **Bulk Operations**: BulkOperation, BulkMutation
- **Themes**: OnlineStoreTheme, ShopLocale
- **Misc**: Domain, ShopFeatures, ShopPlan, SavedSearch, ScriptTag

## Workflow

### Initial Setup (One Time)

```bash
# 1. Customize what you want
vim scripts/shopify/schema_filter_config.json

# 2. Fetch filtered schema
python scripts/shopify/fetch_schema_filtered.py --env production

# 3. Generate Python types
sgqlc-codegen schema shopify_schema_filtered.json shopify_schema.py

# 4. Commit the new, smaller schema
git add shopify_schema.py shopify_schema_filtered.json
git commit -m "Switch to filtered Shopify schema"
```

### Updating Schema (When Shopify API Changes)

```bash
# Just re-run the same commands
python scripts/shopify/fetch_schema_filtered.py --env production
sgqlc-codegen schema shopify_schema_filtered.json shopify_schema.py
```

### Adding New Types (When You Need More)

```bash
# 1. Edit config to add new patterns
vim scripts/shopify/schema_filter_config.json
# Add "SellingPlan" to keep_type_patterns

# 2. Regenerate
python scripts/shopify/fetch_schema_filtered.py --env production
sgqlc-codegen schema shopify_schema_filtered.json shopify_schema.py
```

## Benefits

### Before Filtering
- ❌ 27,416 lines
- ❌ Hundreds of unused types
- ❌ Slow IDE autocomplete
- ❌ Hard to find what you need
- ❌ Large git diffs

### After Filtering
- ✅ ~2,000-5,000 lines (80-90% reduction)
- ✅ Only types you use
- ✅ Fast IDE autocomplete
- ✅ Easy to navigate
- ✅ Smaller git diffs

## Troubleshooting

### "Type X not found" Error

If you get an error about a missing type:

1. Check if it's excluded in `exclude_types`
2. Add the type pattern to `keep_type_patterns`
3. Regenerate the schema

Example:
```json
{
  "keep_type_patterns": [
    "SellingPlan"  // Add this if you need subscription types
  ]
}
```

### Schema Too Large

If the filtered schema is still too large:

1. Review `keep_type_patterns` - remove patterns you don't need
2. Add more patterns to `exclude_types`
3. Check the output - it shows how many types were kept

### Schema Too Small

If you're missing types you need:

1. Add broader patterns to `keep_type_patterns`
2. Remove patterns from `exclude_types`
3. Remember: dependencies are automatically included

## Advanced Usage

### Generate Multiple Schemas

```bash
# Core schema (orders, products, customers only)
python scripts/shopify/fetch_schema_filtered.py \
  --env production \
  --output shopify_schema_core.json

# Extended schema (add marketing, analytics)
python scripts/shopify/fetch_schema_filtered.py \
  --env production \
  --output shopify_schema_extended.json
```

### Compare Schemas

```bash
# See what's different between full and filtered
diff <(jq '.data.__schema.types[].name' shopify_schema.json | sort) \
     <(jq '.__schema.types[].name' shopify_schema_filtered.json | sort)
```

### Analyze Type Usage

```bash
# See which types are actually used in your code
grep -r "from shopify_schema import" backend/ bars_cli/ | \
  sed 's/.*import //' | \
  tr ',' '\n' | \
  sort | uniq -c | sort -rn
```

## Next Steps

1. **Review the default config** in `schema_filter_config.json`
2. **Customize for your needs** - add/remove patterns
3. **Generate filtered schema** - run the script
4. **Test your code** - make sure nothing breaks
5. **Commit the changes** - enjoy the smaller schema!

## Questions?

- **"Should I keep the full schema?"** - No, but you can regenerate it anytime with `fetch_schema.py`
- **"Will this break my code?"** - No, as long as you include the types you use
- **"Can I add types later?"** - Yes, just edit the config and regenerate
- **"How often should I update?"** - When Shopify releases new API versions or you need new types
