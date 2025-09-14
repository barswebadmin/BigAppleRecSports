const shopifyLocationGid = "gid://shopify/Location/61802217566";

function createVariantsFromRow(rowObject) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const {
    rowNumber,
    totalInventory,
    price,
    division,
    vetRegistrationStartDateTime
  } = rowObject;

  const productUrlColIndex = sheetHeaders.indexOf("Product URL") + 1;
  const productUrl = sheet.getRange(rowNumber, productUrlColIndex).getValue();

  if (!productUrl) {
    SpreadsheetApp.getUi().alert("❌ Product URL is missing for this row.");
    return;
  }

  const productIdMatch = productUrl.match(/\/products\/(\d+)$/);
  const productGid = productIdMatch ? `gid://shopify/Product/${productIdMatch[1]}` : null;

  if (!productGid) {
    SpreadsheetApp.getUi().alert("❌ Invalid Product URL. Cannot extract Product ID.");
    return;
  }

  // ✅ Build variants array dynamically
  const variantsToCreate = [];

  if (vetRegistrationStartDateTime) {
    Logger.log("✅ Including Veteran Registration variant.");
    variantsToCreate.push({
      title: "Veteran Registration",
      price,
      inventory: 0
    });
  } else {
    Logger.log("⏭️ Skipping Veteran Registration variant.");
  }

  Logger.log("➕ Adding remaining variants...");
  variantsToCreate.push(
    {
      title: `${division === 'Open' ? 'W' : ''}TNB+ and BIPOC Early Registration`,
      price,
      inventory: 0
    },
    {
      title: "Open Registration",
      price,
      inventory: 0
    },
    {
      title: "Coming Off Waitlist Registration",
      price,
      inventory: 0
    }
  );

  // ✅ Step 1: Create product option and first variant (using productOptionsCreate)
  const createFirstVariant = () => {
    const first = variantsToCreate[0];
    const payload = JSON.stringify({
      query: `
        mutation createOptions($productId: ID!, $options: [OptionCreateInput!]!) {
          productOptionsCreate(productId: $productId, options: $options) {
            userErrors { field message code }
            product { options { id name optionValues { id name } } }
          }
        }`,
      variables: {
        productId: productGid,
        options: [{ name: "Registration", values: [{ name: first.title }] }]
      }
    });

    return UrlFetchApp.fetch(getSecret('SHOPIFY_GRAPHQL_URL'), {
      method: "post",
      contentType: "application/json",
      headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_TOKEN') },
      payload
    });
  };

  createFirstVariant();

  // ✅ Step 2: Get GID of the first variant
  const getFirstVariantGid = () => {
    const payload = JSON.stringify({
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
      payload
    });

    return JSON.parse(response.getContentText()).data?.product?.variants?.nodes[0]?.id || null;
  };

  const firstVariantGid = getFirstVariantGid();

  // ✅ Step 3: Update price and inventory for first variant
  const updateFirstVariant = () => {
    const inventoryQuery = JSON.stringify({
      query: `
        query GetInventoryItemId($variantId: ID!) {
          productVariant(id: $variantId) {
            inventoryItem { id }
          }
        }`,
      variables: { variantId: firstVariantGid }
    });

    const inventoryResponse = UrlFetchApp.fetch(getSecret('SHOPIFY_GRAPHQL_URL'), {
      method: "post",
      contentType: "application/json",
      headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_TOKEN') },
      payload: inventoryQuery
    });

    const inventoryItemId = JSON.parse(inventoryResponse.getContentText()).data?.productVariant?.inventoryItem?.id;

    if (!inventoryItemId) {
      SpreadsheetApp.getUi().alert("❌ Error fetching inventory item ID.");
      return;
    }

    const updatePricePayload = JSON.stringify({
      query: `
        mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
          productVariantsBulkUpdate(productId: $productId, variants: $variants) {
            productVariants { id }
            userErrors { field message }
          }
        }`,
      variables: {
        productId: productGid,
        variants: [{ id: firstVariantGid, price: variantsToCreate[0].price }]
      }
    });

    UrlFetchApp.fetch(getSecret('SHOPIFY_GRAPHQL_URL'), {
      method: "post",
      contentType: "application/json",
      headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_TOKEN') },
      payload: updatePricePayload
    });

    const updateQuantityPayload = JSON.stringify({
      query: `
        mutation inventoryAdjustQuantities($input: InventoryAdjustQuantitiesInput!) {
          inventoryAdjustQuantities(input: $input) {
            userErrors { field message }
          }
        }`,
      variables: {
        input: {
          reason: "movement_created",
          name: "available",
          changes: [{
            delta: variantsToCreate[0].inventory,
            inventoryItemId,
            locationId: shopifyLocationGid
          }]
        }
      }
    });

    UrlFetchApp.fetch(getSecret('SHOPIFY_GRAPHQL_URL'), {
      method: "post",
      contentType: "application/json",
      headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_TOKEN') },
      payload: updateQuantityPayload
    });
  };

  updateFirstVariant();

  const firstVariantTitle = variantsToCreate[0].title;
  const columns = {
    "Veteran Registration": sheetHeaders.indexOf("Vet Registration Variant ID") + 1,
    "Early": sheetHeaders.indexOf("Early Registration Variant ID") + 1,
    "Open": sheetHeaders.indexOf("Open Registration Variant ID") + 1,
    "Waitlist": sheetHeaders.indexOf("Coming Off Waitlist Registration Variant ID") + 1
  };

  if (firstVariantTitle.includes("Veteran")) {
    sheet.getRange(rowNumber, columns["Veteran Registration"]).setValue(firstVariantGid);
  } else if (firstVariantTitle.includes("Early")) {
    sheet.getRange(rowNumber, columns["Early"]).setValue(firstVariantGid);
  } else if (firstVariantTitle.includes("Open")) {
    sheet.getRange(rowNumber, columns["Open"]).setValue(firstVariantGid);
  } else if (firstVariantTitle.includes("Waitlist")) {
    sheet.getRange(rowNumber, columns["Waitlist"]).setValue(firstVariantGid);
  }

  // ✅ Step 4: Create remaining variants
  const createRemainingVariants = () => {
    const remaining = variantsToCreate.slice(1);
    const payload = JSON.stringify({
      query: `
        mutation ProductVariantsCreate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
          productVariantsBulkCreate(productId: $productId, variants: $variants) {
            productVariants { id title }
            userErrors { field message }
          }
        }`,
      variables: {
        productId: productGid,
        variants: remaining.map(variant => ({
          price: variant.price,
          inventoryQuantities: [{ availableQuantity: variant.inventory, locationId: shopifyLocationGid }],
          optionValues: [{ name: variant.title, optionName: "Registration" }]
        }))
      }
    });

    const response = UrlFetchApp.fetch(getSecret('SHOPIFY_GRAPHQL_URL'), {
      method: "post",
      contentType: "application/json",
      headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_TOKEN') },
      payload
    });

    return JSON.parse(response.getContentText()).data?.productVariantsBulkCreate?.productVariants || [];
  };

  const createdVariants = createRemainingVariants();

  createdVariants.forEach(variant => {
    if (variant.title.includes("Veteran")) {
      sheet.getRange(rowObject.rowNumber, columns["Veteran Registration"]).setValue(variant.id);
    }
    if (variant.title.includes("Early")) {
      sheet.getRange(rowObject.rowNumber, columns["Early"]).setValue(variant.id);
    }
    if (variant.title.includes("Open")) {
      sheet.getRange(rowObject.rowNumber, columns["Open"]).setValue(variant.id);
    }
    if (variant.title.includes("Waitlist")) {
      sheet.getRange(rowObject.rowNumber, columns["Waitlist"]).setValue(variant.id);
    }
  });

  SpreadsheetApp.getUi().alert("✅ Product and Variants created successfully!");

  scheduleInventoryMoves(rowNumber);
  schedulePriceChanges(rowNumber)

}
