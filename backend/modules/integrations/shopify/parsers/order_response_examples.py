"""
Shopify Order Response Examples

Reference documentation showing example JSON responses for different order states
and how to access the fields needed for frontend display.

This file serves as documentation only and is not executed.

# =============================================================================
# LONG-TERM MIGRATION NOTES (codegen client + thin routes)
# =============================================================================
#
# KEEP / MIGRATE TO modules/orders/ (domain), NOT integrations/:
#
# 1. Identifier parsing — 5-digit order number vs 11–16-digit order ID → GraphQL
#    query string (`name:#12345` vs `id:…`). Today duplicated in:
#    - ShopifyOrderIdentifierRequest.parse() (requests.py)
#    - ShopifyAPIController._parse_order_identifier()
#    Target: one function e.g. order_search_query(identifier: str) -> str
#
# 2. Display / presenter logic (from OrderResponse @validator in api_models.py):
#    - order number (strip # from name)
#    - admin URLs (orders/products) — NOT in GraphQL; use config + gid digits
#    - form_email from line_items[0].custom_attributes (key contains "email")
#    - cancellation_status / refund_status formatted strings (see scenarios below)
#    Target: present_order_for_refund_form(order: Order) -> dict | Pydantic DTO
#    Do NOT keep SuccessResponse envelope or dict validators.
#
# 3. Refund eligibility business rules — stay in modules/refunds/, not GraphQL models.
#
# 4. These scenario dicts — keep as fixtures until presenter has tests; then optional.
#
# DELETE WITH LEGACY STACK (no long-term home):
# - SuccessResponse / OrderResponse / api_models.py envelope tree
# - ShopifyAPIController + shopify_api routers
# - integrations/shopify/models/requests.py (after #1 migrated)
# - parse_shopify_response / ShopifyResponse (already deleted)
#
# NEW STACK (lib.clients.shopify generated Order):
# - Routes: response_model=Order | OrderCancel; errors via core/api_errors
# - Service: shopify.orders_get / order_cancel; raise or ApiFailure, never None
#
# =============================================================================
# FIELD MAP: examples below vs generated Order fragment (order.graphql)
# =============================================================================
#
# COVERED by codegen Order (snake_case in Python) — same shape for every orders query:
#   id, name, email, created_at, cancelled_at, cancel_reason
#   total_price_set.shop_money.amount, total_refunded_set.shop_money.amount
#   total_discounts_set.shop_money.amount
#   line_items.nodes[].title, custom_attributes, variant, product.id/title
#   transactions[] (id, kind, status, gateway, parent_transaction)
#   refunds[].id, note, created_at, total_refunded_set.shop_money.amount
#   refunds[].transactions.nodes[].gateway, kind, status, created_at, amount_set
#
# GAP — money field naming:
#   Examples: totalPriceSet.presentmentMoney, totalRefundedSet.presentmentMoney
#   Fragment: shopMoney only. For single-currency USD shop often identical;
#   use presentmentMoney if GAS must match historical display exactly.
#
# IN FRAGMENT but NOT in examples / GAS display guide (kept for one Order shape):
#   phone, updated_at, note, tags, total_discounts_set
#   order.transactions[] (refund UI uses refund.transactions; unused fields OK)
#
# INTENTIONALLY NOT on Order fragment (fetch elsewhere):
#   customer { email } — use customers_get / customer_update; scenarios use order.email
#   product.description_html — use products_get / product_update
#   display_financial_status, subtotal_price_set, total_tax_set — dropped
#   line_items.quantity, line_items.product.handle — dropped
#   order.custom_attributes — line-item customAttributes only
#
# ADD only if a consumer needs them — do not bloat default Order fragment.
# =============================================================================
"""

# =============================================================================
# SCENARIO 1: NOT CANCELED / NOT REFUNDED
# =============================================================================

