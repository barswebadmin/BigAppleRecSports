// Global configuration constant for API destination
const API_DESTINATION = 'local'; // Change to 'AWS' for production

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
    "early registration start date/time": "earlyRegistrationStartDateTime",
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
  rowObject.earlyRegistrationStartDateTime = {raw: rowObject['earlyRegistrationStartDateTime'], formatted: formatDateAndTime(rowObject["earlyRegistrationStartDateTime"])};
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