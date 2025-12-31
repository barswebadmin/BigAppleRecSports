
import { getSecret } from './secretsUtils';

/**
 * Shopify API Utilities for Waitlist System
 * Handles all Shopify GraphQL API calls
 */

/**
 * Get Shopify access token
 * @returns {string} Access token
 */
export function getShopifyAccessToken() {
  return getSecret('SHOPIFY_ACCESS_TOKEN_ADMIN');
}

/**
 * Get Shopify store URL
 * @returns {string} Store URL
 */
function getShopifyStoreUrl() {
  return 'https://09fe59-3.myshopify.com';
}

/**
 * Fetch data from Shopify GraphQL API
 * @param {string} query - GraphQL query
 * @param {Object} variables - Query variables
 * @returns {Object} Response data
 */
function fetchShopify(query, variables = {}) {
  const url = `${getShopifyStoreUrl()}/admin/api/2025-04/graphql.json`;
  const token = getShopifyAccessToken();

  if (!token) {
    throw new Error('Shopify access token not configured');
  }

  const options = {
    method: 'post',
    headers: {
      'Content-Type': 'application/json',
      'X-Shopify-Access-Token': token
    },
    payload: JSON.stringify({ query, variables }),
    muteHttpExceptions: true
  };

  try {
    const response = UrlFetchApp.fetch(url, options);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();

    if (responseCode !== 200) {
      throw new Error(`Shopify API error ${responseCode}: ${responseText}`);
    }

    const data = JSON.parse(responseText);

    if (data.errors) {
      throw new Error(`Shopify GraphQL errors: ${JSON.stringify(data.errors)}`);
    }

    return data.data;
  } catch (error) {
    Logger.log(`💥 Shopify API error: ${error.message}`);
    throw error;
  }
}

/**
 * Get product by handle
 * @param {string} handle - Product handle
 * @returns {Object|null} Product data or null
 */
function getProductByHandle(handle) {
  const query = `
    query getProduct($handle: String!) {
      productByHandle(handle: $handle) {
        id
        title
        handle
      }
    }
  `;

  try {
    const data = fetchShopify(query, { handle });
    return data.productByHandle;
  } catch (error) {
    Logger.log(`❌ Error fetching product by handle '${handle}': ${error.message}`);
    return null;
  }
}

/**
 * Get product with variants and inventory
 * @param {string} productId - Product ID (GID format)
 * @returns {Object|null} Product with variants or null
 */
function getProductWithVariants(productId) {
  const query = `
    query getProduct($id: ID!) {
      product(id: $id) {
        id
        title
        handle
        variants(first: 100) {
          edges {
            node {
              id
              title
              inventoryQuantity
            }
          }
        }
      }
    }
  `;

  try {
    const data = fetchShopify(query, { id: productId });
    if (!data.product) return null;

    const product = data.product;
    product.variants = product.variants.edges.map(edge => edge.node);

    return product;
  } catch (error) {
    Logger.log(`❌ Error fetching product variants: ${error.message}`);
    return null;
  }
}

/**
 * Fetch customer by email
 * @param {string} email - Customer email
 * @returns {Object|null} Customer data or null
 */
export function fetchShopifyCustomerByEmail(email) {
  const query = `
    query getCustomer($email: String!) {
      customers(first: 1, query: $email) {
        edges {
          node {
            id
            email
            firstName
            lastName
            tags
            phone
          }
        }
      }
    }
  `;

  try {
    const data = fetchShopify(query, { email: `email:${email}` });
    if (!data.customers || data.customers.edges.length === 0) {
      return null;
    }

    return data.customers.edges[0].node;
  } catch (error) {
    Logger.log(`❌ Error fetching customer: ${error.message}`);
    return null;
  }
}

/**
 * Create Shopify customer
 * @param {string} email - Customer email
 * @param {string} firstName - First name
 * @param {string} lastName - Last name
 * @returns {string} Customer ID
 */
export function createShopifyCustomer(email, firstName, lastName) {
  const mutation = `
    mutation customerCreate($input: CustomerInput!) {
      customerCreate(input: $input) {
        customer {
          id
        }
        userErrors {
          field
          message
        }
      }
    }
  `;

  const input = {
    email: email,
    firstName: firstName || '',
    lastName: lastName || ''
  };

  try {
    const data = fetchShopify(mutation, { input });

    if (data.customerCreate.userErrors && data.customerCreate.userErrors.length > 0) {
      throw new Error(`Customer creation errors: ${JSON.stringify(data.customerCreate.userErrors)}`);
    }

    return data.customerCreate.customer.id;
  } catch (error) {
    Logger.log(`❌ Error creating customer: ${error.message}`);
    throw error;
  }
}

