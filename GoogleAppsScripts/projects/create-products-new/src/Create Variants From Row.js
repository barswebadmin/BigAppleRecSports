const shopifyLocationGid = "gid://shopify/Location/61802217566";

function createVariantsFromRow(rowObject) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const {
    rowNumber,
    totalInventory,
    price,
    division,
    vetRegistrationStartDateTime,
    tnbWtnbRegistrationStartDateTime,
    bipocRegistrationStartDateTime,
    earlyRegistrationStartDateTime, // Backward compatibility
    openRegistrationStartDateTime
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
  // Only create variants that have a startDateTime (except waitlist - always created)
  const variantsToCreate = [];

  // Helper function to check if a date object has a valid raw value
  const hasValidDate = (dateObj) => {
    if (!dateObj) return false;
    const rawValue = typeof dateObj === 'object' && dateObj.raw !== undefined ? dateObj.raw : dateObj;
    return rawValue && String(rawValue).trim() !== '';
  };

  // Check if vet registration has a valid date
  if (hasValidDate(vetRegistrationStartDateTime)) {
    Logger.log("✅ Including Veteran Registration variant.");
    variantsToCreate.push({
      title: "Veteran Registration",
      price,
      inventory: 0
    });
  } else {
    Logger.log("⏭️ Skipping Veteran Registration variant (no startDateTime).");
  }

  // Check TNB/WTNB and BIPOC registration dates
  const hasTnbWtnb = hasValidDate(tnbWtnbRegistrationStartDateTime);
  const hasBipoc = hasValidDate(bipocRegistrationStartDateTime);
  
  // Helper to compare dates (handles both date objects and raw values)
  const datesEqual = (date1, date2) => {
    if (!date1 || !date2) return false;
    const raw1 = typeof date1 === 'object' && date1.raw !== undefined ? date1.raw : date1;
    const raw2 = typeof date2 === 'object' && date2.raw !== undefined ? date2.raw : date2;
    if (!raw1 || !raw2) return false;
    return new Date(raw1).getTime() === new Date(raw2).getTime();
  };
  
  if (hasTnbWtnb && hasBipoc && datesEqual(tnbWtnbRegistrationStartDateTime, bipocRegistrationStartDateTime)) {
    // Same date - create combined variant
    Logger.log("✅ Including combined TNB+ and BIPOC Early Registration variant.");
    variantsToCreate.push({
      title: `${division === 'Open' ? 'W' : ''}TNB+ and BIPOC Early Registration`,
      price,
      inventory: 0,
      type: 'early'
    });
  } else {
    // Different dates or only one present - create separate variants
    if (hasTnbWtnb) {
      Logger.log("✅ Including TNB/WTNB Early Registration variant.");
      variantsToCreate.push({
        title: `${division === 'Open' ? 'W' : ''}TNB+ Early Registration`,
        price,
        inventory: 0,
        type: 'wtnb'
      });
    }
    if (hasBipoc) {
      Logger.log("✅ Including BIPOC Early Registration variant.");
      variantsToCreate.push({
        title: "BIPOC Early Registration",
        price,
        inventory: 0,
        type: 'bipoc'
      });
    }
    // Backward compatibility: if old earlyRegistrationStartDateTime exists but new columns don't
    if (!hasTnbWtnb && !hasBipoc && hasValidDate(earlyRegistrationStartDateTime)) {
      Logger.log("✅ Including Early Registration variant (backward compatibility).");
      variantsToCreate.push({
        title: `${division === 'Open' ? 'W' : ''}TNB+ and BIPOC Early Registration`,
        price,
        inventory: 0,
        type: 'early'
      });
    }
  }

  // Check open registration date
  if (hasValidDate(openRegistrationStartDateTime)) {
    Logger.log("✅ Including Open Registration variant.");
    variantsToCreate.push({
      title: "Open Registration",
      price,
      inventory: 0
    });
  } else {
    Logger.log("⏭️ Skipping Open Registration variant (no startDateTime).");
  }

  // Waitlist is always created
  Logger.log("✅ Including Waitlist variant (always created).");
  variantsToCreate.push({
    title: "Coming Off Waitlist Registration",
    price,
    inventory: 0
  });

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
  const firstVariantType = variantsToCreate[0].type || '';
  const columns = {
    "Veteran Registration": sheetHeaders.indexOf("Vet Registration Variant ID") + 1,
    "TNB/WTNB": sheetHeaders.indexOf("TNB/WTNB Registration Variant ID") + 1,
    "BIPOC": sheetHeaders.indexOf("BIPOC Registration Variant ID (if different)") + 1,
    "Early": sheetHeaders.indexOf("Early Registration Variant ID") + 1, // Backward compatibility
    "Open": sheetHeaders.indexOf("Open Registration Variant ID") + 1,
    "Waitlist": sheetHeaders.indexOf("Coming Off Waitlist Registration Variant ID") + 1
  };

  // Store first variant GID based on type or title
  if (firstVariantTitle.includes("Veteran")) {
    sheet.getRange(rowNumber, columns["Veteran Registration"]).setValue(firstVariantGid);
  } else if (firstVariantType === 'wtnb' || firstVariantTitle.includes("TNB+") && !firstVariantTitle.includes("BIPOC")) {
    sheet.getRange(rowNumber, columns["TNB/WTNB"]).setValue(firstVariantGid);
  } else if (firstVariantType === 'bipoc' || firstVariantTitle.includes("BIPOC")) {
    sheet.getRange(rowNumber, columns["BIPOC"]).setValue(firstVariantGid);
  } else if (firstVariantTitle.includes("Early") || firstVariantType === 'early') {
    // Combined early variant - store in both columns if they exist
    if (columns["TNB/WTNB"] > 0) sheet.getRange(rowNumber, columns["TNB/WTNB"]).setValue(firstVariantGid);
    if (columns["BIPOC"] > 0) sheet.getRange(rowNumber, columns["BIPOC"]).setValue(firstVariantGid);
    // Also store in old column for backward compatibility
    if (columns["Early"] > 0) sheet.getRange(rowNumber, columns["Early"]).setValue(firstVariantGid);
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

  createdVariants.forEach((variant, index) => {
    // Get the variant type from the original variantsToCreate array (index + 1 because first was already handled)
    const variantInfo = variantsToCreate[index + 1];
    const variantType = variantInfo ? variantInfo.type : '';
    
    if (variant.title.includes("Veteran")) {
      if (columns["Veteran Registration"] > 0) {
        sheet.getRange(rowObject.rowNumber, columns["Veteran Registration"]).setValue(variant.id);
      }
    } else if (variantType === 'wtnb' || (variant.title.includes("TNB+") && !variant.title.includes("BIPOC"))) {
      if (columns["TNB/WTNB"] > 0) {
        sheet.getRange(rowObject.rowNumber, columns["TNB/WTNB"]).setValue(variant.id);
      }
    } else if (variantType === 'bipoc' || variant.title.includes("BIPOC")) {
      if (columns["BIPOC"] > 0) {
        sheet.getRange(rowObject.rowNumber, columns["BIPOC"]).setValue(variant.id);
      }
    } else if (variant.title.includes("Early") || variantType === 'early') {
      // Combined early variant - store in both new columns if they exist
      if (columns["TNB/WTNB"] > 0) sheet.getRange(rowObject.rowNumber, columns["TNB/WTNB"]).setValue(variant.id);
      if (columns["BIPOC"] > 0) sheet.getRange(rowObject.rowNumber, columns["BIPOC"]).setValue(variant.id);
      // Also store in old column for backward compatibility
      if (columns["Early"] > 0) sheet.getRange(rowObject.rowNumber, columns["Early"]).setValue(variant.id);
    } else if (variant.title.includes("Open")) {
      if (columns["Open"] > 0) {
        sheet.getRange(rowObject.rowNumber, columns["Open"]).setValue(variant.id);
      }
    } else if (variant.title.includes("Waitlist")) {
      if (columns["Waitlist"] > 0) {
        sheet.getRange(rowObject.rowNumber, columns["Waitlist"]).setValue(variant.id);
      }
    }
  });

  SpreadsheetApp.getUi().alert("✅ Product and Variants created successfully!");

  // Schedule inventory moves (add all inventory at scheduled dates)
  scheduleInventoryMoves(rowNumber);
  
  // Schedule price changes (update prices at scheduled dates)
  schedulePriceChanges(rowNumber);
  
  // Prompt user to schedule go-live inventory (partial inventory release at first registration)
  scheduleGoLiveInventoryFromRow(rowNumber);
  
}

