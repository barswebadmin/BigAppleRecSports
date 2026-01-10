// Global configuration constant for API destination
const API_DESTINATION = 'AWS'; // Change to 'AWS' for production

const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
const data = sheet.getDataRange().getValues();
const sheetHeaders = data[0];

const ui = SpreadsheetApp.getUi();

function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu("🛍️ BARS Product Creation")
    .addItem("🏗️ Create Product", "createProduct")
    .addItem("🎯 Create Variants and Schedule Changes", "createVariants")
    .addItem("📦 Update Scheduled Inventory Movements", "scheduleInventoryMoves")
    .addItem("💰 Update Scheduled Price Adjustments", "schedulePriceChanges")
    .addItem("🔧 Create Manual Inventory Moves", "createManualScheduledInventoryMoves")
    .addSeparator()
    .addItem("🚀 Schedule/Update Product Go-Live", "scheduleGoLiveInventoryFromRow")
    .addSeparator()
    .addItem("📋 Create Metadata Fields for Product", "createMetadataFieldsForProduct")
    .addItem("📢 Publish Product to Online Store", "publishProductManually")
    .addSeparator()
    .addItem("📘 View Instructions", "showInstructions")
    .addToUi();
    
  // Show instructions on first open
  showInstructions();
}

// ✅ Parses a given row into a key-value object based on column headers
let rowObject = {}

function parseRowData(row, rowIndex) {
  Logger.log(`row: ${JSON.stringify(row)}`)
  Logger.log(`rowIndex: ${rowIndex}`)
  const rowObj = { rowNumber: Number.parseInt(rowIndex)};

  const headerMapping = {
    "sport": "sport",
    "day": "day",
    "sport sub-category": "sportSubCategory",
    "division": "division",
    "season": "season",
    "year": "year",
    "social or advanced": "socialOrAdvanced",
    "type(s)": "types",
    "new player orientation date/time": "newPlayerOrientationDateTime",
    "scout night date/time": "scoutNightDateTime",
    "opening party date": "openingPartyDate",
    "season start date": "seasonStartDate",
    "season end date": "seasonEndDate",
    "alternative start time\n(optional)": "alternativeStartTime",
    "alternative end time\n(optional)": "alternativeEndTime",
    "off dates, separated by comma (leave blank if none)\n\nmake sure this is in the format m/d/yy": "offDatesCommaSeparated",
    "rain date": "rainDate",
    "closing party date": "closingPartyDate",
    "sport start time": "sportStartTime",
    "sport end time": "sportEndTime",
    "location": "location",
    "price": "price",
    "veteran registration start date/time\n(leave blank if no vet registration applies for this season)": "vetRegistrationStartDateTime",
    "tnb/wtnb registration start date/time": "tnbWtnbRegistrationStartDateTime",
    "bipoc registration start date/time (set to the same date/time as tnb/wtnb unless splitting the reg periods)": "bipocRegistrationStartDateTime",
    "early registration start date/time": "earlyRegistrationStartDateTime", // Backward compatibility
    "open registration start date/time": "openRegistrationStartDateTime",
    "total inventory": "totalInventory",
  };

  Logger.log(`headers: [${sheetHeaders.join(', ')}]`)
  sheetHeaders.forEach((header, i) => {
    const key = header.toLowerCase().trim(); // Normalize header text
    if (headerMapping[key]) {
      rowObj[headerMapping[key]] = row[i]; // Assign value dynamically
    }
  });

  return rowObj; // Return the parsed row object
}