/**
 * Update customer tags and phone
 * @param {Object} params - {customerId, tags, phone}
 * @returns {boolean} Success
 */
export function updateCustomer({ customerId, tags, phone }) {
  const mutation = `
    mutation customerUpdate($input: CustomerInput!) {
      customerUpdate(input: $input) {
        customer {
          id
        }
        userErrors {
          field
          message
        }
      }
    }
  `;

  const input = {
    id: customerId,
    tags: Array.isArray(tags) ? tags : [tags],
  };

  if (phone) {
    input.phone = phone;
  }

  try {
    const data = fetchShopify(mutation, { input });

    if (data.customerUpdate.userErrors && data.customerUpdate.userErrors.length > 0) {
      throw new Error(`Customer update errors: ${JSON.stringify(data.customerUpdate.userErrors)}`);
    }

    Logger.log(`✅ Customer ${customerId} updated successfully`);
    return true;
  } catch (error) {
    Logger.log(`❌ Error updating customer: ${error.message}`);
    throw error;
  }
}

/**
 * Validate product and inventory using product ID
 * Checks if product is sold out (excluding waitlist variants)
 * @param {string} productId - Product ID in GraphQL format
 * @returns {Object} - {isValid: boolean, reason: string}
 */
export function validateProductAndInventoryById(productId) {
  Logger.log("🚀 === STARTING PRODUCT VALIDATION BY ID ===");
  Logger.log(`🔍 Product ID to validate: "${productId}"`);
  
  try {
    Logger.log("📞 Calling getProductWithVariants with product ID...");
    const productWithVariants = getProductWithVariants(productId);
    Logger.log(`📦 getProductWithVariants returned: ${JSON.stringify(productWithVariants, null, 2)}`);
    
    if (!productWithVariants) {
      Logger.log("❌ VALIDATION RESULT: No product found");
      return {
        isValid: false,
        reason: "No product found for this product ID"
      };
    }
    
    Logger.log(`✅ Found product: ${productWithVariants.title} (ID: ${productWithVariants.id})`);
    
    if (!productWithVariants.variants || productWithVariants.variants.length === 0) {
      Logger.log("❌ VALIDATION RESULT: Product has no variants");
      return {
        isValid: false,
        reason: "Product has no variants"
      };
    }
    
    let hasAvailableInventory = false;
    let totalNonWaitlistInventory = 0;
    
    for (const variant of productWithVariants.variants) {
      const title = (variant.title || '').toLowerCase();
      const isWaitlistVariant = title.includes('waitlist');
      
      if (!isWaitlistVariant) {
        const inventory = variant.inventoryQuantity || 0;
        totalNonWaitlistInventory += inventory;
        if (inventory > 0) {
          hasAvailableInventory = true;
        }
        
        Logger.log(`📦 Variant: "${variant.title}" - Inventory: ${inventory} (Waitlist: ${isWaitlistVariant})`);
      }
    }
    
    Logger.log(`📊 Total non-waitlist inventory: ${totalNonWaitlistInventory}`);
    Logger.log(`💰 Has available inventory: ${hasAvailableInventory}`);
    
    if (hasAvailableInventory) {
      Logger.log("❌ VALIDATION RESULT: Inventory still available");
      return {
        isValid: false,
        reason: "There are still spots available for this league"
      };
    }
    
    Logger.log("✅ VALIDATION RESULT: Product is sold out (excluding waitlist variants)");
    return {
      isValid: true,
      reason: "Product is sold out"
    };
    
  } catch (error) {
    Logger.log(`💥 Error validating product by ID: ${error.message}`);
    return {
      isValid: false,
      reason: `Validation error: ${error.message}`
    };
  }
}

/**
 * Validate product and inventory using product handle
 * @param {string} handle - Product handle
 * @returns {Object} - {isValid: boolean, reason: string}
 */
export function validateProductAndInventory(handle) {
  Logger.log("🚀 === STARTING PRODUCT VALIDATION BY HANDLE ===");
  Logger.log(`🔍 Product handle to validate: "${handle}"`);
  
  try {
    const product = getProductByHandle(handle);
    
    if (!product) {
      Logger.log("❌ VALIDATION RESULT: No product found");
      return {
        isValid: false,
        reason: "No product found for this handle"
      };
    }
    
    return validateProductAndInventoryById(product.id);
    
  } catch (error) {
    Logger.log(`💥 Error validating product by handle: ${error.message}`);
    return {
      isValid: false,
      reason: `Validation error: ${error.message}`
    };
  }
}
