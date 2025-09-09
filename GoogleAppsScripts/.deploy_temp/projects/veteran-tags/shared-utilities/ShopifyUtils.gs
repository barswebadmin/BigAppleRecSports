// =============================================================================
// Shopify Utilities - Consolidated from all projects
// =============================================================================

// Constants - Replace with actual values in setupSecrets
const SHOPIFY_ACCESS_TOKEN = "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";
const SHOPIFY_API_URL = 'https://09fe59-3.myshopify.com/admin/api/2023-10/graphql.json';
const SHOPIFY_GRAPHQL_URL = "https://09fe59-3.myshopify.com/admin/api/2025-07/graphql.json";

// =============================================================================
// Core Shopify API Functions
// =============================================================================

/**
 * Core function to make GraphQL requests to Shopify
 * @param {Object} payload - GraphQL query and variables
 * @returns {Object} - Shopify API response
 */
function fetchShopify(payload) {
  const options = {
    method: 'POST',
    contentType: 'application/json',
    headers: {
      'X-Shopify-Access-Token': SHOPIFY_ACCESS_TOKEN
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  Logger.log(`📤 Sending to Shopify:\n${JSON.stringify(payload, null, 2)}`);

  const response = UrlFetchApp.fetch(SHOPIFY_API_URL, options);
  const parsed = JSON.parse(response.getContentText());

  Logger.log(`📥 Response from Shopify:\n${JSON.stringify(parsed, null, 2)}`);

  return parsed;
}

/**
 * Alternative fetch function with error handling via email
 * Used by process-refunds-exchanges project
 */
const fetchShopifyWithEmailErrors = (query = {}) => {
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
      const debugEmail = getDebugEmail();
      if (debugEmail) {
        MailApp.sendEmail({
          to: debugEmail, 
          subject: 'Debugging fetch shopify - errors 1', 
          htmlBody: `query: ${JSON.stringify(query,null,2)} \n \n
          Shopify API Errors: ${JSON.stringify(jsonResponse.errors,null,2)}
          `
        });
      }
    }

    return jsonResponse;
  } catch (error) {
    const debugEmail = getDebugEmail();
    if (debugEmail) {
      MailApp.sendEmail({
        to: debugEmail, 
        subject: 'Debugging fetch shopify - errors 2', 
        htmlBody: `query: ${JSON.stringify(query,null,2)} \n \n
        Shopify Fetch Error: ${JSON.stringify(error.message,null,2)}
        `
      });
    }
    return null;
  }
};

/**
 * Helper to get debug email from properties or constants
 */
function getDebugEmail() {
  try {
    return PropertiesService.getScriptProperties().getProperty('DEBUG_EMAIL') || 
           (typeof DEBUG_EMAIL !== 'undefined' ? DEBUG_EMAIL : null);
  } catch (error) {
    return null;
  }
}

// =============================================================================
// Product Functions
// =============================================================================

/**
 * Get product by handle
 * @param {string} handle - Product handle
 * @returns {Object|null} - Product data or null if not found
 */
function getProductByHandle(handle) {
  const query = `
    query {
      productByHandle(handle: "${handle}") {
        id
        title
        handle
      }
    }
  `;

  const payload = { query };
  const result = fetchShopify(payload);

  if (result.errors) {
    Logger.log(`❌ Error fetching product by handle "${handle}": ${JSON.stringify(result.errors, null, 2)}`);
    return null;
  }

  const product = result.data?.productByHandle;

  if (!product) {
    Logger.log(`⚠️ No product found with handle "${handle}"`);
    return null;
  }

  Logger.log(`✅ Product found: ${JSON.stringify(product, null, 2)}`);
  return product;
}

/**
 * Get product with variants and inventory by product ID
 * @param {string} productId - Product ID
 * @returns {Object|null} - Product with variants or null if not found
 */
