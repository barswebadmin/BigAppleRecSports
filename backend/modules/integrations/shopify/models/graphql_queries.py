from __future__ import annotations
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field


class ShopifyGraphQLQuery(BaseModel):
    """
    Strongly-typed GraphQL request payload for Shopify Admin API.

    Enforces a consistent structure for all query builders to return:
    { "query": str, "variables": dict }
    """

    query: str
    variables: Dict[str, Any] = Field(default_factory=dict)

    def to_payload(self) -> Dict[str, Any]:
        return {"query": self.query, "variables": self.variables}

    @staticmethod
    def order_search(search: str) -> "ShopifyGraphQLQuery":
        """
        Build an orders search query input accepting Shopify's query string, e.g.:
        - id:1234567890
        - name:#12345

        Returns a ready-to-send payload shape.
        """
        q = (
            "query FetchOrder($q: String!){\n"
            "  orders(first: 1, query: $q){\n"
            "    edges{ node{\n"
            "      id name\n"
            "      totalPriceSet{ shopMoney{ amount currencyCode } }\n"
            "      customer{ id email }\n"
            "      transactions{ id kind gateway parentTransaction{ id } }\n"
            "      refunds{\n"
            "        createdAt\n"
            "        staffMember{ firstName lastName }\n"
            "        totalRefundedSet{ presentmentMoney{ amount currencyCode } shopMoney{ amount currencyCode } }\n"
            "      }\n"
            "      cancelledAt\n"
            "    }}\n"
            "  }\n"
            "}"
        )
        return ShopifyGraphQLQuery(query=q, variables={"q": search})