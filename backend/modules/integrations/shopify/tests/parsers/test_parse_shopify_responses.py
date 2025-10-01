import json
import pytest

from ..models.responses import ShopifyResponseKind, ShopifyResponse
from ..parsers.parse_shopify_response import parse_shopify_response


def test_parse_shopify_responses_table_driven(capfd):
    cases = [
        {
            "error_type": "ACCESS_DENIED for orders field",
            "body": {
                "errors": [
                    {
                        "message": "Access denied for orders field.",
                        "locations": [{"line": 1, "column": 9}],
                        "path": ["orders"],
                        "extensions": {"code": "ACCESS_DENIED", "documentation": "https://shopify.dev/api/usage/access-scopes"},
                    }
                ],
                "data": None,
            },
            "expected": ShopifyResponseKind.FORBIDDEN,
        },
        {
            "error_type": "Bad request syntax",
            "body": {
                "errors": [
                    {
                        "message": "syntax error, unexpected LPAREN (\"(\") at [2, 5]",
                        "locations": [{"line": 2, "column": 5}],
                    }
                ]
            },
            "expected": ShopifyResponseKind.BAD_REQUEST,
        },
        {
            "error_type": "Incorrect input in query/variables (id:gid)",
            "body": {
                "data": {"orders": {"edges": []}},
                "extensions": {
                    "search": [
                        {
                            "path": ["orders"],
                            "query": "id:gid://shopify/Order/234234234",
                            "warnings": [
                                {"field": "id", "message": "Expected field to be a positive integer or UUID, received `gid`."}
                            ],
                        }
                    ]
                },
            },
            "expected": ShopifyResponseKind.NOT_ACCEPTABLE,
        },
        {
            "error_type": "Incorrect input in return fields (undefinedField)",
            "body": {
                "errors": [
                    {
                        "message": "Field 'defaultEmail' doesn't exist on type 'Customer'",
                        "locations": [{"line": 8, "column": 25}],
                        "path": [
                            "query",
                            "orders",
                            "edges",
                            "node",
                            "customer",
                            "defaultEmail",
                        ],
                        "extensions": {
                            "code": "undefinedField",
                            "typeName": "Customer",
                            "fieldName": "defaultEmail",
                        },
                    }
                ]
            },
            "expected": ShopifyResponseKind.UNPROCESSABLE_ENTITY,
        },
        {
            "error_type": "No records found (orders edges empty)",
            "body": {"data": {"orders": {"edges": []}}},
            "expected": ShopifyResponseKind.NO_CONTENT,
        },
        {
            "error_type": "Success (orders edge with node)",
            "body": {
                "data": {
                    "orders": {
                        "edges": [
                            {
                                "node": {
                                    "id": "gid://shopify/Order/5890295201886",
                                    "name": "#43262",
                                    "email": "user@example.com",
                                }
                            }
                        ]
                    }
                }
            },
            "expected": ShopifyResponseKind.OK,
        },
    ]

    failures = 0
    for c in cases:
        actual = parse_shopify_response(c["body"])
        actual_kind = actual.kind if isinstance(actual, ShopifyResponse) else actual
        expected_kind = c["expected"]
        ok = actual_kind == expected_kind
        print(f"Case: {c['error_type']}\nExpected: {expected_kind}\nActual: {actual_kind}\nMatch: {ok}\n---")
        if not ok:
            failures += 1

    # Show logs
    out, _ = capfd.readouterr()
    print(out)

    # All test cases should pass with the implemented parser
    assert failures == 0
