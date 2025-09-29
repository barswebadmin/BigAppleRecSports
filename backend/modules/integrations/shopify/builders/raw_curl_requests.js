
// ORDERS
// Get Order Details by Identifier (name, id)
/*
curl -X POST "https://09fe59-3.myshopify.com/admin/api/2025-07/graphql.json" \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Access-Token: shopify_token" \
  -w '{"status_code": %{http_code}}\n' \
  -d '{
    "query": "query { orders(first: 1, query: \"${id | name}:43298\") { edges { node { id name email totalPriceSet { shopMoney { amount currencyCode } } } } } }"
  }'
  */

  /*
with more details, prob should combine:
curl -X POST https://09fe59-3.myshopify.com/admin/api/2025-07/graphql.json \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Access-Token: shopify_token" \
  -w '{"status_code": %{http_code}}\n' \
  -d '{"query": "query getOrderDetails($id: ID!) 
  { order(id: $id) 
   { id transactions
     { createdAt id kind gateway parentTransaction 
      { id 
       }
      }
       }
      }", 
      "variables": { "id": "gid://shopify/Order/23453" }}'
  * /



  REFUNDS

  /* Create Refund - not sure which one works
curl -X POST https://09fe59-3.myshopify.com/admin/api/2025-07/graphql.json \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Access-Token: shopify_token" \
  -d '{"query":"mutation CreateRefund($input: RefundInput!) { refundCreate(input: $input) { refund { id note totalRefundedSet { presentmentMoney { amount } } } userErrors { field message } } }","variables":{"input":{"notify":true,"orderId":"gid://shopify/Order/5741898694750","note":"Store Credit issued via Slack workflow for $86.25","refundMethods":[{"storeCreditRefund":{"amount":{"amount":"86.25","currencyCode":"USD"}}}]}}}'


  curl -X POST https://09fe59-3.myshopify.com/admin/api/2025-07/graphql.json \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Access-Token: shopify_token" \
  -d '{"query":"mutation CreateRefund($input: RefundInput!) { refundCreate(input: $input) { refund { id note totalRefundedSet { presentmentMoney { amount } } } userErrors { field message } } }","variables":{"input":{"notify":true,"orderId":"gid://shopify/Order/5741898694750","note":"Store Credit issued via Slack workflow for $86.25","refundMethods":[{"storeCreditRefund":{"amount":{"amount":"86.25","currencyCode":"USD"}}}]}}}'


  curl -X POST https://09fe59-3.myshopify.com/admin/api/2025-07/graphql.json \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Access-Token: shopify_token" \
  -d '{"query":"mutation CreateRefund($input: RefundInput!) { refundCreate(input: $input) { refund { id note totalRefundedSet { presentmentMoney { amount } } } userErrors { field message } } }","variables":{"input":{"notify":true,"orderId":"gid://shopify/Order/5783646765150","note":"Refund issued via Slack workflow for $35.00","transactions":[{"orderId":"gid://shopify/Order/5783646765150","gateway":"shopify_payments","kind":"REFUND","amount":"35.0","parentId":"gid://shopify/OrderTransaction/7409358209118"}]}}}'
  */

// PRODUCTS  
  /* // update media

  curl -X POST \
https://09fe59-3.myshopify.com/admin/api/2025-10/graphql.json \
-H 'Content-Type: application/json' \
-H 'X-Shopify-Access-Token: shopify_token' \
-d '{
"query": "mutation UpdateProductWithNewMedia($product: ProductUpdateInput!, $media: [CreateMediaInput!]) { productUpdate(product: $product, media: $media) { product { id media(first: 10) { nodes { alt mediaContentType preview { status } } } } userErrors { field message } } }",
 "variables": {
    "product": {
      "id": "gid://shopify/Product/{product_gid}"
    },
    "media": [
      {
        "originalSource": {sold_out_image_url},
        "alt": "Sold out image for {sport}",
        "mediaContentType": "IMAGE"
      }
    ]
  }
}'

// update product attributes:

curl -X POST "https://09fe59-3.myshopify.com/admin/api/2025-07/graphql.json" \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Access-Token: shopify_token" \
  -d '{"query":"mutation { productUpdate(input: {id: \"gid://shopify/Product/7350462185566\", tags: [\"waitlist-only\"]}) { product { id tags } userErrors { field message } } }"}'
  
// Get product by identifier:

curl -X POST \
https://09fe59-3.myshopify.com/admin/api/2025-10/graphql.json \
-H 'Content-Type: application/json' \
-H 'X-Shopify-Access-Token: shopify_token' \
-d '{
"query": "query($identifier: ProductIdentifierInput!) { product: productByIdentifier(identifier: $identifier) { id handle title tags } }",
 "variables": {
    "identifier": {
      "id": "gid://shopify/Product/7461773082718"
    }
  }
}'

  */