NOT_CANCELED_NOT_REFUNDED = {
    "id": "gid://shopify/Order/6069195636830",
    "name": "#45308",
    "email": "tortoretejacoba@att.net",
    "createdAt": "2026-01-09T23:15:37Z",
    "cancelledAt": None,
    "cancelReason": None,
    "totalPriceSet": {
        "presentmentMoney": {
            "amount": "115.0",
            "currencyCode": "USD"
        }
    },
    "refunds": [],
    "lineItems": {
        "nodes": [
            {
                "id": "gid://shopify/LineItem/14478841282654",
                "title": "Big Apple Kickball - Saturday - Open Division - Winter 2026",
                "customAttributes": [
                    {
                        "key": "Best Contact Email Address",
                        "value": "tortoretejacoba@att.net"
                    }
                ],
                "product": {
                    "id": "gid://shopify/Product/7543133765726",
                    "title": "Big Apple Kickball - Saturday - Open Division - Winter 2026"
                }
            }
        ]
    }
}

# Field Access Paths:
# - Order Number: data['name'] -> strip '#' -> "45308"
# - Order ID: data['id'] -> extract digits -> "6069195636830"
# - Order URL: build_shopify_admin_url('orders', data['id'])
# - Product Title: data['lineItems']['nodes'][0]['product']['title']
# - Product ID: data['lineItems']['nodes'][0]['product']['id']
# - Product URL: build_shopify_admin_url('products', product_id)
# - Form Email: find in data['lineItems']['nodes'][0]['customAttributes'] where key contains 'email'
# - Amount Paid: data['totalPriceSet']['presentmentMoney']['amount']
# - Cancellation Status: "N/A" (cancelledAt is None)
# - Refund Status: "N/A (Not Refunded)" (refunds is empty list)


# =============================================================================
# SCENARIO 2: CANCELED / NOT REFUNDED
# =============================================================================

CANCELED_NOT_REFUNDED = {
    "id": "gid://shopify/Order/5886679941214",
    "name": "#43065",
    "email": "craigallan@hotmail.com",
    "createdAt": "2025-09-17T23:02:01Z",
    "cancelledAt": "2025-09-24T01:03:37Z",
    "cancelReason": "CUSTOMER",
    "totalPriceSet": {
        "presentmentMoney": {
            "amount": "0.0",
            "currencyCode": "USD"
        }
    },
    "refunds": [
        {
            "id": "gid://shopify/Refund/947621822558",
            "createdAt": "2025-09-24T01:03:36Z",
            "note": "Order canceled",
            "totalRefundedSet": {
                "presentmentMoney": {
                    "amount": "0.0",
                    "currencyCode": "USD"
                }
            },
            "transactions": {
                "nodes": []
            }
        }
    ],
    "lineItems": {
        "nodes": [
            {
                "id": "gid://shopify/LineItem/14120950464606",
                "title": "Big Apple Pickleball - Tuesday - Open Division - Fall 2025",
                "customAttributes": [
                    {
                        "key": "Best Contact Email Address",
                        "value": "craigallan@hotmail.com"
                    }
                ],
                "product": {
                    "id": "gid://shopify/Product/7458523021406",
                    "title": "Big Apple Pickleball - Tuesday - Open Division - Fall 2025"
                }
            }
        ]
    }
}

# Field Access Paths:
# - Cancellation Status: f"Canceled at {data['cancelledAt']} ({data['cancelReason']})"
# - Refund Status: "N/A (Canceled but not refunded)"
#   Logic: cancelledAt is not None AND refunds[0]['totalRefundedSet']['presentmentMoney']['amount'] == "0.0"


# =============================================================================
# SCENARIO 3: NOT CANCELED / REFUNDED
# =============================================================================

NOT_CANCELED_REFUNDED = {
    "id": "gid://shopify/Order/5876430798942",
    "name": "#42309",
    "email": "jdazz87@gmail.com",
    "createdAt": "2025-09-10T08:00:53Z",
    "cancelledAt": None,
    "cancelReason": None,
    "totalPriceSet": {
        "presentmentMoney": {
            "amount": "2.0",
            "currencyCode": "USD"
        }
    },
    "refunds": [
        {
            "id": "gid://shopify/Refund/946748260446",
            "createdAt": "2025-09-12T11:49:08Z",
            "note": "Refund issued via Slack workflow for $1.20",
            "totalRefundedSet": {
                "presentmentMoney": {
                    "amount": "1.2",
                    "currencyCode": "USD"
                }
            },
            "transactions": {
                "nodes": [
                    {
                        "id": "gid://shopify/OrderTransaction/7543226466398",
                        "gateway": "shopify_payments",
                        "amount": "1.20",
                        "createdAt": "2025-09-12T11:49:08Z",
                        "kind": "REFUND",
                        "status": "SUCCESS"
                    }
                ]
            }
        }
    ],
    "lineItems": {
        "nodes": [
            {
                "id": "gid://shopify/LineItem/14101799829598",
                "title": "joe test product - dodgeball",
                "customAttributes": [],
                "product": {
                    "id": "gid://shopify/Product/7350462185566",
                    "title": "joe test product - dodgeball"
                }
            }
        ]
    }
}

