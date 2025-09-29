# all these responses have 200 response status code:

# { insufficient permissions} => FORBIDDEN

# (parse if `errors` is present and `data` is null, and errors[0].extensions.code = "ACCESS_DENIED")

# (return the list of errors, mapped/filtered to the `message` (string))
# {
#   "errors": [
#     {
#       "message": "Access denied for orders field.",
#       "locations": [
#         {
#           "line": 1,
#           "column": 9
#         }
#       ],
#       "path": [
#         "orders"
#       ],
#       "extensions": {
#         "code": "ACCESS_DENIED",
#         "documentation": "https://shopify.dev/api/usage/access-scopes"
#       }
#     }
#   ],
#   "data": null,
#   "extensions": {
#     "cost": {
#       "requestedQueryCost": 3,
#       "actualQueryCost": 2,
#       "throttleStatus": {
#         "maximumAvailable": 2000.0,
#         "currentlyAvailable": 1998,
#         "restoreRate": 100.0
#       }
#     }
#   }
# }





# {bad request syntax} => BAD_REQUEST

# (response contains only errors (list), return the list)

# {
#   "errors": [
#     {
#       "message": "syntax error, unexpected LPAREN (\"(\") at [2, 5]",
#       "locations": [
#         {
#           "line": 2,
#           "column": 5
#         }
#       ]
#     }
#   ]
# }


# { incorrect input in query/variables} => NOT_ACCEPTABLE

# (e.g. calling /orders with id:{gid})

# `data`` is present, but flattened object has no values in it

# `search` present at top level, has a `query`, return all els, mapped/filtered to include only `query` (string) and `warnings` (list, `field` and `message`)

# {
#   "data": {
#     "orders": {
#       "edges": []
#     }
#   },
#   "extensions": {
#     "cost": {
#       "requestedQueryCost": 8,
#       "actualQueryCost": 2,
#       "throttleStatus": {
#         "maximumAvailable": 2000.0,
#         "currentlyAvailable": 1998,
#         "restoreRate": 100.0
#       }
#     },
#     "search": [
#       {
#         "path": [
#           "orders"
#         ],
#         "query": "id:gid://shopify/Order/234234234",
#         "parsed": {
#           "and": [
#             {
#               "field": "default",
#               "match_all": "//shopify/Order/234234234"
#             },
#             {
#               "field": "id",
#               "match_all": "gid"
#             }
#           ]
#         },
#         "warnings": [
#           {
#             "field": "id",
#             "message": "Expected field to be a positive integer or UUID, received `gid`."
#           }
#         ]
#       }
#     ]
#   }
# }


# { incorrect input in return fields} => UNPROCESSABLE_ENTITY

# (if no `data` present, only `errors`, and `errors` is at least length 1, and at least 1 el has `extensions` with `code`, `typeName`, and `fieldName`)
# return the list of errors, mapped/filtered to the `message` (string), and `extensions` (dict)

# {
#   "errors": [
#     {
#       "message": "Field 'defaultEmail' doesn't exist on type 'Customer'",
#       "locations": [
#         {
#           "line": 8,
#           "column": 25
#         }
#       ],
#       "path": [
#         "query",
#         "orders",
#         "edges",
#         "node",
#         "customer",
#         "defaultEmail"
#       ],
#       "extensions": {
#         "code": "undefinedField",
#         "typeName": "Customer",
#         "fieldName": "defaultEmail"
#       }
#     }
#   ]
# }

# { multi status} => MULTI_STATUS
# (parse if `errors` is present and not empty,) but `data` is also present, and flattened object is not empty (it has values)

# (return the `data` and `errors`. have to consider checking `errors` against all the other error logic)


# ( no records found) => NO_CONTENT

# (parse if flattened `data` has no values (outside empty objects and empty lists))

# # success, but no record found

# Status Code: 200

# {
#   "data": {
#     "orders": {
#       "edges": []
#     }
#   },
#   "extensions": {
#     "cost": {
#       "requestedQueryCost": 8,
#       "actualQueryCost": 2,
#       "throttleStatus": {
#         "maximumAvailable": 2000.0,
#         "currentlyAvailable": 1998,
#         "restoreRate": 100.0
#       }
#     }
#   }
# }

# (success case) => OK

# `errors` not present, `data` has non-empty string values when flattened