/* update product handle:

curl -X POST "https://09fe59-3.myshopify.com/admin/api/2025-01/graphql.json" \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Access-Token: shopify_token" \
  -d '{
    "query": "mutation productUpdate($input: ProductInput!) { productUpdate(input: $input) { product { id handle } userErrors { field message } } }",
    "variables": {
      "input": {
        "id": "gid://shopify/Product/7461773082718",
        "handle": "2025-fall-pickleball-thursday-opendiv"
      }
    }
  }'

*/




// VARIANTS
/*
// Get first variant:
curl -X POST "https://09fe59-3.myshopify.com/admin/api/2025-07/graphql.json" \
  -H "Content-Type: application/json" \
  -w "%{http_code}" \
  -H "X-Shopify-Access-Token: shopify_token" \
  -d '{"query":"query { product(id: \"gid://shopify/Product/7350462185566\") { tags variants(first: 1) { nodes { id name } } } }"}'


// Set variant to taxable: false and requiresShipping: false

curl -X POST "https://09fe59-3.myshopify.com/admin/api/2025-07/graphql.json" \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Access-Token: shopify_token" \
  -d '{"query":"mutation { productVariantUpdate(input: { id: \"gid://shopify/ProductVariant/7448170070110\", taxable: false, requiresShipping: false }) { userErrors { field message } } }"}'


  // Get Line Items:
  curl -X POST "https://09fe59-3.myshopify.com/admin/api/2025-07/graphql.json" -H "Content-Type: application/json" -H "X-Shopify-Access-Token: shopify_token" -d '{"query":"{ order(id: \"gid://shopify/Order/5885867851870\") { id name lineItems(first: 50) { edges { node { id title quantity } } } } }"}'
*/




// REFUNDS


/*
curl -X POST "https://09fe59-3.myshopify.com/admin/api/2025-07/graphql.json" \ 
-H "Content-Type: application/json" \
-H "X-Shopify-Access-Token: shopify_token" \
-d '{"query":"mutation { orderEditBegin(id: \"5885867851870\") { calculatedOrder { id } userErrors { field message } } }"}'

  curl -X POST "https://09fe59-3.myshopify.com/admin/api/2025-07/graphql.json" \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Access-Token: shopify_token" \
  {"query":"mutation { orderEditBegin(id: \"5885867851870\") { calculatedOrder { id } userErrors { field message } } }"}

  query: `mutation {productVariantUpdate(input: {id: \"gid://shopify/Product/7448170070110\",taxable: false,requiresShipping: false}) {userErrors { field message }}}`


curlj -X POST https://09fe59-3.myshopify.com/admin/api/2025-07/graphql.json \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Access-Token: shopify_token" \
  -d '{"query":"mutation CreateRefund($input: RefundInput!) { refundCreate(input: $input) { refund { id note totalRefundedSet { presentmentMoney { amount }}} userErrors { field message }}}","variables":{"input":{"notify":true,"orderId":"gid:\/\/shopify\/Order\/5759496454238","note":"Store Credit issued via Slack workflow for $2","refundMethods": [{ "storeCreditRefund": { "amount": { "amount": "2.00", "currencyCode": "USD"}} }] }}}'

  query: `
      mutation CreateRefund($input: RefundInput!) { refundCreate(input: $input) { refund { id note totalRefundedSet { presentmentMoney { amount }}} userErrors { field message }}}`,
    variables: {
      input: {
        notify: true,
        orderId: orderId,
        note: `Store Credit issued via Slack workflow for $${refundAmount}`,
        refundMethods: {
          storeCreditRefund: {
            amount: refundAmount.toString()
          }
        }
      }
    }

*/