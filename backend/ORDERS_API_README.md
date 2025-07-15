# BARS Orders API

This document describes the new `/orders` API endpoints that have been created to handle Shopify order operations, including refunds, cancellations, and inventory management.

## Overview

The Orders API provides a backend service that replaces the complex Google Apps Script logic for processing refunds and exchanges with a clean REST API interface. This allows for better error handling, testing, and maintenance.

## Architecture

### Files Created/Modified

1. **Backend Services**:
   - `backend/services/orders_service.py` - Core business logic for order operations
   - `backend/routers/orders.py` - FastAPI router with REST endpoints
   - `backend/utils/date_utils.py` - Enhanced with refund calculation functions

2. **Google Apps Scripts**:
   - `RawGsProjects/BARS - Process Refunds and Exchanges/processRefundWithBackend.gs` - Simplified script that calls the backend API

3. **Configuration**:
   - `backend/main.py` - Updated to include orders router

## API Endpoints

### GET /orders/{order_number}

Get detailed order information including refund calculations and inventory status.

**Parameters**:
- `order_number` (path) - The Shopify order number (with or without #)
- `email` (query, optional) - Email address for fallback lookup

**Response**:
```json
{
  "success": true,
  "data": {
    "order": {
      "orderId": "gid://shopify/Order/...",
      "orderName": "#1001",
      "orderCreatedAt": "2025-01-01T00:00:00Z",
      "totalAmountPaid": 150.00,
      "customer": {
        "id": "gid://shopify/Customer/...",
        "email": "customer@example.com"
      },
      "product": {
        "title": "Big Apple Dodgeball - Sunday Open - Big Ball Tournament - Summer 2025",
        "productId": "gid://shopify/Product/...",
        "variants": [...]
      }
    },
    "refund_calculation": {
      "success": true,
      "refund_amount": 142.50,
      "refund_text": "Estimated Refund Due: $142.50..."
    },
    "credit_calculation": {
      "success": true,
      "refund_amount": 150.00,
      "refund_text": "Estimated Refund Due: $150.00..."
    },
    "inventory_summary": {
      "success": true,
      "inventory_list": {
        "veteran": {...},
        "early": {...},
        "open": {...},
        "waitlist": {...}
      }
    },
    "product_urls": {
      "shopify_admin": "https://admin.shopify.com/store/09fe59-3/products/...",
      "order_admin": "https://admin.shopify.com/store/09fe59-3/orders/..."
    }
  }
}
```

### DELETE /orders/{order_number}

Cancel an order and process refund/store credit with optional inventory restocking.

**Parameters**:
- `order_number` (path) - The Shopify order number
- `refund_type` (query, default: "refund") - "refund" or "credit"
- `refund_amount` (query, optional) - Custom refund amount (calculated if not provided)
- `restock_inventory` (query, default: true) - Whether to restock inventory
- `email` (query, optional) - Email for fallback lookup

**Response**:
```json
{
  "success": true,
  "message": "Order #1001 has been canceled successfully",
  "data": {
    "order_id": "gid://shopify/Order/...",
    "order_number": "#1001",
    "cancellation": {...},
    "refund_amount": 142.50,
    "refund_type": "refund",
    "refund_result": {...},
    "restock_results": [...],
    "customer": {...},
    "product": {...}
  }
}
```

### POST /orders/{order_number}/refund

Create a refund or store credit without canceling the order.

**Parameters**:
- `order_number` (path) - The Shopify order number
- `refund_type` (query, default: "refund") - "refund" or "credit"
- `refund_amount` (query, optional) - Custom refund amount
- `email` (query, optional) - Email for fallback lookup

### POST /orders/{order_number}/restock

Restock inventory for an order's product variants.

**Parameters**:
- `order_number` (path) - The Shopify order number
- `variant_name` (query, optional) - Specific variant to restock
- `email` (query, optional) - Email for fallback lookup

## Slack Integration

The Orders API includes automatic Slack notifications to the `#refunds` channel when refunds are processed. This replicates the functionality from the original Google Apps Script.

### Slack Features

- **Refund Notifications**: Automatic messages when refunds/credits are processed
- **Rich Message Formatting**: Includes order details, inventory status, and season information
- **Sport-specific Mentions**: Automatically mentions relevant team groups (kickball, bowling, etc.)
- **Interactive Elements**: Message blocks with order and product links
- **Error Notifications**: Alerts for API errors and issues

### Slack Configuration

The Slack integration uses the following configuration (from the original Google Apps Script):
- **Channel**: `#refunds` (ID: `C08J1EN7SFR`)
- **Team Groups**: Kickball, Bowling, Pickleball, Dodgeball

### Message Format

When a refund is processed, Slack receives a message like:
```
✅ Request to provide a $142.50 refund for Order #1001 for customer@example.com has been processed by API User

📦 Season Start Date for Winter Basketball League is 2025-02-01.
Current Inventory:
• Veteran Registration: 5 spots available
• Open Registration: 12 spots available
• Waitlist Registration: 0 spots available
```

## Business Logic

### Refund Calculation

The system automatically calculates refund amounts based on:

1. **Season Start Date**: Extracted from product description HTML
2. **Off Dates**: Weeks when the league is not active
3. **Request Timing**: When the refund request was submitted
4. **Refund Type**: "refund" (with processing fees) vs "credit" (no fees)

**Refund Tiers**:
- **Refund**: 95%, 90%, 80%, 70%, 60%, 50% (based on timing)
- **Credit**: 100%, 95%, 85%, 75%, 65%, 55% (based on timing)

### Inventory Management

The system identifies and manages different registration types:
- **Veteran Registration**: Priority spots for returning players
- **Early Registration**: WTNB/Trans players
- **Open Registration**: General public
- **Waitlist Registration**: Coming off waitlist

### Error Handling

- Comprehensive error messages for debugging
- Graceful degradation (e.g., refund processed even if inventory restock fails)
- Detailed logging for troubleshooting

## Google Apps Script Integration

### Simplified Functions

The new `processRefundWithBackend.gs` provides simplified functions:

```javascript
// Get order details
const orderResult = getOrderDetails(orderNumber, email);

// Cancel order with refund
const refundResult = cancelOrderWithRefund(
  orderNumber, 
  'refund',    // or 'credit'
  null,        // auto-calculate amount
  true,        // restock inventory
  email
);

// Create refund only (no cancellation)
const refundResult = createRefundOnly(orderNumber, 'credit', 50.00);

// Restock inventory
const restockResult = restockInventory(orderNumber, 'open');

// Process complete refund request
const result = processRefundRequest(orderNumber, email, 'refund');
```

### Configuration

Update the `BACKEND_API_URL` in the Google Apps Script:
```javascript
const BACKEND_API_URL = 'https://your-deployed-backend.com'; // Update this
```

## Testing

### Local Testing

1. Start the backend server:
```bash
cd backend
python3 -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

2. Run the test script:
```bash
python3 test_orders_api.py
```

3. Test API endpoints:
```bash
# Get order details
curl -X GET "http://127.0.0.1:8000/orders/1001"

# Cancel order with refund
curl -X DELETE "http://127.0.0.1:8000/orders/1001?refund_type=credit&restock_inventory=true"
```

### Google Apps Script Testing

Use the `testBackendConnection()` function to verify connectivity:
```javascript
testBackendConnection(); // Check logs and email for results
```

## Deployment

1. **Backend Deployment**: Deploy to your preferred platform (Render, Heroku, etc.)
2. **Update Scripts**: Change `BACKEND_API_URL` in Google Apps Scripts
3. **Environment Variables**: Ensure Shopify credentials are set
4. **Testing**: Run end-to-end tests with real orders

## Migration from Original Scripts

### What's Replaced

The new API replaces the following complex Google Apps Script files:
- `approveRefundRequest.gs` → `DELETE /orders/{order_number}`
- `cancelRefundRequest.gs` → Order cancellation logic
- `updateRefundRequestOrderDetails.gs` → Order lookup and validation
- `getRefundDue.gs` → Refund calculation logic
- `restockInventory.gs` → `POST /orders/{order_number}/restock`
- `ShopifyUtils.gs` → `OrdersService` methods

### Benefits

1. **Centralized Logic**: All order processing logic in one place
2. **Better Error Handling**: Comprehensive error messages and logging
3. **Easier Testing**: Unit tests and API testing capabilities
4. **Maintainability**: Clean separation of concerns
5. **Scalability**: Can handle multiple concurrent requests
6. **Documentation**: Auto-generated API docs at `/docs`

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running from the project root
2. **Shopify Connection**: Verify credentials in `config.py`
3. **Order Not Found**: Check order number format (with/without #)
4. **Refund Calculation**: Verify product description contains season dates

### Logging

Check application logs for detailed error information:
```bash
# View recent logs
tail -f backend.log
```

### Support

For issues or questions:
1. Check the API documentation at `/docs`
2. Review error messages in logs
3. Test with the provided test scripts
4. Contact the development team

## Future Enhancements

Potential improvements:
1. **Webhook Integration**: Real-time order updates
2. **Batch Processing**: Handle multiple orders at once
3. **Email Notifications**: Automated customer communications
4. **Analytics**: Refund processing metrics
5. **Admin Interface**: Web UI for order management 