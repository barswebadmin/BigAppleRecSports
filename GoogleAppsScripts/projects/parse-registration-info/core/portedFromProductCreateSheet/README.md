# Ported Product Creation Logic

This directory contains product creation logic ported from the `product-variant-creation` project to enable direct Shopify product creation from `parse-registration-info`.

## Files

### `createShopifyProduct.gs`
- Main entry point for product creation flow
- Handles row data parsing and conversion to product format
- Shows confirmation dialog to user
- Coordinates the product creation process
- Writes results back to the spreadsheet

### `shopifyProductCreation.gs`
- Core Shopify API integration
- Creates main product with GraphQL
- Creates product variants (Vet, Early, Open, Waitlist)
- Handles variant option management
- Schedules inventory and price updates

## Flow

1. User selects "🛍️ Create Shopify Product" from menu
2. System scans rows for complete product data (columns A/B, C, D, E, F, G, H, M, O)
3. User selects a row number from available options
4. System parses row data using existing parse-registration-info logic
5. Confirmation dialog shows parsed data for review/editing
6. User confirms product creation
7. System creates Shopify product and variants via GraphQL API
8. Results written to columns Q (Product URL), R (Vet Variant), S (Early Variant), T (Open Variant), U (Waitlist Variant)

## Required Columns

- **A/B**: Day of Week / Type of Play (merged cells)
- **C**: League Details
- **D**: Season Start Date
- **E**: Season End Date
- **F**: Price
- **G**: League Play Time(s)
- **H**: Location (Field/Court/Lane)
- **M**: WTNB/BIPOC/TNB Register
- **O**: Open Register

## Output Columns

- **Q**: Product URL (hyperlink to Shopify admin)
- **R**: Vet Registration Variant ID
- **S**: Early Registration Variant ID
- **T**: Open Registration Variant ID
- **U**: Waitlist Registration Variant ID

## Dependencies

- Uses existing `parseSourceRowEnhanced_()` from core parser
- Requires Shopify secrets (SHOPIFY_GRAPHQL_URL, SHOPIFY_TOKEN)
- Uses shared utilities for text processing and validation