function createProduct() {
  try {
    Logger.log("🚀 Starting createProduct function");
    
    const readyToCreateColIndex = sheetHeaders.findIndex(col => col.toLowerCase().includes("ready to create product"));
  
  if (readyToCreateColIndex === -1) {
    SpreadsheetApp.getUi().alert("⚠️ 'Ready to Create?' column not found!");
    return;
  }

  let validRows = [];
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    if (!!row[readyToCreateColIndex] && !row[readyToCreateColIndex+1]) validRows.push({ rowIndex: i + 1, rowData: row });
  }
  

  const [sportColIdx, dayColIdx, divisionColIdx, seasonColIdx, yearColIdx] = [sheetHeaders.indexOf('Sport'), sheetHeaders.indexOf('Day'), sheetHeaders.indexOf('Division'), sheetHeaders.indexOf('Season'), sheetHeaders.indexOf('Year')]

  const options = validRows.map(rowObj => 
    `Row ${rowObj.rowIndex}: ${rowObj.rowData[sportColIdx]} - ${rowObj.rowData[dayColIdx]} - ${rowObj.rowData[divisionColIdx]} - ${rowObj.rowData[seasonColIdx]} ${rowObj.rowData[yearColIdx]}`
  );

  if (options.length === 0) {
    SpreadsheetApp.getUi().alert("No rows/products ready for creation.");
    return;
  }

  const rowInput = ui.prompt(
    "Enter the row number to create a product. Rows available for creation: \n" + options.join(`\n`),
    ui.ButtonSet.OK_CANCEL
  )

  const selectedButton = rowInput.getSelectedButton();
  const selectedRow = rowInput.getResponseText().trim();

  if (selectedButton === ui.Button.CANCEL || selectedButton === ui.Button.CLOSE || !selectedButton) {
    SpreadsheetApp.getUi().alert("Operation canceled.");
    return;
  }

  if (selectedButton == ui.Button.OK && !selectedRow || isNaN(selectedRow)) {
    SpreadsheetApp.getUi().alert("❌ Invalid selection.");
    return;
  }

  

  rowObject = parseRowData(data[selectedRow - 1], selectedRow);

  rowObject.year = parseInt(rowObject["year"]);
  rowObject.price = parseInt(rowObject["price"])
  rowObject.totalInventory = parseInt(rowObject["totalInventory"])
  rowObject.newPlayerOrientationDateTime = {raw: rowObject['newPlayerOrientationDateTime'], formatted: formatDateAndTime(rowObject["newPlayerOrientationDateTime"])};
  rowObject.scoutNightDateTime = {raw: rowObject['scoutNightDateTime'], formatted: formatDateAndTime(rowObject["scoutNightDateTime"])};
  rowObject.openingPartyDate = {raw: rowObject['openingPartyDate'], formatted: formatDateOnly(rowObject["openingPartyDate"])};
  rowObject.seasonStartDate = {raw: rowObject['seasonStartDate'], formatted: formatDateOnly(rowObject["seasonStartDate"])};
  rowObject.seasonEndDate = {raw: rowObject['seasonEndDate'], formatted: formatDateOnly(rowObject["seasonEndDate"])};
  rowObject.closingPartyDate = {raw: rowObject['closingPartyDate'], formatted: formatDateOnly(rowObject["closingPartyDate"])};
  rowObject.rainDate = {raw: rowObject['rainDate'], formatted: formatDateOnly(rowObject["rainDate"])};

  const offDatesArray = rowObject.offDatesCommaSeparated
    ? rowObject.offDatesCommaSeparated.split(",").filter(s => s.trim() !== "")
    : [];
  if (!!rowObject.offDatesCommaSeparated) {

    rowObject.offDatesCommaSeparated = offDatesArray
      .map(formatDateOnly)
      .join(", ");
  }

  rowObject.sportStartTime = {raw: rowObject['sportStartTime'], formatted: formatTimeOnly(rowObject["sportStartTime"])};
  rowObject.sportEndTime = {raw: rowObject['sportEndTime'], formatted: formatTimeOnly(rowObject["sportEndTime"])};
  rowObject.alternativeStartTime = {raw: rowObject['alternativeStartTime'], formatted: formatTimeOnly(rowObject["alternativeStartTime"])};
  rowObject.alternativeEndTime = {raw: rowObject['alternativeEndTime'], formatted: formatTimeOnly(rowObject["alternativeEndTime"])};
  rowObject.vetRegistrationStartDateTime = {raw: rowObject['vetRegistrationStartDateTime'], formatted: formatDateAndTime(rowObject["vetRegistrationStartDateTime"])};
  rowObject.tnbWtnbRegistrationStartDateTime = {raw: rowObject['tnbWtnbRegistrationStartDateTime'], formatted: formatDateAndTime(rowObject["tnbWtnbRegistrationStartDateTime"])};
  rowObject.bipocRegistrationStartDateTime = {raw: rowObject['bipocRegistrationStartDateTime'], formatted: formatDateAndTime(rowObject["bipocRegistrationStartDateTime"])};
  // Backward compatibility: derive earlyRegistrationStartDateTime from TNB/WTNB if not explicitly set
  if (!rowObject['earlyRegistrationStartDateTime'] && rowObject['tnbWtnbRegistrationStartDateTime']) {
    rowObject.earlyRegistrationStartDateTime = rowObject.tnbWtnbRegistrationStartDateTime;
  } else {
    rowObject.earlyRegistrationStartDateTime = {raw: rowObject['earlyRegistrationStartDateTime'], formatted: formatDateAndTime(rowObject["earlyRegistrationStartDateTime"])};
  }
  rowObject.openRegistrationStartDateTime = {raw: rowObject['openRegistrationStartDateTime'], formatted: formatDateAndTime(rowObject["openRegistrationStartDateTime"])};

  const numOfWeeks = Math.round(
    (new Date(rowObject.seasonEndDate.raw) - new Date(rowObject.seasonStartDate.raw)) / (1000 * 60 * 60 * 24 * 7) + 1
  );
  const numOfWeeksAdjusted = numOfWeeks - offDatesArray.length
  rowObject.numOfWeeks = numOfWeeksAdjusted

  Logger.log("📞 Calling createProductFromRow with processed data");
  createProductFromRow(rowObject);
  Logger.log("✅ createProduct function completed successfully");
  
  } catch (error) {
    Logger.log(`❌ Error in createProduct: ${error.toString()}`);
    Logger.log(`❌ Stack trace: ${error.stack}`);
    SpreadsheetApp.getUi().alert(`❌ Error creating product: ${error.message}\n\nCheck the logs for details.`);
  }
}

