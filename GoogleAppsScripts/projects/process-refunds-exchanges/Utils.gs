const SHEET_ID = "11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw";
const SHEET_GID = "1435845892";
const WAITLIST_RESPONSES_URL = 'https://docs.google.com/spreadsheets/d/1wFoayUoIx1PPOO0TtuS0Jnwb5hoIbgCd_kebMeYNzGQ/edit?resourcekey=&gid=744639660#gid=744639660'
const SHOPIFY_LOGIN_URL = 'https://shopify.com/55475535966/account'

const MODE = 'debug'; // Options: 'prodApi', 'debugApi'

const BACKEND_API_URL = 'https://bars-backend.onrender.com';
const LOCAL_TUNNEL_URL = 'https://334e55c8b409.ngrok-free.app'

const DEBUG_EMAIL = 'web@bigapplerecsports.com'

const API_URL = MODE.includes('prod') ? BACKEND_API_URL : LOCAL_TUNNEL_URL

function getSheet() {
  return SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
}

function getSheetData() {
  return getSheet().getDataRange().getValues();
}

function getSheetHeaders() {
  const data = getSheetData();
  return data[0];
}

const capitalize = str => str[0].toUpperCase() + str.slice(1)

const formatDateOnly = date => {
  return new Date(date).toLocaleDateString("en-US", { year: "2-digit", month: "numeric", day: "numeric" });
};

const formatDateAndTime = date => {
  const d = new Date(date);
  const datePart = d.toLocaleDateString("en-US", { year: "2-digit", month: "numeric", day: "numeric" });
  const timePart = d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true });
  return `${datePart} at ${timePart}`;
};

const formatTwoDecimalPoints = rawAmount => {
  return Number.parseFloat(rawAmount).toFixed(2)
}

  
function normalizeOrderNumber(orderNumber) {
  const str = String(orderNumber || "").trim();
  return str.startsWith("#") ? str : `#${str}`;
}

function parseRowData(rowObject, sheetHeaders) {
  const rowData = {};

  sheetHeaders.forEach((header, i) => {
    const lowerHeader = header.toLowerCase().trim();

    if (lowerHeader.includes("timestamp")) {
      rowData.requestSubmittedAt = rowObject[i];
    } else if (lowerHeader.includes("email address")) {
      rowData.requestorEmail = rowObject[i];
    } else if (lowerHeader.includes("order number")) {
      rowData.rawOrderNumber = rowObject[i];
    } else if (lowerHeader.includes("do you want a refund")) {
      rowData.refundOrCredit = rowObject[i].toLowerCase().includes("refund") ? "refund" : "credit";
    } else if (lowerHeader.includes("anything else to note")) {
      rowData.requestNotes = rowObject[i];
    } else if (lowerHeader.includes("first name")) {
      rowData.requestorFirstName = rowObject[i];
    } else if (lowerHeader.includes("last name")) {
      rowData.requestorLastName = rowObject[i];
    }
  });

  return rowData; // Return the parsed row data
}

function getRequestDetailsFromOrderNumber(rawOrderNumber) {
  const data = getSheetData();
  const sheetHeaders = getSheetHeaders();

  const orderIdColIndex = sheetHeaders.findIndex(h => h.toLowerCase().includes("order number"));
  const timestampColIndex = sheetHeaders.findIndex(h => h.toLowerCase().includes("timestamp"));

  if (orderIdColIndex === -1) {
    Logger.log(`❌ Order column header not found.`);
    return null;
  }

  // Find all matching rows
  const matchingRows = data
    .slice(1) // skip headers
    .filter(row => {
      const cellValue = row[orderIdColIndex];
      return normalizeOrderNumber(cellValue?.toString()?.trim()) === normalizeOrderNumber(rawOrderNumber);
    });
  if (matchingRows.length === 0) {
    Logger.log(`❌ No matching order found for ${rawOrderNumber}.`);
    return null;
  }

  // Return the row with the most recent timestamp
  const mostRecentRow = matchingRows.sort((a, b) => new Date(b[timestampColIndex]) - new Date(a[timestampColIndex]))[0];

  return parseRowData(mostRecentRow, sheetHeaders);
}

function getRowLink(orderNumber) {
  const data = getSheetData();
  const sheetHeaders = getSheetHeaders();
  
  const orderIdColIndex = sheetHeaders.findIndex(h => h.toLowerCase().includes("order number"));

  const rowIndex = data.slice(1).findIndex(row => {
    const cellValue = row[orderIdColIndex];
    if (!cellValue) return false;
    return normalizeOrderNumber(cellValue.toString()) === normalizeOrderNumber(orderNumber.toString());
  });
  
  if (rowIndex === -1) {
    Logger.log(`⚠️ Order number ${orderNumber} not found in sheet.`);
    return "";
  }

  // Convert to 1-based row index for Google Sheets link
  const rowNumber = rowIndex + 2;
  return `https://docs.google.com/spreadsheets/d/${SHEET_ID}/edit#gid=${SHEET_GID}&range=A${rowNumber}`;
}

function extractSeasonDates(descriptionHtml) {
  // Strip HTML tags and decode entities
  const text = descriptionHtml.replace(/<[^>]+>/g, "").replace(/&nbsp;/g, " ").replace(/\s+/g, " ").trim();
  Logger.log(`stripped descriptionHtml: ${text}`)

  const seasonDatesRegex =
    /Season Dates[^:\d]*[:\s]*?(\d{1,2}\/\d{1,2}\/\d{2,4})\s*[–—-]\s*(\d{1,2}\/\d{1,2}\/\d{2,4})(?:\s*\(\d+\s+weeks(?:,\s*off\s+([^)]+))?\))?/i;

  const match = text.match(seasonDatesRegex);
  Logger.log(`match: ${match}`)

  if (!match) return [null, null];

  const seasonStartDate = match[1];
  const offDatesStr = match[3] || null;
  if (!seasonStartDate?.includes('/') || (!!offDatesStr && !offDatesStr?.includes('/')) ) return [null, null];

  return [seasonStartDate, offDatesStr];
}

function markOrderAsProcessed(rawOrderNumber) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const data = sheet.getDataRange().getValues();
  const headers = data[0];

  const orderColIndex = headers.findIndex(h =>
    h.toLowerCase().includes("order number")
  );
  const processedColIndex = headers.findIndex(h =>
    h.toLowerCase().includes("processed")
  );

  if (orderColIndex === -1 || processedColIndex === -1) {
    throw new Error(
      `Missing required columns.\nHeaders: ${JSON.stringify(headers)}\nFound orderColIndex: ${orderColIndex}, processedColIndex: ${processedColIndex}`
    );
  }

  const normalizedTarget = normalizeOrderNumber(rawOrderNumber);
  let matchedValue = null;
  const rowIndex = data.findIndex((row, i) => {
    if (i === 0) return false;
    const cellValue = row[orderColIndex];
    const normalizedCell = normalizeOrderNumber(cellValue?.toString().trim() || "");
    if (normalizedCell === normalizedTarget) {
      matchedValue = cellValue;
      return true;
    }
    return false;
  });

  if (rowIndex === -1) {
    throw new Error(
      `Order number not found.\nRaw input: ${rawOrderNumber}\nNormalized: ${normalizedTarget}\nColumn Index: ${orderColIndex}\nExample values:\n` +
      data.slice(1, 6).map(row => row[orderColIndex]).join("\n")
    );
  }

  sheet.getRange(rowIndex + 1, processedColIndex + 1).setValue(true);
}