function getProductWithVariants(productId) {
  const query = `
    query getProduct($id: ID!) {
      product(id: $id) {
        id
        title
        handle
        variants(first: 50) {
          edges {
            node {
              id
              title
              inventoryQuantity
              price
            }
          }
        }
      }
    }
  `;

  const payload = {
    query,
    variables: { id: productId }
  };

  const result = fetchShopify(payload);

  if (result.errors) {
    Logger.log(`❌ Error fetching product variants for ID "${productId}": ${JSON.stringify(result.errors, null, 2)}`);
    return null;
  }

  const product = result.data?.product;
  if (!product) {
    Logger.log(`⚠️ No product found with ID "${productId}"`);
    return null;
  }

  // Convert GraphQL response to flattened format
  const flattenedProduct = {
    id: product.id,
    title: product.title,
    handle: product.handle,
    variants: product.variants.edges.map(edge => ({
      id: edge.node.id,
      title: edge.node.title,
      inventoryQuantity: edge.node.inventoryQuantity,
      price: edge.node.price
    }))
  };

  Logger.log(`✅ Product with variants found: ${JSON.stringify(flattenedProduct, null, 2)}`);
  return flattenedProduct;
}

/**
 * Constructs a Shopify product handle from components
 * @param {string} year - Year (e.g., "2025")
 * @param {string} season - Season (e.g., "fall")
 * @param {string} sport - Sport (e.g., "kickball")
 * @param {string} day - Day (e.g., "sunday")
 * @param {string} rawDivision - Division (e.g., "Open Division")
 * @returns {string} - The constructed handle
 */
function getProductHandleOrPromptFallback(year, season, sport, day, rawDivision) {
  let handle = '';
  try {
    const getDivisionString = rawDivision => {
      return rawDivision.split(' ')[0].replace('+','').toLowerCase() + 'div'
    }

    return `${year}-${season.toLowerCase()}-${sport.toLowerCase()}-${day.toLowerCase()}-${getDivisionString(rawDivision)}`
  } catch (err) {
    Logger.log(`⚠️ Failed to generate product handle: ${err.message}`);

    // Prompt the user for manual input
    const ui = SpreadsheetApp.getUi();
    const resp = ui.prompt(
      'Product Handle Needed',
      'Automatic handle generation failed.\n\n' +
      'Please paste the full Product URL from the live registration page (e.g. https://barsleague.com/products/2025-spring-dodgeball-thursday-opendiv)\n\n' +
      'We will use the part after the last "/" as the product handle.',
      ui.ButtonSet.OK_CANCEL
    );

    if (resp.getSelectedButton() !== ui.Button.OK) {
      throw new Error('User canceled manual product handle entry.');
    }

    const inputUrl = resp.getResponseText().trim();
    if (!inputUrl) throw new Error('No input provided.');

    // Take the substring after the last '/'
    const urlParts = inputUrl.split('/');
    handle = urlParts[urlParts.length - 1].trim();

    if (!handle) throw new Error('Unable to extract handle from provided URL.');

    Logger.log(`✅ Using manual product handle: ${handle}`);
    return handle;
  }
}

// =============================================================================
// Customer Functions
// =============================================================================

/**
 * Fetch Shopify customer by email
 * @param {string} email - Customer email
 * @returns {Object|null} - Customer data or null if not found
 */
function fetchShopifyCustomerByEmail(email) {
  const query = {
    query: `{
      customers(first: 1, query: "email:${email}") {
        edges {
          node {
            id
            email
            tags
          }
        }
      }
    }`
  };

  const response = fetchShopify(query);
  const customer = response?.data?.customers?.edges?.[0]?.node || null;
  return customer;
}

/**
 * Create new Shopify customer
 * @param {string} email - Customer email
 * @param {string} firstName - Customer first name
 * @param {string} lastName - Customer last name
 * @returns {string} - Customer ID
 */