# Field Access Paths:
# - Cancellation Status: "N/A" (cancelledAt is None)
# - Refund Status: Format each refund as:
#   f"${refund['totalRefundedSet']['presentmentMoney']['amount']} refunded to "
#   f"{refund['transactions']['nodes'][0]['gateway']} at {refund['createdAt']} "
#   f"({refund['note']})"
# - Form Email: "Not Collected in form" (customAttributes is empty list)


# =============================================================================
# SCENARIO 4: CANCELED / REFUNDED
# =============================================================================

CANCELED_REFUNDED = {
    "id": "gid://shopify/Order/5885000000000",
    "name": "#43000",
    "email": "customer@example.com",
    "createdAt": "2025-09-15T10:00:00Z",
    "cancelledAt": "2025-09-20T15:30:00Z",
    "cancelReason": "FRAUD",
    "totalPriceSet": {
        "presentmentMoney": {
            "amount": "150.0",
            "currencyCode": "USD"
        }
    },
    "refunds": [
        {
            "id": "gid://shopify/Refund/947000000000",
            "createdAt": "2025-09-20T15:30:05Z",
            "note": "Full refund due to fraudulent order",
            "totalRefundedSet": {
                "presentmentMoney": {
                    "amount": "150.0",
                    "currencyCode": "USD"
                }
            },
            "transactions": {
                "nodes": [
                    {
                        "id": "gid://shopify/OrderTransaction/7543000000000",
                        "gateway": "shopify_payments",
                        "amount": "150.00",
                        "createdAt": "2025-09-20T15:30:05Z",
                        "kind": "REFUND",
                        "status": "SUCCESS"
                    }
                ]
            }
        }
    ],
    "lineItems": {
        "nodes": [
            {
                "id": "gid://shopify/LineItem/14100000000000",
                "title": "Big Apple Dodgeball - Monday - Open Division - Fall 2025",
                "customAttributes": [
                    {
                        "key": "Preferred First Name",
                        "value": "John"
                    },
                    {
                        "key": "Best Contact Email Address",
                        "value": "customer@example.com"
                    }
                ],
                "product": {
                    "id": "gid://shopify/Product/7450000000000",
                    "title": "Big Apple Dodgeball - Monday - Open Division - Fall 2025"
                }
            }
        ]
    }
}

# Field Access Paths:
# - Cancellation Status: f"Canceled at {data['cancelledAt']} ({data['cancelReason']})"
#   Result: "Canceled at 2025-09-20T15:30:00Z (FRAUD)"
# - Refund Status: Format refund (amount > 0):
#   f"${refund['totalRefundedSet']['presentmentMoney']['amount']} refunded to "
#   f"{refund['transactions']['nodes'][0]['gateway']} at {refund['createdAt']} "
#   f"({refund['note']})"
#   Result: "$150.0 refunded to shopify_payments at 2025-09-20T15:30:05Z (Full refund due to fraudulent order)"


# =============================================================================
# MULTIPLE REFUNDS EXAMPLE
# =============================================================================

