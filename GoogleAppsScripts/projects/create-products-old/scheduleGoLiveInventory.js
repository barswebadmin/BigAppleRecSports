/**
 * Prompts user to schedule go-live inventory for a product.
 * Called automatically after product and variant creation.
 * 
 * Flow:
 * 1. Determines which registration period comes first (Vet or Early)
 * 2. Prompts user for number of spots to release at first registration
 * 3. Schedules first inventory addition via Lambda
 * 4. If spots < total inventory, schedules remaining spots at second registration
 */
function promptAndScheduleGoLiveInventory(productUrl, variantIds, registrationDates, totalInventory, rowObject) {
  const { vetVariantId, earlyVariantId, openVariantId } = variantIds;
  const { vetRegistrationStartDateTime, earlyRegistrationStartDateTime } = registrationDates;
  
  let firstRegType, firstRegTime, firstVariantId;
  let secondRegType, secondRegTime, secondVariantId;
  
  if (vetRegistrationStartDateTime && vetRegistrationStartDateTime.raw && 
      earlyRegistrationStartDateTime && earlyRegistrationStartDateTime.raw &&
      new Date(vetRegistrationStartDateTime.raw) < new Date(earlyRegistrationStartDateTime.raw)) {
    firstRegType = 'Veteran';
    firstRegTime = vetRegistrationStartDateTime;
    firstVariantId = vetVariantId;
    secondRegType = 'Early';
    secondRegTime = earlyRegistrationStartDateTime;
    secondVariantId = earlyVariantId;
  } else if (earlyRegistrationStartDateTime && earlyRegistrationStartDateTime.raw) {
    firstRegType = 'Early';
    firstRegTime = earlyRegistrationStartDateTime;
    firstVariantId = earlyVariantId;
    secondRegType = 'Open';
    secondRegTime = null;
    secondVariantId = openVariantId;
  } else {
    Logger.log('No valid registration dates found for inventory scheduling');
    SpreadsheetApp.getUi().alert('Cannot schedule inventory: No valid registration start dates found.');
    return;
  }
  
  const ui = SpreadsheetApp.getUi();
  const promptMessage = 
    `Schedule Initial Inventory\n\n` +
    `How many spots should be added at ${firstRegType} Registration?\n` +
    `(${firstRegType} Registration: ${firstRegTime.formatted})\n\n` +
    `Total Inventory: ${totalInventory}`;
  
  const response = ui.prompt(promptMessage, ui.ButtonSet.OK_CANCEL);
  
  if (response.getSelectedButton() === ui.Button.CANCEL) {
    Logger.log('User cancelled inventory scheduling');
    return;
  }
  
  const spotsAtFirst = parseInt(response.getResponseText());
  
  if (isNaN(spotsAtFirst) || spotsAtFirst <= 0) {
    ui.alert('Invalid number entered. Inventory scheduling cancelled.');
    return;
  }
  
  if (spotsAtFirst > totalInventory) {
    ui.alert(`Cannot schedule ${spotsAtFirst} spots: exceeds total inventory of ${totalInventory}.\nInventory scheduling cancelled.`);
    return;
  }
  
  try {
    scheduleInitialInventoryAddition(
      productUrl,
      firstVariantId,
      firstRegTime.raw,
      spotsAtFirst,
      totalInventory,
      rowObject
    );
    
    if (spotsAtFirst < totalInventory && secondRegTime) {
      const remainingSpots = totalInventory - spotsAtFirst;
      scheduleRemainingInventoryAddition(
        productUrl,
        secondVariantId,
        secondRegTime.raw,
        remainingSpots,
        totalInventory,
        spotsAtFirst,
        rowObject
      );
      
      ui.alert(
        `✅ Inventory scheduled successfully!\n\n` +
        `${spotsAtFirst} spots at ${firstRegType} registration (${firstRegTime.formatted})\n` +
        `${remainingSpots} spots at ${secondRegType} registration (${secondRegTime.formatted})`
      );
    } else {
      ui.alert(
        `✅ Inventory scheduled successfully!\n\n` +
        `${spotsAtFirst} spots at ${firstRegType} registration (${firstRegTime.formatted})`
      );
    }
  } catch (err) {
    Logger.log(`❌ Error scheduling inventory: ${err.message}`);
    ui.alert(`❌ Failed to schedule inventory:\n${err.message}`);
  }
}