function createShopifyCustomer(email, firstName, lastName) {
  const mutation = {
    query: `mutation customerCreate($input: CustomerInput!) {
      customerCreate(input: $input) {
        customer {
          id
          email
          tags
        }
        userErrors {
          field
          message
        }
      }
    }`,
    variables: {
      input: {
        email,
        firstName,
        lastName,
        taxExempt: true,
        emailMarketingConsent: {
          marketingState: "SUBSCRIBED",
          marketingOptInLevel: "SINGLE_OPT_IN",
          consentUpdatedAt: new Date().toISOString()
        }
      }
    }
  };

  const response = fetchShopify(mutation);
  if (response.data?.customerCreate?.userErrors?.length) throw new Error(`Error creating new customer: ${response.data.customerCreate.userErrors}`)
  Logger.log(`created customer: ${JSON.stringify(response.data.customerCreate.customer,null,2)}`)
  const customerId = response?.data?.customerCreate.customer.id
  return customerId;
}

/**
 * Update existing Shopify customer
 * @param {Object} params - Update parameters
 * @param {string} params.customerId - Customer ID
 * @param {Array} params.tags - Customer tags
 * @param {string} params.phone - Customer phone (optional)
 * @returns {Object} - Updated customer data
 */
function updateCustomer({ customerId, tags, phone }) {
  const normalizedPhoneData = phone ? {phone: phone} : {}

  const mutation = {
    query: `mutation customerUpdate($input: CustomerInput!) {
      customerUpdate(input: $input) {
        customer {
          id
          tags
        }
        userErrors {
          field
          message
        }
      }
    }`,
    variables: {
      input: {
        id: customerId,
        tags,
        ...normalizedPhoneData, 
      }
    }
  };

  const response = fetchShopify(mutation);
  if (response.data?.customerUpdate?.userErrors.length) throw new Error(`Error updating customer: ${response.data.customerUpdate.userErrors}`)
  const customer = response.data?.customerUpdate.customer
  return customer
}

// =============================================================================
// Order Functions
// =============================================================================

/**
 * Fetch Shopify order details by order name or customer email
 * @param {Object} params - Search parameters
 * @param {string} params.orderName - Order name (optional)
 * @param {string} params.email - Customer email (optional)
 * @returns {Object} - Order details response
 */
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
    responseData = fetchShopifyWithEmailErrors(query).data;
  } catch (err) {
    const debugEmail = getDebugEmail();
    if (debugEmail) {
      MailApp.sendEmail({
        to: debugEmail, 
        subject: 'Debugging fetch shopify - errors 3', 
        htmlBody: `query: ${JSON.stringify(query,null,2)} \n \n 
        fetchShopify threw error: ${JSON.stringify(err,null,2)}
        `
      });
    }
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

/**
 * Cancel a Shopify order
 * @param {string} orderId - Order ID to cancel
 * @returns {Object} - Cancellation result
 */
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

  const responseData = fetchShopifyWithEmailErrors(mutation).data;

  if (!responseData || responseData.orderCancel?.userErrors?.length || responseData.orderCancel?.orderCancelUserErrors?.length) {
    const debugEmail = getDebugEmail();
    if (debugEmail) {
      MailApp.sendEmail({
        to: debugEmail, 
        subject: `❌ BARS Refund Request - Shopify Order Cancellation Failed`, 
        htmlBody: `Cancellation errors: ${JSON.stringify(responseData?.orderCancel?.userErrors || responseData?.orderCancel?.orderCancelUserErrors, null, 2)}`
      });
    }
    return {success: false, data: null};
  }

  return { success: true, data: responseData.orderCancel };
}

// =============================================================================
// Discount and Refund Functions
// =============================================================================