# return `data`

# "data": {
#     "orders": {
#       "edges": [
#         {
#           "node": {
#             "id": "gid://shopify/Order/5890295201886",
#             "name": "#43262",
#             "email": "someEmail@gmail.com",
#             "customer": {
#               "id": "gid://shopify/Customer/8204287901790",
#               "defaultEmailAddress": {
#                 "emailAddress": "someEmail@gmail.com"
#               }
#             },
#             "createdAt": "2025-09-20T14:40:33Z",
#             "totalPriceSet": {
#               "shopMoney": {
#                 "amount": "145.0",
#                 "currencyCode": "USD"
#               }
#             },
#             "transactions": [
#               {
#                 "createdAt": "2025-09-20T14:40:28Z",
#                 "id": "gid://shopify/OrderTransaction/7560313339998",
#                 "kind": "SALE",
#                 "gateway": "shopify_payments",
#                 "parentTransaction": null
#               },
#               {
#                 "createdAt": "2025-09-24T01:00:36Z",
#                 "id": "gid://shopify/OrderTransaction/7567356264542",
#                 "kind": "REFUND",
#                 "gateway": "shopify_payments",
#                 "parentTransaction": {
#                   "id": "gid://shopify/OrderTransaction/7560313339998"
#                 }
#               }
#             ],
#             "refunds": [
#               {
#                 "createdAt": "2025-09-24T01:00:36Z",
#                 "staffMember": null,
#                 "totalRefundedSet": {
#                   "presentmentMoney": {
#                     "amount": "145.0",
#                     "currencyCode": "USD"
#                   },
#                   "shopMoney": {
#                     "amount": "145.0",
#                     "currencyCode": "USD"
#                   }
#                 }
#               }
#             ]
#           }
#         }
#       ]
#     }
#   },

from typing import Any, Dict, Optional
from backend.modules.integrations.shopify.models.responses import ShopifyResponse, ShopifyResponseKind


def _has_values(obj: Any) -> bool:
    """Check if object has non-empty values when flattened."""
    if isinstance(obj, dict):
        return any(_has_values(v) for v in obj.values())
    elif isinstance(obj, list):
        return any(_has_values(item) for item in obj)
    elif isinstance(obj, str):
        return len(obj) > 0
    elif obj is not None:
        return True
    return False


def parse_shopify_response(response_body: Dict[str, Any]) -> ShopifyResponse:
    """Parse Shopify GraphQL response and classify the result."""
    errors = response_body.get("errors")
    data = response_body.get("data")
    extensions = response_body.get("extensions", {})
    
    # FORBIDDEN: Access denied with specific error code
    if (errors and data is None and 
        any(e.get("extensions", {}).get("code") == "ACCESS_DENIED" for e in errors)):
        return ShopifyResponse.Error(
            kind=ShopifyResponseKind.FORBIDDEN,
            errors=str(errors)
        )
    
    # UNPROCESSABLE_ENTITY: Field errors with extensions (check first)
    if (errors and not data and 
        any("extensions" in e and "code" in e["extensions"] and 
            "typeName" in e["extensions"] and "fieldName" in e["extensions"] 
            for e in errors)):
        return ShopifyResponse.Error(
            kind=ShopifyResponseKind.UNPROCESSABLE_ENTITY,
            errors=str(errors)
        )
    
    # BAD_REQUEST: Syntax errors (only errors, no data)
    if errors and not data:
        return ShopifyResponse.Error(
            kind=ShopifyResponseKind.BAD_REQUEST,
            errors=str(errors)
        )
    
    # NOT_ACCEPTABLE: Search warnings with empty data
    if (data and not _has_values(data) and 
        "search" in extensions and 
        any("warnings" in s for s in extensions["search"])):
        return ShopifyResponse.Error(
            kind=ShopifyResponseKind.NOT_ACCEPTABLE,
            errors=f"Search warnings: {extensions['search']}"
        )
    
    # NO_CONTENT: Data present but no values
    if data and not _has_values(data):
        return ShopifyResponse.NoContent(data=data)
    
    # OK: Data present with values
    if data and _has_values(data):
        return ShopifyResponse.Success(data=data)
    
    return ShopifyResponse.Error(
        kind=ShopifyResponseKind.UNEXPECTED_ERROR,
        errors="Unable to classify response"
    )