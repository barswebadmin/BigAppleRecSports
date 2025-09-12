#!/bin/bash

# Test the exact query format that the backend uses
SHOPIFY_STORE="09fe59-3.myshopify.com"
SHOPIFY_TOKEN="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"

echo "🔍 Testing EXACT backend GraphQL query with order #42309"
echo "======================================================="
echo

echo "📤 Backend's full query (2025-07 version):"
echo "URL: https://${SHOPIFY_STORE}/admin/api/2025-07/graphql.json"
echo

# This is the exact query structure from orders_service.py lines 59-88
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Access-Token: ${SHOPIFY_TOKEN}" \
  -d '{
    "query": "{ orders(first: 1, query: \"name:#42309\") { edges { node { id name createdAt discountCode totalPriceSet { presentmentMoney { amount } } customer { id email } lineItems(first: 10) { edges { node { id title quantity originalUnitPriceSet { presentmentMoney { amount } } product { id title descriptionHtml tags } } } } } } } }"
  }' \
  "https://${SHOPIFY_STORE}/admin/api/2025-07/graphql.json" | jq '.'

echo
echo "======================================================="
echo

echo "📤 Same query but with 2025-01 version:"
echo "URL: https://${SHOPIFY_STORE}/admin/api/2025-01/graphql.json"
echo

curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Access-Token: ${SHOPIFY_TOKEN}" \
  -d '{
    "query": "{ orders(first: 1, query: \"name:#42309\") { edges { node { id name createdAt discountCode totalPriceSet { presentmentMoney { amount } } customer { id email } lineItems(first: 10) { edges { node { id title quantity originalUnitPriceSet { presentmentMoney { amount } } product { id title descriptionHtml tags } } } } } } } }"
  }' \
  "https://${SHOPIFY_STORE}/admin/api/2025-01/graphql.json" | jq '.'

echo
echo "🎯 If both return data, then the issue is NOT the query format!"
