# Shopify API Calls Made by Verification Script

## Overview

The verification script (`verify-bars-scripts-migration.sh`) makes **minimal actual API calls**. Most commands are tested with `--help` flags which don't make API calls.

## Actual API Calls (With Test Data)

When run with:
```bash
./scripts/verify-bars-scripts-migration.sh \
  43261 \
  customer@example.com \
  123456789 \
  7452597878878 \
  stephen@bigapplerecsports.com \
  U03LZKQSHEU
```

### 1. Order Lookup (`shopify order get 43261`)

**GraphQL Query:**
```graphql
query FetchOrder($q: String!) {
  orders(first: 1, query: $q) {
    edges {
      node {
        id
        name
        email
        createdAt
        displayFinancialStatus
        displayFulfillmentStatus
        cancelledAt
        cancelReason
        totalPriceSet {
          shopMoney {
            amount
            currencyCode
          }
        }
        customer {
          id
          email
          firstName
          lastName
          displayName
        }
        lineItems(first: 5) {
          nodes {
            id
            title
            quantity
            originalUnitPriceSet {
              shopMoney {
                amount
                currencyCode
              }
            }
            product {
              id
              title
            }
            customAttributes {
              key
              value
            }
          }
        }
        transactions {
          id
          kind
          gateway
          status
          amountSet {
            shopMoney {
              amount
              currencyCode
            }
          }
        }
        refunds {
          createdAt
          staffMember {
            firstName
            lastName
          }
          totalRefundedSet {
            presentmentMoney {
              amount
              currencyCode
            }
            shopMoney {
              amount
              currencyCode
            }
          }
        }
      }
    }
  }
}
```

**Variables:**
```json
{
  "q": "name:#43261"
}
```

**HTTP Method:** `POST`  
**Endpoint:** `https://{shop}.myshopify.com/admin/api/{version}/graphql.json`  
**API Call:** `orders` query (read-only)

---

### 2. Customer Lookup (`shopify customer get customer@example.com`)

**GraphQL Query:**
```graphql
query FetchCustomer($q: String!) {
  customers(first: 1, query: $q) {
    edges {
      node {
        id
        email
        firstName
        lastName
        displayName
        phone
        tags
        addresses {
          id
          address1
          city
          province
          zip
          country
        }
        ordersCount
        orders(first: 5) {
          edges {
            node {
              id
              name
              createdAt
            }
          }
        }
      }
    }
  }
}
```

**Variables:**
```json
{
  "q": "email:customer@example.com"
}
```

**HTTP Method:** `POST`  
**Endpoint:** `https://{shop}.myshopify.com/admin/api/{version}/graphql.json`  
**API Call:** `customers` query (read-only)

---

### 3. Product Lookup (`shopify product get 7452597878878`)

**GraphQL Query:**
```graphql
query FetchProduct($id: ID!) {
  product(id: $id) {
    id
    title
    handle
    description
    vendor
    productType
    tags
    status
    variants(first: 5) {
      nodes {
        id
        title
        sku
        price
        inventoryQuantity
        inventoryItem {
          id
          tracked
        }
      }
    }
  }
}
```

**Variables:**
```json
{
  "id": "gid://shopify/Product/7452597878878"
}
```

**HTTP Method:** `POST`  
**Endpoint:** `https://{shop}.myshopify.com/admin/api/{version}/graphql.json`  
**API Call:** `product` query (read-only)

---

## Commands Tested with `--help` (No API Calls)

These commands are tested for existence only (using `--help` flag), so **NO API calls are made**:

1. ✅ `shopify order cancel --help` - No API call
2. ✅ `shopify order refund --help` - No API call
3. ✅ `shopify order cancel-and-refund --help` - No API call
4. ✅ `shopify product restock --help` - No API call
5. ✅ `shopify product orders --help` - No API call
6. ✅ `slack user update --help` - No API call (Slack API, not Shopify)
7. ✅ `slack channel get --help` - No API call (Slack API, not Shopify)
8. ✅ `slack group get --help` - No API call (Slack API, not Shopify)
9. ✅ `shopify page get --help` - No API call
10. ✅ `shopify page update-about --help` - No API call

---

## Summary

### Total API Calls Made:
- **3 GraphQL queries** (all read-only):
  1. `orders` query - Get order #43261
  2. `customers` query - Get customer by email
  3. `product` query - Get product by ID (if product ID provided)

### No Mutations:
- ❌ No `orderCancel` mutations
- ❌ No `refundCreate` mutations
- ❌ No `customerUpdate` mutations
- ❌ No inventory adjustments

### API Rate Limits:
- All queries are read-only (safer for rate limits)
- Only 3 queries total (well within Shopify's rate limits)
- No mutations = no risk of data changes

---

## If You Want to Test Mutations

To test actual mutations (cancel, refund, etc.), you would need to:

1. **Remove `--help` flags** from the script
2. **Add `--confirm` or `--dry-run` flags** to prevent accidental changes
3. **Use test orders** in development environment

**Example modification:**
```bash
# Instead of:
run_bars_cli "shopify order cancel" "--help"

# Use:
run_bars_cli "shopify order cancel" "$TEST_ORDER_NUMBER" "--dry-run"
```

**Warning:** Mutations will make actual changes to Shopify data. Always use `--dry-run` or test environment first!

---

## API Endpoints Used

All Shopify API calls go to:
```
POST https://{shop}.myshopify.com/admin/api/{version}/graphql.json
```

Where:
- `{shop}` = Your Shopify shop domain (from `.env`)
- `{version}` = API version (e.g., `2024-10`)

**Authentication:** Uses `SHOPIFY_TOKEN_ADMIN` from environment variables or AWS SSM Parameter Store.