function scheduleInitialInventoryAddition(productUrl, variantGid, scheduledAt, numberVetSpotsToReleaseAtGoLive, totalInventory, rowObject) {
  const lambdaUrl = 'https://6ltvg34u77der4ywcfk3zwr4fq0tcvvj.lambda-url.us-east-1.on.aws/'
  
  const productIdMatch = productUrl.match(/\/products\/(\d+)/);
  const productIdDigitsOnly = productIdMatch ? productIdMatch[1] : 'unknown';
  
  const mapSportToAbbreviation = (sport) => {
    const map = {
      'Dodgeball': 'db',
      'Pickleball': 'pb',
      'Bowling': 'bowl',
      'Kickball': 'kb'
    };
    return map[sport] || sport.toLowerCase();
  };
  
  const sportSlug = mapSportToAbbreviation(rowObject.sport);
  const daySlug = rowObject.day.toLowerCase();
  const divisionSlug = rowObject.division.toLowerCase().split('+')[0] + 'div';
  
  const productTitle = `Big Apple ${rowObject.sport} - ${rowObject.day} - ${rowObject.division} Division - ${rowObject.season} ${rowObject.year}`;
  
  const payload = {
    actionType: 'create-initial-inventory-addition-and-title-change',
    scheduleName: `auto-set-${productIdDigitsOnly}-${sportSlug}-${daySlug}-${divisionSlug}-live`,
    groupName: 'set-product-live',
    productUrl: productUrl,
    productTitle: productTitle,
    variantGid: variantGid,
    newDatetime: new Date(scheduledAt).toISOString(),
    note: "newDateTime is in UTC (ET is 4 hours earlier than what this says)",
    totalInventory: totalInventory,
    numberVetSpotsToReleaseAtGoLive: numberVetSpotsToReleaseAtGoLive
  };
  
  Logger.log(`Scheduling initial inventory: ${JSON.stringify(payload, null, 2)}`);
  
  sendLambdaRequest(lambdaUrl, payload);
}

function scheduleRemainingInventoryAddition(productUrl, variantGid, scheduledAt, inventoryToAdd, totalInventory, numberVetSpotsToReleaseAtGoLive, rowObject) {
  const lambdaUrl = secrets['LAMBDA_SCHEDULE_CHANGES'];
  
  const productIdMatch = productUrl.match(/\/products\/(\d+)/);
  const productIdDigitsOnly = productIdMatch ? productIdMatch[1] : 'unknown';
  
  const mapSportToAbbreviation = (sport) => {
    const map = {
      'Dodgeball': 'db',
      'Pickleball': 'pb',
      'Bowling': 'bowl',
      'Kickball': 'kb'
    };
    return map[sport] || sport.toLowerCase();
  };
  
  const sportSlug = mapSportToAbbreviation(rowObject.sport);
  const daySlug = rowObject.day.toLowerCase();
  const divisionSlug = rowObject.division.toLowerCase().split('+')[0] + 'div';
  
  const productTitle = `Big Apple ${rowObject.sport} - ${rowObject.day} - ${rowObject.division} Division - ${rowObject.season} ${rowObject.year}`;
  
  const payload = {
    actionType: 'create-initial-inventory-addition-and-title-change',
    scheduleName: `auto-add-remaining-inventory-${productIdDigitsOnly}-${sportSlug}-${daySlug}-${divisionSlug}`,
    groupName: 'add-remaining-inventory-to-live-product',
    productUrl: productUrl,
    productTitle: productTitle,
    variantGid: variantGid,
    newDatetime: new Date(scheduledAt).toISOString(),
    note: "newDateTime is in UTC (ET is 4 hours earlier than what this says)",
    totalInventory: totalInventory,
    numberVetSpotsToReleaseAtGoLive: numberVetSpotsToReleaseAtGoLive,
    inventoryToAdd: inventoryToAdd
  };
  
  Logger.log(`Scheduling remaining inventory: ${JSON.stringify(payload, null, 2)}`);
  
  sendLambdaRequest(lambdaUrl, payload);
}

function sendLambdaRequest(lambdaUrl, payload) {
  try {
    const response = UrlFetchApp.fetch(lambdaUrl, {
      method: 'POST',
      contentType: 'application/json',
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    });
    
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();
    
    Logger.log(`Lambda response [${responseCode}]: ${responseText}`);
    
    if (responseCode < 200 || responseCode >= 300) {
      throw new Error(`Lambda returned ${responseCode}: ${responseText}`);
    }
  } catch (err) {
    Logger.log(`❌ Error sending Lambda request: ${err.message}`);
    throw err;
  }
}