function createVariants() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const data = sheet.getDataRange().getValues();
  const sheetHeaders = data[0];

  const readyToCreateVariantsColIndex = sheetHeaders.findIndex(col => col.toLowerCase().includes("ready to create variants"));
  
  if (readyToCreateVariantsColIndex === -1) {
    SpreadsheetApp.getUi().alert("⚠️ 'Ready to Create Variants?' column not found!");
    return;
  }

  let validRows = [];
  for (let i = 1; i < data.length; i++) {
    const row = data[i];

    if (!!row[readyToCreateVariantsColIndex] && !row[readyToCreateVariantsColIndex+2]) validRows.push({ rowIndex: i + 1, rowData: row });
  }

  const [sportColIdx, dayColIdx, divisionColIdx, seasonColIdx, yearColIdx] = [sheetHeaders.indexOf('Sport'), sheetHeaders.indexOf('Day'), sheetHeaders.indexOf('Division'), sheetHeaders.indexOf('Season'), sheetHeaders.indexOf('Year')]

  const options = validRows.map(rowObj => 
    `Row ${rowObj.rowIndex}: ${rowObj.rowData[sportColIdx]} - ${rowObj.rowData[dayColIdx]} - ${rowObj.rowData[divisionColIdx]} - ${rowObj.rowData[seasonColIdx]} ${rowObj.rowData[yearColIdx]}`
  ).join("\n");

  if (options.length === 0) {
    SpreadsheetApp.getUi().alert("No products ready for variant creation.");
    return;
  }

  // ✅ Prompt user to select a row number
  const rowInput = ui.prompt(
    "Enter the row number to create variants for that product. Rows available for creation: \n" + options,
    ui.ButtonSet.OK_CANCEL
  )

  const selectedButton = rowInput.getSelectedButton();
  const selectedRow = rowInput.getResponseText().trim();

  if (selectedButton === ui.Button.CANCEL || selectedButton === ui.Button.CLOSE || !selectedButton) {
    SpreadsheetApp.getUi().alert("Operation canceled.");
    return;
  }

  if (selectedButton == ui.Button.OK && !selectedRow || isNaN(selectedRow)) {
    SpreadsheetApp.getUi().alert("❌ Invalid selection.");
    return;
  }

  rowObject = parseRowData(data[selectedRow - 1], selectedRow);
  createVariantsFromRow(rowObject, sheetHeaders, selectedRow);
}

