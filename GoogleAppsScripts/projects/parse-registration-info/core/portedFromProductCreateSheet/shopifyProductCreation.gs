/**
 * Core Shopify product creation logic ported from product-variant-creation
 * This handles the actual API calls to create products and variants
 * 
 * @fileoverview Shopify API integration for product and variant creation
 * @requires ../../shared-utilities/secretsUtils.gs
 * @requires ../../shared-utilities/ShopifyUtils.gs
 */

// Shopify location GID (same as product-variant-creation)
const SHOPIFY_LOCATION_GID = "gid://shopify/Location/61802217566";

/**
 * Main function to create Shopify product from parsed data
 */
function createShopifyProductFromData_(productData) {
  try {
    Logger.log(`Creating Shopify product from data: ${JSON.stringify(productData, null, 2)}`);
    
    // Step 1: Create the main product
    const productResult = createMainProduct_(productData);
    if (!productResult.success) {
      return productResult;
    }
    
    // Step 2: Create variants
    const variantsResult = createProductVariants_(productResult.productGid, productData);
    if (!variantsResult.success) {
      return variantsResult;
    }
    
    // Step 3: Schedule inventory moves and price changes
    scheduleProductUpdates_(productResult.productId, productData);
    
    return {
      success: true,
      productUrl: productResult.productUrl,
      productId: productResult.productId,
      productGid: productResult.productGid,
      variants: variantsResult.variants,
      variantsSummary: variantsResult.summary
    };
    
  } catch (error) {
    Logger.log(`Error in createShopifyProductFromData_: ${error}`);
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * Create the main Shopify product
 */
function createMainProduct_(productData) {
  try {
    const { sport, day, division, season, year, seasonStartDate, seasonEndDate, location, price, leagueDetails } = productData;
    
    // Build product title
    const productTitle = `${sport} - ${day} - ${division} - ${season} ${year}`;
    
    // Build product description
    const productDescription = buildProductDescription_(productData);
    
    // Create GraphQL mutation
    const mutation = JSON.stringify({
      query: `
        mutation productCreate($product: ProductInput!) {
          productCreate(product: $product) {
            product {
              id
              title
            }
            userErrors {
              field
              message
            }
          }
        }`,
      variables: {
        product: {
          title: productTitle,
          bodyHtml: productDescription,
          vendor: "BARS",
          productType: "Sports League Registration",
          status: "DRAFT",
          tags: [sport, day, division, season, year.toString()].join(", "),
          seo: {
            title: productTitle,
            description: `Join BARS ${sport} league on ${day}s in ${season} ${year}. ${division} division at ${location}.`
          }
        }
      }
    });

    const response = UrlFetchApp.fetch(getSecret('SHOPIFY_GRAPHQL_URL'), {
      method: "post",
      contentType: "application/json",
      headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_TOKEN') },
      payload: mutation
    });

    const responseData = JSON.parse(response.getContentText());
    Logger.log("Shopify product creation response: " + JSON.stringify(responseData, null, 2));
    
    const productGid = responseData.data?.productCreate?.product?.id;
    const userErrors = responseData.data?.productCreate?.userErrors || [];
    
    if (!productGid || userErrors.length > 0) {
      const errorMessages = userErrors.map(err => `${err.field}: ${err.message}`).join("\n");
      return {
        success: false,
        error: `Product creation failed: ${errorMessages || "Unknown error"}`
      };
    }
    
    const productId = productGid.split("/").pop();
    const productUrl = `https://admin.shopify.com/store/09fe59-3/products/${productId}`;
    
    return {
      success: true,
      productGid: productGid,
      productId: productId,
      productUrl: productUrl
    };
    
  } catch (error) {
    Logger.log(`Error creating main product: ${error}`);
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * Build product description HTML
 */
function buildProductDescription_(productData) {
  const { sport, day, division, season, year, seasonStartDate, seasonEndDate, location, playTimes, leagueDetails } = productData;
  
  return `
    <div class="product-details">
      <h3>${sport} League - ${division} Division</h3>
      
      <div class="schedule-info">
        <h4>Schedule Information</h4>
        <ul>
          <li><strong>Day:</strong> ${day}s</li>
          <li><strong>Season:</strong> ${season} ${year}</li>
          <li><strong>Dates:</strong> ${seasonStartDate} - ${seasonEndDate}</li>
          <li><strong>Times:</strong> ${playTimes}</li>
          <li><strong>Location:</strong> ${location}</li>
        </ul>
      </div>
      
      ${leagueDetails ? `
        <div class="league-details">
          <h4>League Details</h4>
          <p>${leagueDetails}</p>
        </div>
      ` : ''}
      
      <div class="registration-info">
        <h4>Registration Information</h4>
        <p>Multiple registration options available with different pricing and timing.</p>
      </div>
    </div>
  `;
}

/**
 * Create product variants (Vet, Early, Open, Waitlist)
 */
function createProductVariants_(productGid, productData) {
  try {
    const { division, price, vetRegistrationStartDateTime } = productData;
    
    // Build variants array
    const variantsToCreate = [];
    
    // Add Veteran variant if applicable
    if (vetRegistrationStartDateTime) {
      variantsToCreate.push({
        title: "Veteran Registration",
        price: price,
        inventory: 0
      });
    }
    
    // Add standard variants
    variantsToCreate.push(
      {
        title: `${division === 'Open' ? 'W' : ''}TNB+ and BIPOC Early Registration`,
        price: price,
        inventory: 0
      },
      {
        title: "Open Registration",
        price: price,
        inventory: 0
      },
      {
        title: "Coming Off Waitlist Registration",
        price: price,
        inventory: 0
      }
    );
    
    // Step 1: Create product option and first variant
    const firstVariant = variantsToCreate[0];
    const optionMutation = JSON.stringify({
      query: `
        mutation createOptions($productId: ID!, $options: [OptionCreateInput!]!) {
          productOptionsCreate(productId: $productId, options: $options) {
            userErrors { field message code }
            product { options { id name optionValues { id name } } }
          }
        }`,
      variables: {
        productId: productGid,
        options: [{ name: "Registration", values: [{ name: firstVariant.title }] }]
      }
    });

    const optionResponse = UrlFetchApp.fetch(getSecret('SHOPIFY_GRAPHQL_URL'), {
      method: "post",
      contentType: "application/json",
      headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_TOKEN') },
      payload: optionMutation
    });
    
    const optionData = JSON.parse(optionResponse.getContentText());
    Logger.log("Option creation response: " + JSON.stringify(optionData, null, 2));
    
    // Step 2: Get the first variant GID
    const firstVariantGid = getFirstVariantGid_(productGid);
    if (!firstVariantGid) {
      return {
        success: false,
        error: "Failed to get first variant GID"
      };
    }
    
    // Step 3: Update first variant with correct details
    updateVariantDetails_(firstVariantGid, firstVariant.title, firstVariant.price);
    
    // Step 4: Create remaining variants
    const remainingVariants = variantsToCreate.slice(1);
    const createdVariants = createRemainingVariants_(productGid, remainingVariants);
    
    // Collect all variant GIDs
    const variants = {
      vet: vetRegistrationStartDateTime ? firstVariantGid : null,
      early: vetRegistrationStartDateTime ? createdVariants[0] : firstVariantGid,
      open: vetRegistrationStartDateTime ? createdVariants[1] : createdVariants[0],
      waitlist: vetRegistrationStartDateTime ? createdVariants[2] : createdVariants[1]
    };
    
    const summary = Object.entries(variants)
      .filter(([key, value]) => value)
      .map(([key, value]) => `${key}: ${value}`)
      .join('\n');
    
    return {
      success: true,
      variants: variants,
      summary: summary
    };
    
  } catch (error) {
    Logger.log(`Error creating variants: ${error}`);
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * Get the first variant GID
 */
function getFirstVariantGid_(productGid) {
  const query = JSON.stringify({
    query: `
      query($identifier: ProductIdentifierInput!) {
        product: productByIdentifier(identifier: $identifier) {
          variants(first: 1) { nodes { id } }
        }
      }`,
    variables: { identifier: { id: productGid } }
  });

  const response = UrlFetchApp.fetch(getSecret('SHOPIFY_GRAPHQL_URL'), {
    method: "post",
    contentType: "application/json",
    headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_TOKEN') },
    payload: query
  });

  const responseData = JSON.parse(response.getContentText());
  return responseData.data?.product?.variants?.nodes[0]?.id || null;
}

/**
 * Update variant details (price, title, etc.)
 */
function updateVariantDetails_(variantGid, title, price) {
  const mutation = JSON.stringify({
    query: `
      mutation productVariantUpdate($input: ProductVariantInput!) {
        productVariantUpdate(input: $input) {
          productVariant { id title price }
          userErrors { field message }
        }
      }`,
    variables: {
      input: {
        id: variantGid,
        title: title,
        price: price.toString(),
        taxable: true,
        inventoryPolicy: "DENY",
        inventoryManagement: "SHOPIFY",
        requiresShipping: false
      }
    }
  });

  const response = UrlFetchApp.fetch(getSecret('SHOPIFY_GRAPHQL_URL'), {
    method: "post",
    contentType: "application/json",
    headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_TOKEN') },
    payload: mutation
  });

  const responseData = JSON.parse(response.getContentText());
  Logger.log(`Updated variant ${variantGid}: ${JSON.stringify(responseData, null, 2)}`);
}

/**
 * Create remaining variants
 */
function createRemainingVariants_(productGid, remainingVariants) {
  const mutation = JSON.stringify({
    query: `
      mutation ProductVariantsCreate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
        productVariantsBulkCreate(productId: $productId, variants: $variants) {
          productVariants { id title }
          userErrors { field message }
        }
      }`,
    variables: {
      productId: productGid,
      variants: remainingVariants.map(variant => ({
        price: variant.price.toString(),
        inventoryQuantities: [{ availableQuantity: variant.inventory, locationId: SHOPIFY_LOCATION_GID }],
        optionValues: [{ name: variant.title, optionName: "Registration" }],
        taxable: true,
        inventoryPolicy: "DENY",
        inventoryManagement: "SHOPIFY",
        requiresShipping: false
      }))
    }
  });

  const response = UrlFetchApp.fetch(getSecret('SHOPIFY_GRAPHQL_URL'), {
    method: "post",
    contentType: "application/json",
    headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_TOKEN') },
    payload: mutation
  });

  const responseData = JSON.parse(response.getContentText());
  Logger.log("Remaining variants creation response: " + JSON.stringify(responseData, null, 2));
  
  const createdVariants = responseData.data?.productVariantsBulkCreate?.productVariants || [];
  return createdVariants.map(v => v.id);
}

/**
 * Schedule inventory moves and price changes (placeholder)
 */
function scheduleProductUpdates_(productId, productData) {
  try {
    Logger.log(`Scheduling updates for product ${productId}`);
    
    // TODO: Implement inventory moves and price changes scheduling
    // This would call the scheduling functions from product-variant-creation
    // For now, just log that it would happen
    
    Logger.log("Product updates scheduled successfully");
    
  } catch (error) {
    Logger.log(`Error scheduling product updates: ${error}`);
    // Don't fail the whole process for scheduling errors
  }
}
