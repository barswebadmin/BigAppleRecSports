// const API_DESTINATION = 'local'
const API_DESTINATION = 'AWS'

function schedulePriceChanges(rowNumber = null) {

  const apiEndpoint = API_DESTINATION === 'AWS' ? 
      'https://6ltvg34u77der4ywcfk3zwr4fq0tcvvj.lambda-url.us-east-1.on.aws/'
      : 
      'https://chubby-grapes-trade.loca.lt' + '/api/price-scheduler'

  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const data = sheet.getDataRange().getValues();
  const sheetHeaders = data[0];
  const ui = SpreadsheetApp.getUi();

  const productUrlColIndex = sheetHeaders.findIndex(h => h.toLowerCase().includes("product url"));
  const openVariantColIndex = sheetHeaders.findIndex(h => h.toLowerCase().includes("open registration variant id"));
  const waitlistVariantColIndex = sheetHeaders.findIndex(h => h.toLowerCase().includes("waitlist registration variant id"));
  const seasonStartDateColIndex = sheetHeaders.findIndex(h => h.toLowerCase().includes("season start date"));
  const offDatesColIndex = sheetHeaders.findIndex(h => h.toLowerCase().includes("off dates"));
  const priceColIndex = sheetHeaders.findIndex(h => h.toLowerCase().includes("price"));
  const scheduledColIndex = sheetHeaders.findIndex(h => h.toLowerCase().includes("scheduled?"));
  const sportStartTimeColIndex = sheetHeaders.findIndex(h => h.toLowerCase().includes("sport start time"));
  
  const [sportColIdx, dayColIdx, divisionColIdx] = [
    sheetHeaders.indexOf("Sport"),
    sheetHeaders.indexOf("Day"),
    sheetHeaders.indexOf("Division")
  ];

  if (!rowNumber) {
    const validRows = data.map((row, idx) => ({
      index: idx + 1,
      isValid: !!row[openVariantColIndex] && !!row[priceColIndex]
    })).filter(row => row.isValid && row.index > 1);

    if (validRows.length === 0) {
      ui.alert("No valid rows with both Open Variant ID and Price.");
      return;
    }

    const options = validRows.map(row => {
      const r = data[row.index - 1];
      return `Row ${row.index}: ${r[sportColIdx]} - ${r[dayColIdx]} - ${r[divisionColIdx]}`;
    }).join("\n");

    const input = ui.prompt("Select Row", `Enter row number to schedule price change:\n${options}`, ui.ButtonSet.OK_CANCEL);
    if (input.getSelectedButton() !== ui.Button.OK || isNaN(input.getResponseText().trim())) {
      ui.alert("Cancelled or invalid row.");
      return;
    }

    rowNumber = parseInt(input.getResponseText().trim());
  }

  const row = data[rowNumber - 1];

  const offDatesRaw = row[offDatesColIndex];
  Logger.log(`offDatesRaw: ${offDatesRaw}, type is ${typeof offDatesRaw}`)

  const offDatesCommaSeparated = (() => {
    if (offDatesRaw instanceof Date) {
      return formatDateOnly(offDatesRaw);
    } else if (typeof offDatesRaw === 'string') {
      return offDatesRaw.trim();
    } else {
      return "";
    }
  })();

  const productIdDigitsOnly = row[productUrlColIndex].split('/').pop()

  const rawPayload = {
    actionType: `create-scheduled-price-changes`,
    sport: row[sportColIdx],
    day: row[dayColIdx],
    division: row[divisionColIdx],
    productGid: row[productUrlColIndex],
    openVariantGid: row[openVariantColIndex],
    waitlistVariantGid: row[waitlistVariantColIndex],
    price: row[priceColIndex],
    seasonStartDate: {type: typeof row[seasonStartDateColIndex], data: row[seasonStartDateColIndex]},
    sportStartTime: {type: typeof row[sportStartTimeColIndex], data: row[sportStartTimeColIndex]},
    offDatesRaw: {type: typeof row[offDatesColIndex], data: row[offDatesColIndex]}
  }

  const formattedPayload = {
    actionType: `create-scheduled-price-changes`,
    sport: row[sportColIdx],
    day: row[dayColIdx],
    division: row[divisionColIdx],
    productGid: `gid://shopify/Product/${productIdDigitsOnly}`,
    openVariantGid: row[openVariantColIndex],
    waitlistVariantGid: row[waitlistVariantColIndex],
    price: Number(row[priceColIndex]),
    seasonStartDate: formatDateOnly(row[seasonStartDateColIndex]),
    sportStartTime: formatTimeOnly(row[sportStartTimeColIndex]),
    offDatesCommaSeparated
  };

  const fetchPayload = API_DESTINATION === 'AWS' ? formattedPayload : rawPayload

  try {
    Logger.log(`sending: ${JSON.stringify(fetchPayload,null,2)}`)
    const response = UrlFetchApp.fetch(apiEndpoint, {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify(formattedPayload),
      muteHttpExceptions: true
    });

    

    const responseText = response.getContentText();
    Logger.log(`💬 Response from price scheduler: ${responseText}`);

    if (response.getResponseCode() === 200) {
      sheet.getRange(rowNumber, scheduledColIndex + 1).setValue(true);
      ui.alert("✅ Price change scheduled successfully!");
    } else {
      ui.alert(`❌ Error scheduling price change:\n${responseText}`);
    }

  } catch (error) {
    ui.alert(`❌ Failed to schedule price change: ${error.message}`);
  }
}