function createMetadataFieldsForProduct() {
  try {
    Logger.log("🚀 Starting createMetadataFieldsForProduct function");
    
    // Column AB is index 27 (A=0, B=1, ..., AB=27)
    const productUrlColIndex = 27;
    
    // Find rows with non-empty product URL (reusing pattern from createProduct)
    let validRows = [];
    for (let i = 1; i < data.length; i++) {
      const row = data[i];
      const productUrl = row[productUrlColIndex];
      if (productUrl && productUrl.toString().trim() !== '') {
        validRows.push({ rowIndex: i + 1, rowData: row });
      }
    }
    
    if (validRows.length === 0) {
      SpreadsheetApp.getUi().alert("No rows found with a product URL in column AB.");
      return;
    }
    
    // Show available rows (reusing pattern from createProduct)
    const [sportColIdx, dayColIdx, divisionColIdx, seasonColIdx, yearColIdx] = [
      sheetHeaders.indexOf('Sport'),
      sheetHeaders.indexOf('Day'),
      sheetHeaders.indexOf('Division'),
      sheetHeaders.indexOf('Season'),
      sheetHeaders.indexOf('Year')
    ];
    
    const options = validRows.map(rowObj => 
      `Row ${rowObj.rowIndex}: ${rowObj.rowData[sportColIdx]} - ${rowObj.rowData[dayColIdx]} - ${rowObj.rowData[divisionColIdx]} - ${rowObj.rowData[seasonColIdx]} ${rowObj.rowData[yearColIdx]}`
    );
    
    const rowInput = ui.prompt(
      "Enter the row number to create metadata fields. Rows with product URLs: \n" + options.join(`\n`),
      ui.ButtonSet.OK_CANCEL
    );
    
    const selectedButton = rowInput.getSelectedButton();
    const selectedRow = rowInput.getResponseText().trim();
    
    if (selectedButton === ui.Button.CANCEL || selectedButton === ui.Button.CLOSE || !selectedButton) {
      SpreadsheetApp.getUi().alert("Operation canceled.");
      return;
    }
    
    if (selectedButton == ui.Button.OK && !selectedRow || isNaN(selectedRow)) {
      SpreadsheetApp.getUi().alert("❌ Invalid selection.");
      return;
    }
    
    const rowNumber = parseInt(selectedRow);
    const rowData = data[rowNumber - 1];
    const productUrl = rowData[productUrlColIndex];
    
    if (!productUrl || productUrl.toString().trim() === '') {
      SpreadsheetApp.getUi().alert("❌ Selected row does not have a product URL in column AB.");
      return;
    }
    
    // Extract product ID from URL (reusing pattern from Create Product From Row.js)
    const productIdMatch = productUrl.toString().match(/products\/(\d+)/);
    if (!productIdMatch) {
      SpreadsheetApp.getUi().alert("❌ Could not extract product ID from URL: " + productUrl);
      return;
    }
    
    const productIdDigitsOnly = productIdMatch[1];
    const productGid = `gid://shopify/Product/${productIdDigitsOnly}`;
    
    // Use existing parseRowData function to get row data
    rowObject = parseRowData(rowData, rowNumber);
    
    // Filter out empty values from parsed row data
    // Convert Date objects to UTC ISO strings, otherwise use raw string values
    const metadata = {};
    for (const key in rowObject) {
      if (key !== 'rowNumber') { // Exclude rowNumber from metadata
        const value = rowObject[key];
        if (value !== null && value !== undefined) {
          // Convert Date objects to UTC ISO string
          if (value instanceof Date) {
            metadata[key] = value.toISOString();
          } else {
            const stringValue = value.toString().trim();
            if (stringValue !== '') {
              metadata[key] = stringValue;
            }
          }
        }
      }
    }
    
    if (Object.keys(metadata).length === 0) {
      SpreadsheetApp.getUi().alert("❌ No metadata fields found with values to attach.");
      return;
    }
    
    Logger.log(`📋 Metadata to attach: ${JSON.stringify(metadata, null, 2)}`);
    
    // Create a single JSON metafield containing all metadata
    const metafield = {
      namespace: "custom",
      key: "product_metadata",
      value: JSON.stringify(metadata),
      type: "json",
      ownerId: productGid
    };
    
    // Use existing Shopify API call pattern (reusing from Create Product From Row.js)
    const mutation = {
      query: `
        mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
          metafieldsSet(metafields: $metafields) {
            metafields {
              id
              namespace
              key
              value
            }
            userErrors {
              field
              message
            }
          }
        }
      `,
      variables: {
        metafields: [metafield]
      }
    };
    
    const response = UrlFetchApp.fetch(getSecret('SHOPIFY_GRAPHQL_URL'), {
      method: "POST",
      contentType: "application/json",
      headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_TOKEN') },
      payload: JSON.stringify(mutation),
      muteHttpExceptions: true
    });
    
    const responseData = JSON.parse(response.getContentText());
    Logger.log(`📥 Shopify Response: ${JSON.stringify(responseData, null, 2)}`);
    
    const userErrors = responseData.data?.metafieldsSet?.userErrors || [];
    const metafieldsCreated = responseData.data?.metafieldsSet?.metafields || [];
    
    if (userErrors.length > 0) {
      const errorMessages = userErrors.map(e => `${e.field}: ${e.message}`).join('\n');
      SpreadsheetApp.getUi().alert(`❌ Error creating metafields:\n${errorMessages}`);
      return;
    }
    
    if (metafieldsCreated.length > 0) {
      SpreadsheetApp.getUi().alert(`✅ Successfully created metadata field for product ${productIdDigitsOnly}\n\nFields attached: ${Object.keys(metadata).join(', ')}`);
    } else {
      SpreadsheetApp.getUi().alert("⚠️ No metafields were created. Check logs for details.");
    }
    
    Logger.log("✅ createMetadataFieldsForProduct function completed successfully");
    
  } catch (error) {
    Logger.log(`❌ Error in createMetadataFieldsForProduct: ${error.toString()}`);
    Logger.log(`❌ Stack trace: ${error.stack}`);
    SpreadsheetApp.getUi().alert(`❌ Error creating metadata fields: ${error.message}\n\nCheck the logs for details.`);
  }
}

