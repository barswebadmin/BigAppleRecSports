function scheduleInventoryMoves(selectedRow = null) {
  const apiEndpoint = API_DESTINATION === 'AWS' ? getSecret('AWS_CREATE_PRODUCT_ENDPOINT') : 'https://chubby-grapes-trade.loca.lt/products/create';
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const data = sheet.getDataRange().getValues();
  const sheetHeaders = data[0];

  const productUrlColIndex = sheetHeaders.indexOf("Product URL");
  const vetVariantColIndex = sheetHeaders.indexOf("Vet Registration Variant ID");
  const wtnbVariantColIndex = sheetHeaders.indexOf("TNB/WTNB Registration Variant ID");
  const bipocVariantColIndex = sheetHeaders.indexOf("BIPOC Registration Variant ID (if different)");
  const earlyVariantColIndex = sheetHeaders.indexOf("Early Registration Variant ID"); // Backward compatibility
  const openVariantColIndex = sheetHeaders.indexOf("Open Registration Variant ID");
  
  const numTotalInventoryColIndex = sheetHeaders.indexOf("Total Inventory");
  const isInventoryMoveScheduledIndex = sheetHeaders.indexOf("Inventory Moves Scheduled?");

  let validRows = [];
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    // Valid if has open variant and at least one early variant (TNB/WTNB, BIPOC, or old Early)
    const hasEarlyVariant = !!(row[wtnbVariantColIndex] || row[bipocVariantColIndex] || row[earlyVariantColIndex]);
    if (hasEarlyVariant && !!row[openVariantColIndex]) {
      validRows.push({ rowIndex: i + 1, rowData: row });
    }
  }

  if (!selectedRow) {
    const [sportColIdx, dayColIdx, divisionColIdx, seasonColIdx, yearColIdx] = [sheetHeaders.indexOf('Sport'), sheetHeaders.indexOf('Day'), sheetHeaders.indexOf('Division'), sheetHeaders.indexOf('Season'), sheetHeaders.indexOf('Year')]

    const options = validRows.map(rowObj => 
      `Row ${rowObj.rowIndex}: ${rowObj.rowData[sportColIdx]} - ${rowObj.rowData[dayColIdx]} - ${rowObj.rowData[divisionColIdx]} - ${rowObj.rowData[seasonColIdx]} ${rowObj.rowData[yearColIdx]}`
    ).join("\n");

    if (options.length === 0) {
      SpreadsheetApp.getUi().alert("No rows are ready for processing - did you create variants?");
      return;
    }

    const rowInput = ui.prompt(
      "Enter the row number to schedule inventory moves. Rows available for creation: \n" + options,
      ui.ButtonSet.OK_CANCEL
    )

    const selectedButton = rowInput.getSelectedButton();
    selectedRow = rowInput.getResponseText().trim();

    if (selectedButton === ui.Button.CANCEL || selectedButton === ui.Button.CLOSE || !selectedButton) {
      SpreadsheetApp.getUi().alert("Operation canceled.");
      return;
    }

    if (selectedButton == ui.Button.OK && !selectedRow || isNaN(selectedRow)) {
      SpreadsheetApp.getUi().alert("❌ Invalid selection.");
      return;
    }
  }

  rowObject = parseRowData(data[selectedRow - 1], selectedRow);

  const { rowData } = validRows.find(row => row.rowIndex == selectedRow);
  const productUrl = rowData[productUrlColIndex]
  const productIdDigitsOnly = productUrl?.split("/")?.pop();
  
  // Helper to extract GID from sheet cell
  const extractGid = (rawValue) => {
    if (!rawValue) return null;
    const str = String(rawValue).trim();
    return str !== '' ? str : null;
  };
  
  // Extract all variant GIDs
  const vetGid = extractGid(rowData[vetVariantColIndex]);
  const wtnbGid = extractGid(rowData[wtnbVariantColIndex]);
  const bipocGid = extractGid(rowData[bipocVariantColIndex]);
  const earlyGid = extractGid(rowData[earlyVariantColIndex]); // Backward compatibility
  const openGid = extractGid(rowData[openVariantColIndex]);
  const numTotalInventory = rowData[numTotalInventoryColIndex]
  
  const sportSlug = mapSportToAbbreviation(rowObject.sport);
  const daySlug = rowObject.day.toLowerCase();
  const divisionSlug = rowObject.division.toLowerCase().split('+')[0] + 'Div'; // splits off the + from wtnb+

  // Extract all registration dates
  const vetDateTime = rowObject.vetRegistrationStartDateTime;
  const wtnbDateTime = rowObject.tnbWtnbRegistrationStartDateTime;
  const bipocDateTime = rowObject.bipocRegistrationStartDateTime;
  const earlyDateTime = rowObject.earlyRegistrationStartDateTime; // Backward compatibility
  const openDateTime = rowObject.openRegistrationStartDateTime;

  // Format dates
  const vetDateString = formatDateToIso(vetDateTime);
  const wtnbDateString = formatDateToIso(wtnbDateTime);
  const bipocDateString = formatDateToIso(bipocDateTime);
  const earlyDateString = formatDateToIso(earlyDateTime);
  const openDateString = formatDateToIso(openDateTime);

  Logger.log(`Variants - vet: ${vetGid}, wtnb: ${wtnbGid}, bipoc: ${bipocGid}, early: ${earlyGid}, open: ${openGid}`);
  Logger.log(`Dates - vet: ${vetDateString}, wtnb: ${wtnbDateString}, bipoc: ${bipocDateString}, early: ${earlyDateString}, open: ${openDateString}`);

  // Build chronological array of all variants
  const variants = [];
  
  if (vetGid && vetDateString) {
    variants.push({
      type: 'vet',
      name: 'Veteran Registration',
      gid: vetGid,
      date: vetDateString,
      dateRaw: vetDateTime
    });
  }
  
  // Handle TNB/WTNB and BIPOC variants
  if (wtnbGid && wtnbDateString) {
    variants.push({
      type: 'wtnb',
      name: `${rowObject.division === 'Open' ? 'W' : ''}TNB+ Early Registration`,
      gid: wtnbGid,
      date: wtnbDateString,
      dateRaw: wtnbDateTime
    });
  }
  
  if (bipocGid && bipocDateString) {
    variants.push({
      type: 'bipoc',
      name: 'BIPOC Early Registration',
      gid: bipocGid,
      date: bipocDateString,
      dateRaw: bipocDateTime
    });
  }
  
  // Backward compatibility: if old early variant exists but new ones don't
  if (earlyGid && earlyDateString && !wtnbGid && !bipocGid) {
    variants.push({
      type: 'early',
      name: `${rowObject.division === 'Open' ? 'W' : ''}TNB+ and BIPOC Early Registration`,
      gid: earlyGid,
      date: earlyDateString,
      dateRaw: earlyDateTime
    });
  }
  
  if (openGid && openDateString) {
    variants.push({
      type: 'open',
      name: 'Open Registration',
      gid: openGid,
      date: openDateString,
      dateRaw: openDateTime
    });
  }
  
  // Sort chronologically by date
  variants.sort((a, b) => {
    const dateA = a.dateRaw?.raw || a.dateRaw || a.date;
    const dateB = b.dateRaw?.raw || b.dateRaw || b.date;
    return new Date(dateA) - new Date(dateB);
  });
  
  Logger.log(`Chronological variants: ${JSON.stringify(variants.map(v => ({type: v.type, date: v.date})), null, 2)}`);

  const requests = []
  
  // Create movement requests in chronological order
  // Each variant moves to the next one in sequence
  for (let i = 0; i < variants.length - 1; i++) {
    const source = variants[i];
    const dest = variants[i + 1];
    
    Logger.log(`Creating movement: ${source.type} → ${dest.type}`);
    requests.push({
      actionType: `create-scheduled-inventory-movements`,
      scheduleName: `auto-move-${sportSlug}-${daySlug}-${productIdDigitsOnly}-${source.type}-to-${dest.type}`,
      groupName: `move-inventory-between-variants-${sportSlug}`,
      productUrl: productUrl,
      sourceVariant: {
        type: source.type,
        name: source.name,
        gid: source.gid
      },
      destinationVariant: {
        type: dest.type,
        name: dest.name,
        gid: dest.gid
      },
      newDatetime: dest.date,
      note: "newDateTime is in UTC (ET is 4 hours earlier than what this says)"
    });
  }

  // START OF STARTING INVENTORY UPDATE
  // Use the first registration variant (chronologically earliest)
  // Ensure we have a valid variant GID before scheduling
  const firstVariant = variants.length > 0 ? variants[0] : null;
  
  if (!firstVariant) {
    Logger.log(`❌ No valid variant found for initial inventory addition.`);
    SpreadsheetApp.getUi().alert(`❌ Error: No valid variant found. Please ensure at least one variant has a valid GID and date in the spreadsheet.`);
    return;
  }
  
  if (firstVariant.gid && firstVariant.date) {
    requests.push({
      actionType: `create-initial-inventory-addition-and-title-change`,
      scheduleName: `auto-set-${productIdDigitsOnly}-${sportSlug}-${daySlug}-${divisionSlug}-live`,
      groupName: `set-product-live`,
      productUrl: productUrl,
      productTitle: `Big Apple ${rowObject.sport} - ${rowObject.day} - ${rowObject.division} Division - ${rowObject.season} ${rowObject.year}`,
      variantGid: firstVariant.gid,
      inventoryToAdd: numTotalInventory,
      newDatetime: firstVariant.date,
      note: "newDateTime is in UTC (ET is 4 hours earlier than what this says)"
    });
  }

  // END OF STARTING INVENTORY UPDATE

  let allSuccessful = true

  for (const request of requests) {
    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify(request),
      muteHttpExceptions: true
    };

    try {
      const response = UrlFetchApp.fetch(apiEndpoint, options);
      const responseBody = JSON.parse(response.getContentText());
      Logger.log(`✅ Response for ${request.scheduleName}: ${response.getContentText()}`);

      if (!responseBody.message?.includes("updated successfully")) {
        allSuccessful = false;
      }
    } catch (err) {
      allSuccessful = false
      Logger.log(`❌ Error sending request for ${request.scheduleName}: ${err}`);
    }
  }

  if (allSuccessful) {
    const successColIndex = sheetHeaders.indexOf("Inventory Moves Scheduled?");
    sheet.getRange(selectedRow, successColIndex + 1).setValue(true);
    ui.alert("✅ Inventory moves scheduled successfully!");
  }
}

function formatDateToIso(dateString) {
  // Handle empty, null, or undefined dates
  if (!dateString || dateString === '' || dateString === null || dateString === undefined) {
    Logger.log(`formatDateToIso input: ${dateString}, output: null (empty date)`);
    return null;
  }
  
  // Handle date objects with .raw property (from parseRowData)
  if (typeof dateString === 'object' && dateString.raw) {
    dateString = dateString.raw;
  }
  
  const date = new Date(dateString);
  
  // Check if date is valid
  if (isNaN(date.getTime())) {
    Logger.log(`formatDateToIso input: ${dateString}, output: null (invalid date)`);
    return null;
  }
  
  const result = date.toISOString().split(".")[0];
  Logger.log(`formatDateToIso input: ${dateString}, output: ${result}`);
  return result;
}

function mapSportToAbbreviation(sport) {
  const map = {
    Dodgeball: 'db',
    Pickleball: 'pb',
    Bowling: 'bowl',
    Kickball: 'kb'
  };
  return map[sport] || "misc";
}

