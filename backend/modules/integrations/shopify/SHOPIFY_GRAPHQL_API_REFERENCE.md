# Shopify Admin GraphQL API Reference

**Generated**: 2025-01-27  
**Conversation ID**: `8e12bf80-b30c-420e-b005-2ae41653103e`  
**API Version**: Latest Shopify Admin GraphQL API

## Overview

This document provides a comprehensive reference for the Shopify Admin GraphQL API operations available for the BARS project. All GraphQL operations have been validated against the official Shopify schema.

## Authentication & Setup

### Conversation ID
**Important**: Use this conversation ID for all Shopify MCP server interactions:
```
8e12bf80-b30c-420e-b005-2ae41653103e
```

### Required Scopes
Different operations require specific API scopes:
- `read_products` / `write_products` - Product operations
- `read_orders` / `write_orders` - Order operations  
- `read_customers` / `write_customers` - Customer operations
- `read_inventory` / `write_inventory` - Inventory operations

## Core Operations

### Products

#### Queries
- **`product(id: ID!)`** - Get single product by ID
- **`products(first: Int, query: String)`** - List products with filtering
- **`productVariant(id: ID!)`** - Get single variant by ID
- **`productVariants(first: Int, query: String)`** - List variants with filtering
- **`productsCount(query: String)`** - Count products (max 10,000)

#### Mutations
- **`productCreate(product: ProductCreateInput)`** - Create new product
- **`productUpdate(product: ProductUpdateInput)`** - Update existing product
- **`productDelete(input: ProductDeleteInput!)`** - Delete product
- **`productSet(input: ProductSetInput!)`** - Bulk create/update products
- **`productDuplicate(productId: ID!, newTitle: String!)`** - Duplicate product

### Orders

#### Queries
- **`order(id: ID!)`** - Get single order by ID
- **`orders(first: Int, query: String, sortKey: OrderSortKeys)`** - List orders
- **`orderByIdentifier(identifier: OrderIdentifierInput!)`** - Get order by identifier
- **`ordersCount(query: String)`** - Count orders (max 10,000)
- **`draftOrder(id: ID!)`** - Get draft order
- **`draftOrders(first: Int, query: String)`** - List draft orders

#### Mutations
- **`orderCreate(order: OrderCreateOrderInput!)`** - Create new order
- **`orderUpdate(input: OrderInput!)`** - Update existing order
- **`orderCancel(orderId: ID!, reason: OrderCancelReason!)`** - Cancel order
- **`orderCapture(input: OrderCaptureInput!)`** - Capture payment
- **`orderMarkAsPaid(input: OrderMarkAsPaidInput!)`** - Mark order as paid
- **`orderOpen(input: OrderOpenInput!)`** - Reopen closed order
- **`orderClose(input: OrderCloseInput!)`** - Close open order

### Customers

#### Queries
- **`customer(id: ID!)`** - Get single customer by ID
- **`customers(first: Int, query: String, sortKey: CustomerSortKeys)`** - List customers
- **`customerByIdentifier(identifier: CustomerIdentifierInput!)`** - Get customer by identifier
- **`customersCount(query: String)`** - Count customers (max 10,000)

#### Mutations
- **`customerCreate(input: CustomerInput!)`** - Create new customer
- **`customerUpdate(input: CustomerInput!)`** - Update existing customer
- **`customerDelete(input: CustomerDeleteInput!)`** - Delete customer
- **`customerSet(input: CustomerSetInput!)`** - Bulk create/update customers
- **`customerMerge(customerOneId: ID!, customerTwoId: ID!)`** - Merge two customers

### Inventory

#### Mutations
- **`inventorySetQuantities(input: InventorySetQuantitiesInput!)`** - Set inventory quantities
- **`inventoryActivate(inventoryItemId: ID!, locationId: ID!)`** - Activate inventory at location
- **`inventoryDeactivate(inventoryLevelId: ID!)`** - Deactivate inventory at location
- **`inventoryMoveQuantities(input: InventoryMoveQuantitiesInput!)`** - Move inventory between locations

## Validated GraphQL Examples

### 1. Get Order by Order Number

**Use Case**: Look up order for refund processing

```graphql
query GetOrderByNumber($query: String!) {
  orders(first: 1, query: $query) {
    edges {
      node {
        id
        name
        email
        totalPrice
        processedAt
        customer {
          id
          email
          firstName
          lastName
        }
        lineItems(first: 10) {
          edges {
            node {
              id
              title
              quantity
              originalUnitPrice
              product {
                id
                title
              }
            }
          }
        }
      }
    }
  }
}
```