function publishProductManually() {
  try {
    Logger.log("🚀 Starting publishProductManually function");
    
    // Column AB is index 27 (A=0, B=1, ..., AB=27)
    const productUrlColIndex = 27;
    
    // Find rows with non-empty product URL (reusing pattern from createMetadataFieldsForProduct)
    let validRows = [];
    for (let i = 1; i < data.length; i++) {
      const row = data[i];
      const productUrl = row[productUrlColIndex];
      if (productUrl && productUrl.toString().trim() !== '') {
        validRows.push({ rowIndex: i + 1, rowData: row });
      }
    }
    
    if (validRows.length === 0) {
      SpreadsheetApp.getUi().alert("No rows found with a product URL in column AB.");
      return;
    }
    
    // Show available rows
    const [sportColIdx, dayColIdx, divisionColIdx, seasonColIdx, yearColIdx] = [
      sheetHeaders.indexOf('Sport'),
      sheetHeaders.indexOf('Day'),
      sheetHeaders.indexOf('Division'),
      sheetHeaders.indexOf('Season'),
      sheetHeaders.indexOf('Year')
    ];
    
    const options = validRows.map(rowObj => 
      `Row ${rowObj.rowIndex}: ${rowObj.rowData[sportColIdx]} - ${rowObj.rowData[dayColIdx]} - ${rowObj.rowData[divisionColIdx]} - ${rowObj.rowData[seasonColIdx]} ${rowObj.rowData[yearColIdx]}`
    );
    
    const rowInput = ui.prompt(
      "Enter the row number to publish product. Rows with product URLs: \n" + options.join(`\n`),
      ui.ButtonSet.OK_CANCEL
    );
    
    const selectedButton = rowInput.getSelectedButton();
    const selectedRow = rowInput.getResponseText().trim();
    
    if (selectedButton === ui.Button.CANCEL || selectedButton === ui.Button.CLOSE || !selectedButton) {
      SpreadsheetApp.getUi().alert("Operation canceled.");
      return;
    }
    
    if (selectedButton == ui.Button.OK && !selectedRow || isNaN(selectedRow)) {
      SpreadsheetApp.getUi().alert("❌ Invalid selection.");
      return;
    }
    
    const rowNumber = parseInt(selectedRow);
    const rowData = data[rowNumber - 1];
    const productUrl = rowData[productUrlColIndex];
    
    if (!productUrl || productUrl.toString().trim() === '') {
      SpreadsheetApp.getUi().alert("❌ Selected row does not have a product URL in column AB.");
      return;
    }
    
    // Extract product ID from URL
    const productIdMatch = productUrl.toString().match(/products\/(\d+)/);
    if (!productIdMatch) {
      SpreadsheetApp.getUi().alert("❌ Could not extract product ID from URL: " + productUrl);
      return;
    }
    
    const productIdDigitsOnly = productIdMatch[1];
    const productGid = `gid://shopify/Product/${productIdDigitsOnly}`;
    
    // Get current UTC datetime in ISO format (matching the curl command)
    const publishDate = new Date().toISOString();
    
    Logger.log(`📢 Publishing product ${productGid} at ${publishDate}`);
    
    // Build GraphQL mutation (matching the curl command that worked)
    const mutation = {
      query: `mutation productPublish($input: ProductPublishInput!) {
        productPublish(input: $input) {
          product {
            id
          }
          userErrors {
            field
            message
          }
        }
      }`,
      variables: {
        input: {
          id: productGid,
          productPublications: [{
            publicationId: 'gid://shopify/Publication/79253667934',
            publishDate: publishDate,
            channelHandle: "online-store"
          }]
        }
      }
    };
    
    // Use existing Shopify API call pattern
    const response = UrlFetchApp.fetch(getSecret('SHOPIFY_GRAPHQL_URL'), {
      method: "POST",
      contentType: "application/json",
      headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_TOKEN') },
      payload: JSON.stringify(mutation),
      muteHttpExceptions: true
    });
    
    const responseData = JSON.parse(response.getContentText());
    Logger.log(`📥 Shopify Response: ${JSON.stringify(responseData, null, 2)}`);
    
    const userErrors = responseData.data?.productPublish?.userErrors || [];
    const product = responseData.data?.productPublish?.product;
    
    if (userErrors.length > 0) {
      const errorMessages = userErrors.map(e => `${e.field}: ${e.message}`).join('\n');
      SpreadsheetApp.getUi().alert(`❌ Error publishing product:\n${errorMessages}`);
      return;
    }
    
    if (product && product.id) {
      SpreadsheetApp.getUi().alert(`✅ Successfully published product ${productIdDigitsOnly} to online store!\n\nPublished at: ${publishDate}`);
    } else {
      SpreadsheetApp.getUi().alert("⚠️ Product publish response received but no product ID returned. Check logs for details.");
    }
    
    Logger.log("✅ publishProductManually function completed successfully");
    
  } catch (error) {
    Logger.log(`❌ Error in publishProductManually: ${error.toString()}`);
    Logger.log(`❌ Stack trace: ${error.stack}`);
    SpreadsheetApp.getUi().alert(`❌ Error publishing product: ${error.message}\n\nCheck the logs for details.`);
  }
}