/**
 * Create a Shopify discount code
 * @param {Object} params - Discount parameters
 * @param {string} params.codeTitle - Discount code title
 * @param {number} params.refundAmount - Refund amount
 * @param {string} params.customerId - Customer ID
 * @returns {Object} - Discount creation result
 */
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

  const response = fetchShopifyWithEmailErrors({ query: mutation, variables }).data;

  if (!response || response?.discountCodeBasicCreate?.userErrors?.length) {
    const debugEmail = getDebugEmail();
    if (debugEmail) {
      MailApp.sendEmail({
        to: debugEmail, 
        subject: '❌ BARS Refund Request - Error creating discount', 
        htmlBody: `Discount errors: ${JSON.stringify(response.discountCodeBasicCreate.userErrors, null, 2)}}`
      });
    }
    return {success: false, data: null};
  }

  const codeInfo = response.discountCodeBasicCreate?.codeDiscountNode;
  return {success: true, data: codeInfo};
}

/**
 * Create a Shopify refund
 * @param {string} orderId - Order ID
 * @param {number} refundAmount - Refund amount
 * @returns {Object} - Refund creation result
 */
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

  const orderData = fetchShopifyWithEmailErrors(orderDetailsQuery).data;
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

  const response = fetchShopifyWithEmailErrors(refundMutation).data;
  const errors = response?.refundCreate?.userErrors;

  if (errors?.length) {
    const debugEmail = getDebugEmail();
    if (debugEmail) {
      MailApp.sendEmail({
        to: debugEmail, 
        subject: '❌ BARS Refund Request - Error creating refund', 
        htmlBody: `Refund errors: ${JSON.stringify(errors, null, 2)}}`
      });
    }
    return {success: false, data: null};
  }

  return {success: true, data: response?.refundCreate?.refund?.id || "Refund created but no ID returned."};
}

/**
 * Create a Shopify store credit
 * @param {Object} params - Store credit parameters
 * @param {string} params.formattedOrderNumber - Formatted order number
 * @param {string} params.orderId - Order ID
 * @param {number} params.refundAmount - Refund amount
 * @returns {Object} - Store credit creation result
 */
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

  const response = fetchShopifyWithEmailErrors(storeCreditMutation).data;
  const errors = response?.refundCreate?.userErrors;

  if (errors?.length) {
    const debugEmail = getDebugEmail();
    if (debugEmail) {
      MailApp.sendEmail({
        to: debugEmail, 
        subject: `❌ BARS Store Credit Request (Order ${formattedOrderNumber}) - Error creating Store Credit`, 
        htmlBody: `Discount errors: ${JSON.stringify(errors, null, 2)}}`
      });
    }
    return {success: false, data: null};
  }

  return {success: true, data: response?.refundCreate?.refund?.id || "Refund created but no ID returned."};
}

// =============================================================================
// Debug Functions
// =============================================================================

/**
 * Debug version of createShopifyRefund that generates curl commands
 */
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

  const orderData = fetchShopifyWithEmailErrors(orderDetailsQuery).data;
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

  const debugEmail = getDebugEmail();
  if (debugEmail) {
    MailApp.sendEmail({
      to: debugEmail,
      subject: '🧪 Shopify Store Credit – Debug Curl Command',
      htmlBody: `<p>Here's your ready-to-run curl command:</p><pre>${curlCommand}</pre>`
    });
  }

  return { success: true, data: "DEBUG – NO REFUND ACTUALLY CREATED" };
}

/**
 * Debug version of createShopifyStoreCredit that generates curl commands
 */
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

  const debugEmail = getDebugEmail();
  if (debugEmail) {
    MailApp.sendEmail({
      to: debugEmail,
      subject: '🧪 Shopify Store Credit – Debug Curl Command',
      htmlBody: `<p>Here's your ready-to-run curl command:</p><pre>${curlCommand}</pre>`
    });
  }

  return { success: true, data: "DEBUG – NO REFUND ACTUALLY CREATED" };
};

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Format number to two decimal places
 * @param {number} amount - Amount to format
 * @returns {string} - Formatted amount
 */
function formatTwoDecimalPoints(amount) {
  return Number(amount).toFixed(2);
}