MULTIPLE_REFUNDS = {
    "id": "gid://shopify/Order/5890000000000",
    "name": "#43500",
    "email": "multi@example.com",
    "createdAt": "2025-10-01T12:00:00Z",
    "cancelledAt": None,
    "cancelReason": None,
    "totalPriceSet": {
        "presentmentMoney": {
            "amount": "200.0",
            "currencyCode": "USD"
        }
    },
    "refunds": [
        {
            "id": "gid://shopify/Refund/948000000001",
            "createdAt": "2025-10-05T10:00:00Z",
            "note": "Partial refund - customer request",
            "totalRefundedSet": {
                "presentmentMoney": {
                    "amount": "50.0",
                    "currencyCode": "USD"
                }
            },
            "transactions": {
                "nodes": [
                    {
                        "gateway": "shopify_payments",
                        "amount": "50.00"
                    }
                ]
            }
        },
        {
            "id": "gid://shopify/Refund/948000000002",
            "createdAt": "2025-10-10T14:30:00Z",
            "note": "Additional refund - service issue",
            "totalRefundedSet": {
                "presentmentMoney": {
                    "amount": "75.0",
                    "currencyCode": "USD"
                }
            },
            "transactions": {
                "nodes": [
                    {
                        "gateway": "shopify_payments",
                        "amount": "75.00"
                    }
                ]
            }
        }
    ],
    "lineItems": {
        "nodes": [
            {
                "id": "gid://shopify/LineItem/14200000000000",
                "title": "Big Apple Kickball - Thursday - WTNB Division - Fall 2025",
                "customAttributes": [
                    {
                        "key": "Best Contact Email Address",
                        "value": "multi@example.com"
                    }
                ],
                "product": {
                    "id": "gid://shopify/Product/7550000000000",
                    "title": "Big Apple Kickball - Thursday - WTNB Division - Fall 2025"
                }
            }
        ]
    }
}

# Field Access Paths:
# - Refund Status: Format with bullet points for multiple refunds:
#   "\n- " + "\n- ".join([format_refund(r) for r in refunds])
#   Result:
#   "- $50.0 refunded to shopify_payments at 2025-10-05T10:00:00Z (Partial refund - customer request)
#    - $75.0 refunded to shopify_payments at 2025-10-10T14:30:00Z (Additional refund - service issue)"


# =============================================================================
# FIELD EXTRACTION SUMMARY
# =============================================================================

FIELD_EXTRACTION_GUIDE = """
Frontend Display Field Extraction Guide
========================================

1. ORDER NUMBER (without #)
   Path: data['name']
   Transform: Strip leading '#'
   Example: "#45308" -> "45308"

2. ORDER URL
   Path: data['id']
   Transform: build_shopify_admin_url('orders', extract_shopify_id(data['id']))
   Example: "gid://shopify/Order/6069195636830" -> 
            "https://admin.shopify.com/store/09fe59-3/orders/6069195636830"

3. PRODUCT TITLE
   Path: data['lineItems']['nodes'][0]['product']['title']
   Fallback: "N/A"

4. PRODUCT URL
   Path: data['lineItems']['nodes'][0]['product']['id']
   Transform: build_shopify_admin_url('products', extract_shopify_id(product_id))

5. ORDER EMAIL (from form)
   Path: data['lineItems']['nodes'][0]['customAttributes']
   Logic: Find dict where key.lower() contains 'email', return value
   Fallback: "Not Collected in form"

6. AMOUNT PAID
   Path: data['totalPriceSet']['presentmentMoney']['amount']
   Display: f"${amount}"
   Example: "115.0" -> "$115.0"

7. CREATED AT
   Path: data['createdAt']
   Display: As-is (ISO format)

8. CANCELLATION STATUS
   Logic:
   - If data['cancelledAt'] is None: "N/A"
   - Else: f"Canceled at {data['cancelledAt']} ({data['cancelReason']})"

9. REFUND STATUS
   Logic:
   - If data['refunds'] is empty: "N/A (Not Refunded)"
   - If data['cancelledAt'] is not None AND all refund amounts are 0: 
     "N/A (Canceled but not refunded)"
   - Else: Format each refund as:
     f"${refund['totalRefundedSet']['presentmentMoney']['amount']} refunded to "
     f"{refund['transactions']['nodes'][0]['gateway']} at {refund['createdAt']} "
     f"({refund['note']})"
   - If multiple refunds: Prefix each with "- " on new lines

10. CUSTOMER EMAIL (from order)
    Path: data['customer']['email']
    Note: This is different from form email (customAttributes)
"""
