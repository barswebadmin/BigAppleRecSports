
// ORDERS
// Get Order Details by Identifier (name, id)
/*
curl -X POST "https://09fe59-3.myshopify.com/admin/api/2025-07/graphql.json" \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Access-Token: shopify_token" \
  -w '{"status_code": %{http_code}}\n' \
  -d '{
    "query": "query { orders(first: 1, query: \"name:43298\") { edges { node { id name email totalPriceSet { shopMoney { amount currencyCode } } } } } }"
  }'
  */