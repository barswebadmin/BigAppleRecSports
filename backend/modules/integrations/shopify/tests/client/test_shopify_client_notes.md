{wrong_store_id} => NOT_FOUND
{wrong api version} => NOT_FOUND

(response status 404,response contains only errors (string), return errors)

{
  "errors": "Not Found"
}


{bad token} => UNAUTHORIZED

(response status 401,response contains only errors (string), return errors)

{
  "errors": "[API] Invalid API key or access token (unrecognized login or wrong password)"
}


all the others have 200 response status code:

{ insufficient permissions} => FORBIDDEN

(parse if `errors` is present and `data` is null, and errors[0].extensions.code = "ACCESS_DENIED")

(return the list of errors, mapped/filtered to the `message` (string))
{
  "errors": [
    {
      "message": "Access denied for orders field.",
      "locations": [
        {
          "line": 1,
          "column": 9
        }
      ],
      "path": [
        "orders"
      ],
      "extensions": {
        "code": "ACCESS_DENIED",
        "documentation": "https://shopify.dev/api/usage/access-scopes"
      }
    }
  ],
  "data": null,
  "extensions": {
    "cost": {
      "requestedQueryCost": 3,
      "actualQueryCost": 2,
      "throttleStatus": {
        "maximumAvailable": 2000.0,
        "currentlyAvailable": 1998,
        "restoreRate": 100.0
      }
    }
  }
}





{bad request syntax} => BAD_REQUEST

(response contains only errors (list), return the list)

{
  "errors": [
    {
      "message": "syntax error, unexpected LPAREN (\"(\") at [2, 5]",
      "locations": [
        {
          "line": 2,
          "column": 5
        }
      ]
    }
  ]
}


{ incorrect input in query/variables} => NOT_ACCEPTABLE

(e.g. calling /orders with id:{gid})

`data`` is present, but flattened object has no values in it

`search` present at top level, has a `query`, return all els, mapped/filtered to include only `query` (string) and `warnings` (list, `field` and `message`)

{
  "data": {
    "orders": {
      "edges": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 8,
      "actualQueryCost": 2,
      "throttleStatus": {
        "maximumAvailable": 2000.0,
        "currentlyAvailable": 1998,
        "restoreRate": 100.0
      }
    },
    "search": [
      {
        "path": [
          "orders"
        ],
        "query": "id:gid://shopify/Order/234234234",
        "parsed": {
          "and": [
            {
              "field": "default",
              "match_all": "//shopify/Order/234234234"
            },
            {
              "field": "id",
              "match_all": "gid"
            }
          ]
        },
        "warnings": [
          {
            "field": "id",
            "message": "Expected field to be a positive integer or UUID, received `gid`."
          }
        ]
      }
    ]
  }
}


{ incorrect input in return fields} => UNPROCESSABLE_ENTITY

(if no `data` present, only `errors`, and `errors` is at least length 1, and at least 1 el has `extensions` with `code`, `typeName`, and `fieldName`)
return the list of errors, mapped/filtered to the `message` (string), and `extensions` (dict)

{
  "errors": [
    {
      "message": "Field 'defaultEmail' doesn't exist on type 'Customer'",
      "locations": [
        {
          "line": 8,
          "column": 25
        }
      ],
      "path": [
        "query",
        "orders",
        "edges",
        "node",
        "customer",
        "defaultEmail"
      ],
      "extensions": {
        "code": "undefinedField",
        "typeName": "Customer",
        "fieldName": "defaultEmail"
      }
    }
  ]
}

{ multi status} => MULTI_STATUS
(parse if `errors` is present and not empty,) but `data` is also present, and flattened object is not empty (it has values)

(return the `data` and `errors`. have to consider checking `errors` against all the other error logic)


( no records found) => NO_CONTENT

(parse if flattened `data` has no values (outside empty objects and empty lists))

# success, but no record found

Status Code: 200

{
  "data": {
    "orders": {
      "edges": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 8,
      "actualQueryCost": 2,
      "throttleStatus": {
        "maximumAvailable": 2000.0,
        "currentlyAvailable": 1998,
        "restoreRate": 100.0
      }
    }
  }
}

(success case) => OK

`errors` not present, `data` has non-empty string values when flattened

return `data`

"data": {
    "orders": {
      "edges": [
        {
          "node": {
            "id": "gid://shopify/Order/5890295201886",
            "name": "#43262",
            "email": "elisegubskaya17@gmail.com",
            "customer": {
              "id": "gid://shopify/Customer/8204287901790",
              "defaultEmailAddress": {
                "emailAddress": "elisegubskaya17@gmail.com"
              }
            },
            "createdAt": "2025-09-20T14:40:33Z",
            "totalPriceSet": {
              "shopMoney": {
                "amount": "145.0",
                "currencyCode": "USD"
              }
            },
            "transactions": [
              {
                "createdAt": "2025-09-20T14:40:28Z",
                "id": "gid://shopify/OrderTransaction/7560313339998",
                "kind": "SALE",
                "gateway": "shopify_payments",
                "parentTransaction": null
              },
              {
                "createdAt": "2025-09-24T01:00:36Z",
                "id": "gid://shopify/OrderTransaction/7567356264542",
                "kind": "REFUND",
                "gateway": "shopify_payments",
                "parentTransaction": {
                  "id": "gid://shopify/OrderTransaction/7560313339998"
                }
              }
            ],
            "refunds": [
              {
                "createdAt": "2025-09-24T01:00:36Z",
                "staffMember": null,
                "totalRefundedSet": {
                  "presentmentMoney": {
                    "amount": "145.0",
                    "currencyCode": "USD"
                  },
                  "shopMoney": {
                    "amount": "145.0",
                    "currencyCode": "USD"
                  }
                }
              }
            ]
          }
        }
      ]
    }
  },