#!/bin/bash

# Test script to check both API versions with order 42309
SHOPIFY_STORE="09fe59-3.myshopify.com"
SHOPIFY_TOKEN="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"

echo "🔍 Testing Shopify API versions with order #42309"
echo "================================================="
echo

# Test 1: Backend's current version (2025-07)
echo "📤 TEST 1: Backend version (2025-07)"
echo "URL: https://${SHOPIFY_STORE}/admin/api/2025-07/graphql.json"
echo

curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Access-Token: ${SHOPIFY_TOKEN}" \
  -d '{
    "query": "{ orders(first: 1, query: \"name:#42309\") { edges { node { id name createdAt customer { email } } } } }"
  }' \
  "https://${SHOPIFY_STORE}/admin/api/2025-07/graphql.json" | jq '.'

echo
echo "================================================="
echo

# Test 2: Environment version (2025-01)
echo "📤 TEST 2: Environment version (2025-01)"
echo "URL: https://${SHOPIFY_STORE}/admin/api/2025-01/graphql.json"
echo

curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Access-Token: ${SHOPIFY_TOKEN}" \
  -d '{
    "query": "{ orders(first: 1, query: \"name:#42309\") { edges { node { id name createdAt customer { email } } } } }"
  }' \
  "https://${SHOPIFY_STORE}/admin/api/2025-01/graphql.json" | jq '.'

echo
echo "================================================="
echo

# Test 3: Current stable version (2024-10)
echo "📤 TEST 3: Current stable version (2024-10)"
echo "URL: https://${SHOPIFY_STORE}/admin/api/2024-10/graphql.json"
echo

curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Access-Token: ${SHOPIFY_TOKEN}" \
  -d '{
    "query": "{ orders(first: 1, query: \"name:#42309\") { edges { node { id name createdAt customer { email } } } } }"
  }' \
  "https://${SHOPIFY_STORE}/admin/api/2024-10/graphql.json" | jq '.'

echo
echo "🎯 SUMMARY:"
echo "- 2025-07: Backend's hardcoded version"
echo "- 2025-01: Environment variable version"
echo "- 2024-10: Current stable version"
echo
echo "Look for which version returns the order data successfully!"