**Required Scopes**: `read_orders`, `read_marketplace_orders`, `read_customers`, `read_products`

**Variables Example**:
```json
{
  "query": "name:#42305"
}
```

### 2. Get Product Details

**Use Case**: Retrieve product information for inventory management

```graphql
query GetProductById($id: ID!) {
  product(id: $id) {
    id
    title
    description
    status
    totalInventory
    variants(first: 10) {
      edges {
        node {
          id
          title
          price
          inventoryQuantity
          availableForSale
        }
      }
    }
  }
}
```

**Required Scopes**: `read_products`

**Variables Example**:
```json
{
  "id": "gid://shopify/Product/1234567890"
}
```

### 3. Create Customer

**Use Case**: Add new customer to system

```graphql
mutation CreateCustomer($input: CustomerInput!) {
  customerCreate(input: $input) {
    customer {
      id
      email
      firstName
      lastName
      createdAt
    }
    userErrors {
      field
      message
    }
  }
}
```

**Required Scopes**: `write_customers`, `read_customers`

**Variables Example**:
```json
{
  "input": {
    "email": "customer@example.com",
    "firstName": "John",
    "lastName": "Doe"
  }
}
```

### 4. Update Inventory Quantities

**Use Case**: Set product inventory levels

```graphql
mutation SetInventoryQuantities($input: InventorySetQuantitiesInput!) {
  inventorySetQuantities(input: $input) {
    inventoryAdjustmentGroup {
      id
      reason
      referenceDocumentUri
    }
    userErrors {
      field
      message
    }
  }
}
```

**Required Scopes**: `write_inventory`, `read_inventory`

## Search Query Syntax

Shopify supports powerful search queries for filtering:

### Order Search Examples
- `name:#42305` - Find order by order number
- `email:customer@example.com` - Find orders by customer email
- `status:open` - Find open orders
- `created_at:>2024-01-01` - Orders created after date

### Product Search Examples
- `title:kickball` - Products with "kickball" in title
- `status:active` - Active products only
- `inventory_total:>0` - Products with inventory

### Customer Search Examples
- `email:customer@example.com` - Find customer by email
- `first_name:John` - Find customers by first name
- `orders_count:>5` - Customers with more than 5 orders

## Error Handling

All mutations return `userErrors` field for validation errors:

```graphql
{
  userErrors {
    field
    message
  }
}
```

Common error patterns:
- **Field validation**: Invalid input format
- **Permission errors**: Missing required scopes
- **Resource not found**: Invalid IDs
- **Rate limiting**: Too many requests

## Integration Points for BARS

### Refund Processing
- Use `order` query to fetch order details
- Use `orderCancel` mutation for order cancellation
- Use `orderCapture` mutation for payment processing

### Inventory Management
- Use `product` and `productVariants` queries for current inventory
- Use `inventorySetQuantities` mutation to update stock levels
- Use webhook handlers to sync inventory changes

### Customer Management
- Use `customerByIdentifier` to find customers by email
- Use `customerCreate` for new customer registration
- Use `customerUpdate` for profile updates

### Product Management
- Use `products` query for product listings
- Use `productUpdate` mutation for product modifications
- Use `productSet` mutation for bulk operations

## Best Practices

1. **Always validate GraphQL operations** using the MCP validation tool
2. **Use specific field selection** - only request needed data
3. **Implement proper error handling** for userErrors
4. **Respect rate limits** - implement exponential backoff
5. **Use pagination** for large result sets (first/after pattern)
6. **Cache frequently accessed data** to reduce API calls

## Related Files

- `backend/modules/integrations/shopify/builders/` - GraphQL query builders
- `backend/modules/integrations/shopify/models/` - Response models
- `backend/modules/orders/` - Order processing logic
- `backend/modules/products/` - Product management
- `backend/modules/refunds/` - Refund processing

## Documentation Links

- [Shopify Admin GraphQL API](https://shopify.dev/docs/api/admin-graphql)
- [GraphQL Query Syntax](https://shopify.dev/docs/api/usage/search-syntax)
- [Webhook Events](https://shopify.dev/docs/api/webhooks)
- [Rate Limits](https://shopify.dev/docs/api/usage/rate-limits)

---

**Note**: This reference was generated using the Shopify MCP server with conversation ID `8e12bf80-b30c-420e-b005-2ae41653103e`. All GraphQL operations have been validated against the official Shopify schema.
