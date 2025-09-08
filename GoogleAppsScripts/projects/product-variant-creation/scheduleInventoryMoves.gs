function scheduleInventoryMoves(selectedRow = null) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const data = sheet.getDataRange().getValues();
  const sheetHeaders = data[0];

  const productUrlColIndex = sheetHeaders.indexOf("Product URL");
  const vetVariantColIndex = sheetHeaders.indexOf("Vet Registration Variant ID");
  const earlyVariantColIndex = sheetHeaders.indexOf("Early Registration Variant ID");
  const openVariantColIndex = sheetHeaders.indexOf("Open Registration Variant ID");
  
  const numTotalInventoryColIndex = sheetHeaders.indexOf("Total Inventory");
  const isInventoryMoveScheduledIndex = sheetHeaders.indexOf("Inventory Moves Scheduled?");

  let validRows = [];
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    if (!!row[earlyVariantColIndex] && !!row[openVariantColIndex]) validRows.push({ rowIndex: i + 1, rowData: row });
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
  const vetGid = rowData[vetVariantColIndex];
  const earlyGid = rowData[earlyVariantColIndex];
  const openGid = rowData[openVariantColIndex];
  const numTotalInventory = rowData[numTotalInventoryColIndex]
  
  const sportSlug = mapSportToAbbreviation(rowObject.sport);
  const daySlug = rowObject.day.toLowerCase();
  const divisionSlug = rowObject.division.toLowerCase().split('+')[0] + 'Div'; // splits off the + from wtnb+

  const vetDateTime = rowObject.vetRegistrationStartDateTime;
  const earlyDateTime = rowObject.earlyRegistrationStartDateTime;
  const openDateTime = rowObject.openRegistrationStartDateTime;

  const vetDateString = formatDateToIso(vetDateTime);
  const earlyDateString = formatDateToIso(earlyDateTime);
  const openDateString = formatDateToIso(openDateTime)

  Logger.log(`rowObject: ${JSON.stringify(rowObject,null,2)} \n vettime is ${typeof vetDateTime}: ${JSON.stringify(vetDateTime)} \n earlytime is ${typeof earlyDateTime}: ${JSON.stringify(earlyDateTime)} \n opentime is ${typeof openDateTime}: ${JSON.stringify(openDateTime)}`)

  let reg1, reg2, time1, time2, gid1, gid2
  if (vetGid) {
    Logger.log('yes vetGid')
    if (vetDateTime < earlyDateTime) {
      Logger.log('vet is before early')
      reg1 = 'vet'
      time1 = vetDateString
      gid1 = vetGid
      reg2 = 'early'
      time2 = earlyDateString
      gid2 = earlyGid
    } else {
      Logger.log('early is before vet')
      reg1 = 'early'
      time1 = earlyDateString
      gid1 = earlyGid
      reg2 = 'vet'
      time2 = vetDateString
      gid2 = vetGid
    }
  } else {
    Logger.log('no vetGid')
    reg1 = 'vet'
    time1 = vetDateString
    gid1 = vetGid
    reg2 = 'early'
    time2 = earlyDateString
    gid2 = earlyGid
  }
  Logger.log(`Final assignments - reg1: ${reg1}, time1: ${time1}, gid1: ${gid1}`);
  Logger.log(`Final assignments - reg2: ${reg2}, time2: ${time2}, gid2: ${gid2}`);

  const requests = []
  if (vetGid && vetDateTime) {
    requests.push({
      actionType: `create-scheduled-inventory-movements`,
      scheduleName: `auto-move-${sportSlug}-${daySlug}-${productIdDigitsOnly}-${reg1}-to-${reg2}`,
      groupName: `move-inventory-between-variants-${sportSlug}`,
      productUrl: productUrl,
      sourceVariant: {
        type: reg1,
        name: `${capitalize(reg1)} Registration`,
        gid: gid1
      },
      destinationVariant: {
        type: reg2,
        name: `${capitalize(reg2)} Registration`,
        gid: gid2
      },
      newDatetime: time2,
      note: "newDateTime is in UTC (ET is 4 hours earlier than what this says)"
    });
  }

  requests.push({
    actionType: `create-scheduled-inventory-movements`,
    scheduleName: `auto-move-${productIdDigitsOnly}-${sportSlug}-${daySlug}-${divisionSlug}-${reg2}-to-open`,
    groupName: `move-inventory-between-variants-${sportSlug}`,
    productUrl: productUrl,
    sourceVariant: {
      type: reg2,
      name: `${capitalize(reg2)} Registration`,
      gid: gid2
    },
    destinationVariant: {
      type: 'open',
      name: 'Open Registration',
      gid: openGid
    },
    newDatetime: openDateString,
    note: "newDateTime is in UTC (ET is 4 hours earlier than what this says)"
  })

  // START OF STARTING INVENTORY UPDATE
  requests.push({
    actionType: `create-initial-inventory-addition-and-title-change`,
    scheduleName: `auto-set-${productIdDigitsOnly}-${sportSlug}-${daySlug}-${divisionSlug}-live`,
    groupName: `set-product-live`,
    productUrl: productUrl,
    productTitle: `Big Apple ${rowObject.sport} - ${rowObject.day} - ${rowObject.division} Division - ${rowObject.season} ${rowObject.year}`,
    variantGid: vetGid,
    inventoryToAdd: numTotalInventory,
    newDatetime: vetDateString,
    note: "newDateTime is in UTC (ET is 4 hours earlier than what this says)"
  })

  // END OF STARTING INVENTORY UPDATE

  // Send the requests
  const apiEndpoint = API_DESTINATION === 'AWS' ? 
      'https://6ltvg34u77der4ywcfk3zwr4fq0tcvvj.lambda-url.us-east-1.on.aws/'
      : 
      'https://chubby-grapes-trade.loca.lt' + '/api/inventory-scheduler'

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
  const date = new Date(dateString);
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

