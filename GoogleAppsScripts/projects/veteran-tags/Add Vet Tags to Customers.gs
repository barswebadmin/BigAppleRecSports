const SHOPIFY_STORE = "09fe59-3.myshopify.com";
const GRAPHQL_URL = `https://${SHOPIFY_STORE}/admin/api/2025-01/graphql.json`;

// ✅ **Finds the row where a given field exists in Column A (case insensitive)**
function getFieldValue(sheet, fieldName) {
  const data = sheet.getRange("A:A").getValues().flat(); // Get all values from Column A
  const rowIndex = data.findIndex(cell => cell && cell.toString().toLowerCase().includes(fieldName.toLowerCase()));

  if (rowIndex === -1) {
    ui.alert(`⚠️ Missing value for ${fieldName}.`);
    return null;
  }

  return sheet.getRange(rowIndex + 1, 2).getValue(); // Return value from Column B (same row)
}

// ✅ **Finds the column index of the "Email" column**
function getEmailColumnIndex(sheet) {
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  return headers.findIndex(header => header.toLowerCase().includes("email")) + 1; // Adjust for 1-based index
}

// ✅ **Extracts all emails from the "Email" column**
function getEmails(sheet, emailColIndex) {
  if (emailColIndex === 0) {
    ui.alert("⚠️ 'Email' column not found!");
    return [];
  }
  return sheet
    .getRange(2, emailColIndex, sheet.getLastRow() - 1, 1)
    .getValues()
    .flat()
    .filter(email => email && email.toString().trim() !== '');
}

// ✅ **Fetch Customer Details from Shopify**
function getCustomerDetails(email) {
  const query = {
    query: `query GetCustomerId($identifier: CustomerIdentifierInput!) {
      customerByIdentifier(identifier: $identifier) { id tags }
    }`,
    variables: { identifier: { emailAddress: email } }
  };

  const options = {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Shopify-Access-Token": SHOPIFY_TOKEN
    },
    payload: JSON.stringify(query)
  };

  const response = UrlFetchApp.fetch(GRAPHQL_URL, options);
  const json = JSON.parse(response.getContentText());

  return [
    json.data?.customerByIdentifier?.id || null,
    json.data?.customerByIdentifier?.tags || [] // Retrieve existing customer tags
  ];
}

// ✅ **Update Customer Tags on Shopify**
function addVeteranTagToEmail(customerId, updatedTags) {
  const mutation = {
    query: `mutation updateCustomerMetafields($input: CustomerInput!) {
      customerUpdate(input: $input) { customer { id tags } userErrors { message field } }
    }`,
    variables: { input: { id: customerId, tags: updatedTags } }
  };

  const options = {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Shopify-Access-Token": SHOPIFY_TOKEN
    },
    payload: JSON.stringify(mutation)
  };

  const response = UrlFetchApp.fetch(GRAPHQL_URL, options);
  const responseData = JSON.parse(response.getContentText());

  if (responseData?.data?.customerUpdate?.userErrors?.length) {
    Logger.log(`❌ Shopify Errors: ${JSON.stringify(responseData.data.customerUpdate.userErrors)}`);
  }
}



// ✅ **Main Function**
function addVeteranTagToCustomerEmails() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();

  // ✅ **Extract values dynamically**
  const fieldsToProcess = {
    sport: getFieldValue(sheet, "Sport"),
    season: getFieldValue(sheet, "Season"),
    year: getFieldValue(sheet, "Year"),
    day: getFieldValue(sheet, "Day"),
    division: getFieldValue(sheet, "Division"),
    veteranTag: getFieldValue(sheet, "Vet code to be added"),
    leadershipEmailAddress: getFieldValue(sheet, "BARS team email alias")
  };

  // ✅ **Check for missing fields**
  for (const [key, value] of Object.entries(fieldsToProcess)) {
    if (!value) return; // Missing value alert is already handled in getFieldValue()
  }

  const { sport, season, year, day, division, veteranTag, leadershipEmailAddress } = fieldsToProcess;

  // ✅ **Extract emails**
  const emailColIndex = getEmailColumnIndex(sheet);
  const emailRange = getEmails(sheet, emailColIndex);
  if (emailRange.length === 0) {
    ui.alert("⚠️ No emails found in the 'Vet Emails' column.");
    return;
  }

  try {
    function mapSportToAbbreviation(sport) {
      const map = {
        Dodgeball: 'db',
        Pickleball: 'pb',
        Bowling: 'bowl',
        Kickball: 'kb'
      };
      return map[sport] || sport.toLowerCase();
    }

    const sportSlug = mapSportToAbbreviation(sport);
    const daySlug = day.toLowerCase();
    const divisionSlug = division.toLowerCase().split('+')[0] + 'Div';

    const scheduleName = `move-${sportSlug}-${daySlug}-${divisionSlug}-vet-to-early`;
    const groupName = `move-inventory-between-variants-${sportSlug}`;

    const payload = {
      action: 'update-scheduled-inventory-move-with-num-eligible-veterans',
      scheduleName,
      groupName,
      numEligibleVeterans: emailRange.length
    };

    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };

    const response = UrlFetchApp.fetch('https://5klhixgo6d.execute-api.us-east-1.amazonaws.com/createSchedule', options);
    Logger.log(`📤 Schedule update response: ${response.getContentText()}`);
  } catch (e) {
    ui.alert("⚠️ The inventory move schedule could not be updated.");
  }

  const errors = [];
  const veteransList = [];

  emailRange.forEach(email => {
    Logger.log(`Processing: ${email}`);

    const [customerId, tags] = getCustomerDetails(email);

    if (!customerId) {
      errors.push(email);
      return;
    }

    // ✅ **Add Veteran Tag & Collect Emails for BCC**
    veteransList.push(email);
    const updatedTags = Array.isArray(tags) && tags.includes(veteranTag)
      ? tags
      : [...(tags || []), veteranTag];
    addVeteranTagToEmail(customerId, updatedTags);
  });

  if (errors.length > 0) {
    ui.alert(`⚠️ The following emails were not found:\n${errors.join(", ")}`);
  }

  // ✅ **Send BCC Email to Veterans**
  if (veteransList.length > 0) {
    const confirmSend = ui.alert(
      `Veteran tags have been added to customer profiles successfully to ${veteransList.length} of ${emailRange.length} emails.\n\nClick OK to send email to those ${veteransList.length} eligible player(s), or Cancel to stop here and send the email yourself.`,
      ui.ButtonSet.OK_CANCEL
    );

    if (confirmSend === ui.Button.CANCEL || confirmSend === ui.Button.CLOSE) {
      ui.alert("Veteran tags added, but players were not emailed. Please remember to email them manually (or run this script again) so players don't send last-minute emails of confusion!");
      return;
    }
    try {
      sendVeteranEmail(veteransList, sport, day, division, season, year, leadershipEmailAddress);
      ui.alert(`✅ Veteran tags added successfully and ${veteransList.length} players have been emailed with instructions!`);
    } catch(e) {
      ui.alert(`⚠️ Not all players could be emailed! Please see the following errors: ${e}`);
    }

  }





}
