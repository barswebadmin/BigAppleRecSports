const SHOPIFY_ACCESS_TOKEN = "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";
const SHOPIFY_GRAPHQL_URL = "https://09fe59-3.myshopify.com/admin/api/2025-07/graphql.json"

const fetchShopify = (query = {}) => {
  try {
    const options = {
      method: "POST",
      contentType: "application/json",
      headers: { "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN },
      payload: JSON.stringify(query)
    };
    const response = UrlFetchApp.fetch(SHOPIFY_GRAPHQL_URL, options);
    const jsonResponse = JSON.parse(response.getContentText());

    if (jsonResponse.errors) {
      MailApp.sendEmail({
        to: DEBUG_EMAIL, 
        subject: 'Debugging fetch shopify - errors 1', 
        htmlBody: `query: ${JSON.stringify(query,null,2)} \n \n
        Shopify API Errors: ${JSON.stringify(jsonResponse.errors,null,2)}
        `
      });
    }

    return jsonResponse;
  } catch (error) {
      MailApp.sendEmail({
        to: DEBUG_EMAIL, 
        subject: 'Debugging fetch shopify - errors 2', 
        htmlBody: `query: ${JSON.stringify(query,null,2)} \n \n
        Shopify Fetch Error: ${JSON.stringify(error.message,null,2)}
        `
      });
    return null;
  }
};

function fetchShopifyOrderDetails({ orderName, email }) {
  let queryStr = "";
  let searchType = "";

  if (orderName) {
    searchType = `name:${orderName}`;
    queryStr = `orders(first: 1, query: "${searchType}")`;
  } else if (email) {
    searchType = `email:${email}`;
    queryStr = `orders(first: 10, sortKey: UPDATED_AT, reverse: true, query: "${searchType}")`;
  } else {
    Logger.log("❌ Missing orderName or email");
    return { success: false, message: "⚠️ Must provide either orderName or email." };
  }

  Logger.log(`📦 Fetching orders by ${orderName ? "orderName" : "email"}: ${searchType}`);

  const query = {
    query: `{
      ${queryStr} {
        edges {
          node {
            id
            name
            createdAt
            discountCode
            totalPriceSet { presentmentMoney { amount } }
            customer { id email }
            lineItems(first: 10) {
              edges {
                node {
                  product {
                    id title descriptionHtml tags
                    variants(first: 10) {
                      edges { node { id title inventoryItem {id} inventoryQuantity price } }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }`
  };

  let responseData;
  try {
    responseData = fetchShopify(query).data;
  } catch (err) {
      MailApp.sendEmail({
        to: DEBUG_EMAIL, 
        subject: 'Debugging fetch shopify - errors 3', 
        htmlBody: `query: ${JSON.stringify(query,null,2)} \n \n 
        fetchShopify threw error: ${JSON.stringify(err,null,2)}
        `
      });
    return { success: false, message: "⚠️ Shopify Fetch Order API call failed." };
  }

  const orders = responseData?.orders?.edges || [];

  if (orders.length === 0) {
    return { success: false, message: "⚠️ No orders found." };
  }

  const formatOrder = (orderNode) => {
    const order = orderNode.node;
    const product = order.lineItems.edges[0]?.node.product;

    if (!product) {
      return null; // Skip orders with no products
    }

    return {
      orderId: order.id,
      orderName: order.name,
      orderCreatedAt: order.createdAt,
      discountCode: order.discountCode,
      totalAmountPaid: order.totalPriceSet.presentmentMoney.amount,
      customer: {
        id: order.customer?.id || "N/A",
        email: order.customer?.email || "N/A"
      },
      product: {
        title: product.title,
        productId: product.id,
        descriptionHtml: product.descriptionHtml,
        tags: product.tags,
        variants: product.variants.edges.map(variant => ({
          variantId: variant.node.id,
          variantName: variant.node.title,
          inventory: variant.node.inventoryQuantity,
          inventoryItemId: variant.node.inventoryItem.id,
          price: variant.node.price
        }))
      }
    };
  };

  const formattedOrders = orders.map(formatOrder).filter(Boolean);

  const result = orderName
    ? formattedOrders[0]
    : formattedOrders;

  Logger.log(`✅ Processed Order Details, data: ${JSON.stringify(result, null, 2)}`);
  return { success: true, data: result };
}

const cancelShopifyOrder = (orderId) => {
  const mutation = {
    query: `
      mutation orderCancel($notifyCustomer: Boolean, $orderId: ID!, $reason: OrderCancelReason!, $refund: Boolean!, $restock: Boolean!, $staffNote: String) {
        orderCancel(notifyCustomer: $notifyCustomer, orderId: $orderId, reason: $reason, refund: $refund, restock: $restock, staffNote: $staffNote) {
          job {
            id
            done
          }
          orderCancelUserErrors {
            field
            message
          }
          userErrors {
            field
            message
          }
        }
      }
    `,
    variables: {
      notifyCustomer: true,
      orderId,
      reason: "CUSTOMER",
      refund: false,
      restock: false,
    }
  };

  const responseData = fetchShopify(mutation).data;

  if (!responseData || responseData.orderCancel?.userErrors?.length || responseData.orderCancel?.orderCancelUserErrors?.length) {
    MailApp.sendEmail({
      to: DEBUG_EMAIL, 
      subject: `❌ BARS Refund Request - Shopify Order Cancellation Failed (Order ${orderName})`, 
      htmlBody: `Cancellation errors: ${JSON.stringify(responseData?.orderCancel?.userErrors || responseData?.orderCancel?.orderCancelUserErrors, null, 2)}`
    });
    return {success: false, data: null};
  }

  return { success: true, data: responseData.orderCancel };
}

const createShopifyDiscountCode = ({ codeTitle, refundAmount, customerId }) => {

  const mutation = `
    mutation CreateDiscountCode($basicCodeDiscount: DiscountCodeBasicInput!) {
      discountCodeBasicCreate(basicCodeDiscount: $basicCodeDiscount) {
        codeDiscountNode {
          id
        }
        userErrors {
          field
          message
        }
      }
    }
  `;

  const variables = {
    basicCodeDiscount: {
      startsAt: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
      title: codeTitle,
      code: codeTitle,
      customerSelection: {
        customers: {
          add: [customerId]
        }
      },
      customerGets: {
        value: {
          discountAmount: {
            amount: Number.parseFloat(refundAmount).toFixed(2).toString()
          }
        },
        items: {
          all: true
        }
      },
      usageLimit: 1,
      appliesOncePerCustomer: true
    }
  };

  const response = fetchShopify({ query: mutation, variables }).data;

  if (
    !response || response?.discountCodeBasicCreate?.userErrors?.length
  ) {
    MailApp.sendEmail({
      to: DEBUG_EMAIL, 
      subject: '❌ BARS Refund Request - Error creating discount', 
      htmlBody: `Discount errors: ${JSON.stringify(response.discountCodeBasicCreate.userErrors, null, 2)}}`
    });
    return {success: false, data: null};
  }

  const codeInfo = response.discountCodeBasicCreate?.codeDiscountNode;
  return {success: true, data: codeInfo};
}

const createShopifyRefund = (orderId, refundAmount) => {
  // Step 1: Fetch order transactions
  const orderDetailsQuery = {
    query: `
      query getOrderDetails($id: ID!) {
        order(id: $id) {
          id
          transactions {
            id
            kind
            gateway
            parentTransaction { id }
          }
        }
      }`,
    variables: {
      id: orderId
    }
  };

  const orderData = fetchShopify(orderDetailsQuery).data;
  if (!orderData?.order?.transactions?.length) {
    throw new Error("No transactions found for this order.");
  }

  const captureTransaction = orderData.order.transactions.find(t => t.kind === "CAPTURE");
  if (!captureTransaction) {
    throw new Error("No capture transaction found for refund.");
  }

  const gateway = captureTransaction.gateway;
  const parentTransactionId = captureTransaction.parentTransaction?.id || captureTransaction.id;

  // Step 2: Build and send the refund mutation
  const refundMutation = {
    query: `
      mutation CreateRefund($input: RefundInput!) {
        refundCreate(input: $input) {
          refund {
            id
            note
            totalRefundedSet {
              presentmentMoney {
                amount
              }
            }
          }
          userErrors {
            field
            message
          }
        }
      }`,
    variables: {
      input: {
        notify: true,
        orderId: orderId,
        note: `Refund issued via Slack workflow for $${formatTwoDecimalPoints(refundAmount)}`,
        transactions: [
          {
            orderId: orderId,
            gateway,
            kind: "REFUND",
            amount: refundAmount.toString(),
            parentId: parentTransactionId
          }
        ]
      }
    }
  };

  const response = fetchShopify(refundMutation).data;
  const errors = response?.refundCreate?.userErrors;

  if (
    errors?.length
  ) {
    MailApp.sendEmail({
      to: DEBUG_EMAIL, 
      subject: '❌ BARS Refund Request - Error creating refund', 
      htmlBody: `Refund errors: ${JSON.stringify(errors, null, 2)}}`
    });
    return {success: false, data: null};
  }

  return {success: true, data: response?.refundCreate?.refund?.id || "Refund created but no ID returned."};
}

const createShopifyStoreCredit = ({ formattedOrderNumber, orderId, refundAmount }) => {
  
  const storeCreditMutation = {
    query: `
      mutation CreateRefund($input: RefundInput!) {
        refundCreate(input: $input) {
          refund {
            id
            note
            totalRefundedSet {
              presentmentMoney {
                amount
              }
            }
          }
          userErrors {
            field
            message
          }
        }
      }`,
    variables: {
      input: {
        notify: true,
        orderId: orderId,
        note: `Store Credit issued via Slack workflow for $${formatTwoDecimalPoints(refundAmount)}`,
        refundMethods: [{
          storeCreditRefund: {
            amount: {
              amount: refundAmount.toString(),
              currencyCode: "USD"
            }
          }
        }]
      }
    }
  };

  const response = fetchShopify(storeCreditMutation).data;
  // MailApp.sendEmail({
  //     to: DEBUG_EMAIL, 
  //     subject: 'Debugging store credit - shopify response', 
  //     htmlBody: `${JSON.stringify(response,null,2)}`
  //   });
  const errors = response?.refundCreate?.userErrors;

  if (
    errors?.length
  ) {
    MailApp.sendEmail({
      to: DEBUG_EMAIL, 
      subject: `❌ BARS Store Credit Request (Order ${formattedOrderNumber}) - Error creating Store Credit`, 
      htmlBody: `Discount errors: ${JSON.stringify(errors, null, 2)}}`
    });
    return {success: false, data: null};
  }

  return {success: true, data: response?.refundCreate?.refund?.id || "Refund created but no ID returned."};
}






const createShopifyRefundDebugVersion = (orderId, refundAmount) => {
  // Step 1: Fetch order transactions
  const orderDetailsQuery = {
    query: `
      query getOrderDetails($id: ID!) {
        order(id: $id) {
          id
          transactions {
            id
            kind
            gateway
            parentTransaction { id }
          }
        }
      }`,
    variables: {
      id: orderId
    }
  };

  const orderData = fetchShopify(orderDetailsQuery).data;
  if (!orderData?.order?.transactions?.length) {
    throw new Error("No transactions found for this order.");
  }

  const captureTransaction = orderData.order.transactions.find(t => ["CAPTURE","SALE"].includes(t.kind));
  if (!captureTransaction) {
    throw new Error("No capture transaction found for refund.");
  }

  const gateway = captureTransaction.gateway;
  const parentTransactionId = captureTransaction.parentTransaction?.id || captureTransaction.id;

  // Step 2: Build and send the refund mutation
  const refundMutation = {
    query: `
      mutation CreateRefund($input: RefundInput!) {
        refundCreate(input: $input) {
          refund {
            id
            note
            totalRefundedSet {
              presentmentMoney {
                amount
              }
            }
          }
          userErrors {
            field
            message
          }
        }
      }`.replace(/\s+/g, ' ').trim(),
    variables: {
      input: {
        notify: true,
        orderId: orderId,
        note: `Refund issued via Slack workflow for $${formatTwoDecimalPoints(refundAmount)}`,
        transactions: [
          {
            orderId: orderId,
            gateway,
            kind: "REFUND",
            amount: refundAmount.toString(),
            parentId: parentTransactionId
          }
        ]
      }
    }
  };

  const curlCommand = `
  curl -X POST ${SHOPIFY_GRAPHQL_URL} \\
  -H "Content-Type: application/json" \\
  -H "X-Shopify-Access-Token: YOUR_ACCESS_TOKEN" \\
  -d '${JSON.stringify(refundMutation)}'
  `.trim();

  MailApp.sendEmail({
    to: DEBUG_EMAIL,
    subject: '🧪 Shopify Store Credit – Debug Curl Command',
    htmlBody: `<p>Here's your ready-to-run curl command:</p><pre>${curlCommand}</pre>`
  });

  return { success: true, data: "DEBUG – NO REFUND ACTUALLY CREATED" };
}

const createShopifyStoreCreditDebugVersion = ({ formattedOrderNumber, orderId, refundAmount }) => {
  const mutationQuery = `
    mutation CreateRefund($input: RefundInput!) {
      refundCreate(input: $input) {
        refund {
          id
          note
          totalRefundedSet {
            presentmentMoney {
              amount
            }
          }
        }
        userErrors {
          field
          message
        }
      }
    }`.replace(/\s+/g, ' ').trim(); // Collapse into single line

  const variables = {
    input: {
      notify: true,
      orderId: orderId,
      note: `Store Credit issued via Slack workflow for $${formatTwoDecimalPoints(refundAmount)}`,
      refundMethods: [{
        storeCreditRefund: {
          amount: {
            amount: refundAmount.toString(),
            currencyCode: "USD"
          }
        }
      }]
    }
  };

  const curlPayload = {
    query: mutationQuery,
    variables: variables
  };

  const curlCommand = `
  curl -X POST ${SHOPIFY_GRAPHQL_URL} \\
  -H "Content-Type: application/json" \\
  -H "X-Shopify-Access-Token: YOUR_ACCESS_TOKEN" \\
  -d '${JSON.stringify(curlPayload)}'
  `.trim();

  MailApp.sendEmail({
    to: DEBUG_EMAIL,
    subject: '🧪 Shopify Store Credit – Debug Curl Command',
    htmlBody: `<p>Here's your ready-to-run curl command:</p><pre>${curlCommand}</pre>`
  });

  return { success: true, data: "DEBUG – NO REFUND ACTUALLY CREATED" };
};