function scheduleGoLiveInventoryFromRow() {
  const ui = SpreadsheetApp.getUi();
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const data = sheet.getDataRange().getValues();
  const sheetHeaders = data[0];
  
  const response = ui.prompt('Schedule Product Go-Live', 'Enter the row number to schedule inventory for:', ui.ButtonSet.OK_CANCEL);
  
  if (response.getSelectedButton() === ui.Button.CANCEL) {
    return;
  }
  
  const rowNumber = parseInt(response.getResponseText());
  
  if (isNaN(rowNumber) || rowNumber < 2 || rowNumber > data.length) {
    ui.alert('Invalid row number. Please enter a row number between 2 and ' + data.length);
    return;
  }
  
  const rowData = data[rowNumber - 1];
  
  const getColumnValue = (headerName) => {
    const index = sheetHeaders.findIndex(h => (h || '').toString().toLowerCase().includes(headerName.toLowerCase()));
    return index !== -1 ? rowData[index] : null;
  };
  
  const productUrl = getColumnValue('product url');
  const vetVariantIdValue = getColumnValue('vet registration variant id');
  const earlyVariantIdValue = getColumnValue('early registration variant id');
  const openVariantIdValue = getColumnValue('open registration variant id');
  const totalInventory = getColumnValue('total inventory');
  
  Logger.log(`📋 Variant IDs read from sheet:`);
  Logger.log(`  Vet: ${vetVariantIdValue}`);
  Logger.log(`  Early: ${earlyVariantIdValue}`);
  Logger.log(`  Open: ${openVariantIdValue}`);
  
  const sport = getColumnValue('sport');
  const day = getColumnValue('day');
  const division = getColumnValue('division');
  const season = getColumnValue('season');
  const year = getColumnValue('year');
  
  const vetRegRaw = getColumnValue('vet registration');
  const earlyRegRaw = getColumnValue('early registration');
  
  if (!productUrl) {
    ui.alert('Cannot schedule: Product URL not found in row ' + rowNumber);
    return;
  }
  
  if (!vetVariantIdValue || !earlyVariantIdValue || !openVariantIdValue) {
    ui.alert('Cannot schedule: Variant IDs not found in row ' + rowNumber + '. Product may not be created yet.');
    return;
  }
  
  if (!totalInventory || isNaN(parseInt(totalInventory))) {
    ui.alert('Cannot schedule: Total Inventory not found or invalid in row ' + rowNumber);
    return;
  }
  
  if (!sport || !day || !division || !season || !year) {
    ui.alert('Cannot schedule: Missing required product info (sport, day, division, season, year) in row ' + rowNumber);
    return;
  }
  
  const formatDateTime = (dateValue) => {
    if (!dateValue) return null;
    try {
      const date = new Date(dateValue);
      if (isNaN(date.getTime())) return null;
      
      const options = { 
        month: 'numeric', 
        day: 'numeric', 
        year: '2-digit', 
        hour: 'numeric', 
        minute: '2-digit', 
        hour12: true 
      };
      const formatted = date.toLocaleString('en-US', options).replace(',', '');
      
      return {
        raw: date,
        formatted: formatted
      };
    } catch (err) {
      Logger.log(`Error formatting date: ${err.message}`);
      return null;
    }
  };
  
  const vetRegistrationStartDateTime = formatDateTime(vetRegRaw);
  const earlyRegistrationStartDateTime = formatDateTime(earlyRegRaw);
  
  if (!vetRegistrationStartDateTime && !earlyRegistrationStartDateTime) {
    ui.alert('Cannot schedule: No valid registration start dates found in row ' + rowNumber);
    return;
  }
  
  const variantIds = {
    vetVariantId: vetVariantIdValue,
    earlyVariantId: earlyVariantIdValue,
    openVariantId: openVariantIdValue
  };
  
  const registrationDates = {
    vetRegistrationStartDateTime: vetRegistrationStartDateTime,
    earlyRegistrationStartDateTime: earlyRegistrationStartDateTime
  };
  
  const rowObject = {
    sport: sport,
    day: day,
    division: division,
    season: season,
    year: year
  };
  
  promptAndScheduleGoLiveInventory(
    productUrl,
    variantIds,
    registrationDates,
    parseInt(totalInventory),
    rowObject
  );
}

