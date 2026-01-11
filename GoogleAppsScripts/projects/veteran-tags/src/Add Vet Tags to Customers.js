const SHOPIFY_STORE = "09fe59-3.myshopify.com";
const GRAPHQL_URL = `https://${SHOPIFY_STORE}/admin/api/2025-01/graphql.json`;
const SHOPIFY_TOKEN = PropertiesService.getScriptProperties().getProperty('SHOPIFY_ACCESS_TOKEN');

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
  Logger.log(`📤 Fetching customer details for: ${email}`);
  
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

  Logger.log(`📤 Sending query to Shopify: ${JSON.stringify(query, null, 2)}`);
  const response = UrlFetchApp.fetch(GRAPHQL_URL, options);
  const json = JSON.parse(response.getContentText());
  Logger.log(`📥 Received response from Shopify: ${JSON.stringify(json, null, 2)}`);

  const customerId = json.data?.customerByIdentifier?.id || null;
  const tags = json.data?.customerByIdentifier?.tags || [];
  
  Logger.log(`   Customer ID: ${customerId}`);
  Logger.log(`   Current tags: ${JSON.stringify(tags)}`);

  return [customerId, tags];
}

// ✅ **Update Customer Tags on Shopify**
function updateCustomerTags(customerId, updatedTags) {
  Logger.log(`📝 Updating customer tags for: ${customerId}`);
  Logger.log(`   New tags to set: ${JSON.stringify(updatedTags)}`);
  
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

  Logger.log(`📤 Sending mutation to Shopify: ${JSON.stringify(mutation, null, 2)}`);
  const response = UrlFetchApp.fetch(GRAPHQL_URL, options);
  const responseData = JSON.parse(response.getContentText());
  Logger.log(`📥 Update response from Shopify: ${JSON.stringify(responseData, null, 2)}`);

  if (responseData?.data?.customerUpdate?.userErrors?.length) {
    Logger.log(`❌ Shopify Errors: ${JSON.stringify(responseData.data.customerUpdate.userErrors)}`);
  } else {
    Logger.log(`✅ Tags updated successfully`);
    Logger.log(`   Final tags on customer: ${JSON.stringify(responseData?.data?.customerUpdate?.customer?.tags)}`);
  }
}

// ✅ **Modify Tags (Add or Remove)**
function modifyTags(tags, veteranTag, operation) {
  const tagArray = tags || [];
  
  Logger.log(`🏷️ Modifying tags (operation: ${operation})`);
  Logger.log(`   Before: ${JSON.stringify(tagArray)}`);
  Logger.log(`   Target tag: ${veteranTag}`);
  
  let result;
  if (operation === 'add') {
    result = tagArray.includes(veteranTag) ? tagArray : [...tagArray, veteranTag];
  } else if (operation === 'remove') {
    result = tagArray.filter(tag => tag !== veteranTag);
  } else {
    result = tagArray;
  }
  
  Logger.log(`   After: ${JSON.stringify(result)}`);
  Logger.log(`   Tags changed: ${JSON.stringify(tagArray) !== JSON.stringify(result)}`);
  
  return result;
}



// ✅ **Generic Function to Process Veteran Tags (Add or Remove)**
function processVeteranTags(operation) {
  const functionName = 'processVeteranTags';
  const startTime = new Date().getTime();
  const timestamp = new Date().toISOString();
  
  Logger.log(`🚀 [${timestamp}] === ENTERING ${functionName} ===`);
  Logger.log(`   Operation: ${operation}`);
  
  let context = {
    operation: operation,
    fieldsToProcess: {},
    emailCount: 0,
    processedCount: 0,
    errorCount: 0,
    errors: []
  };
  
  try {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    Logger.log(`📊 [${timestamp}] Getting active spreadsheet sheet...`);

    Logger.log(`🔍 [${timestamp}] Extracting field values from sheet...`);
    const fieldsToProcess = {
      sport: getFieldValue(sheet, "Sport"),
      season: getFieldValue(sheet, "Season"),
      year: getFieldValue(sheet, "Year"),
      day: getFieldValue(sheet, "Day"),
      division: getFieldValue(sheet, "Division"),
      veteranTag: getFieldValue(sheet, "Vet code to be added"),
      leadershipEmailAddress: getFieldValue(sheet, "BARS team email alias")
    };
    context.fieldsToProcess = fieldsToProcess;
    
    Logger.log(`📋 [${timestamp}] Field values extracted:`);
    Object.entries(fieldsToProcess).forEach(([key, value]) => {
      Logger.log(`   ${key}: ${value || 'MISSING'}`);
    });

    // Validate all fields are present
    const missingFields = [];
    for (const [key, value] of Object.entries(fieldsToProcess)) {
      if (!value) {
        missingFields.push(key);
      }
    }
    
    if (missingFields.length > 0) {
      const errorMsg = `Missing required fields: ${missingFields.join(', ')}`;
      Logger.log(`❌ [${timestamp}] === VALIDATION ERROR in ${functionName} ===`);
      Logger.log(`   Operation: Validating required fields`);
      Logger.log(`   Error: ${errorMsg}`);
      Logger.log(`   Missing fields: ${missingFields.join(', ')}`);
      ui.alert(`⚠️ ${errorMsg}`);
      return;
    }
    
    Logger.log(`✅ [${timestamp}] All required fields present`);

  const { sport, season, year, day, division, veteranTag, leadershipEmailAddress } = fieldsToProcess;

  const emailColIndex = getEmailColumnIndex(sheet);
  const emailRange = getEmails(sheet, emailColIndex);
  if (emailRange.length === 0) {
    ui.alert("⚠️ No emails found in the 'Vet Emails' column.");
    return;
  }

  if (operation === 'add') {
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
  }

    const errors = [];
    const processedList = [];
    context.emailCount = emailRange.length;
    Logger.log(`📧 [${timestamp}] Processing ${emailRange.length} email(s)...`);

    emailRange.forEach((email, index) => {
      const emailStartTime = new Date().getTime();
      Logger.log(`\n${'='.repeat(60)}`);
      Logger.log(`📧 [${timestamp}] Processing email ${index + 1}/${emailRange.length}: ${email}`);
      Logger.log(`${'='.repeat(60)}`);

      try {
        Logger.log(`🔍 [${timestamp}] Getting customer details for: ${email}`);
        const [customerId, tags] = getCustomerDetails(email);

        if (!customerId) {
          const errorMsg = `Customer not found in Shopify for email: ${email}`;
          Logger.log(`❌ [${timestamp}] ${errorMsg}`);
          errors.push(email);
          context.errors.push({ email, error: errorMsg });
          context.errorCount++;
          return;
        }
        
        Logger.log(`✅ [${timestamp}] Customer found: ${customerId}`);
        Logger.log(`   Current tags: ${JSON.stringify(tags)}`);

        Logger.log(`🔍 [${timestamp}] Modifying tags (operation: ${operation})...`);
        const updatedTags = modifyTags(tags, veteranTag, operation);
        
        const tagArray = tags || [];
        const tagsChanged = operation === 'add' 
          ? !tagArray.includes(veteranTag)
          : tagArray.includes(veteranTag);
        
        Logger.log(`🔍 [${timestamp}] Tag change needed: ${tagsChanged}`);
        
        if (tagsChanged) {
          Logger.log(`✅ [${timestamp}] Will update customer tags`);
          processedList.push(email);
          try {
            Logger.log(`📝 [${timestamp}] Updating customer tags...`);
            updateCustomerTags(customerId, updatedTags);
            context.processedCount++;
            const emailDuration = new Date().getTime() - emailStartTime;
            Logger.log(`✅ [${timestamp}] Successfully updated customer ${customerId} (${emailDuration}ms)`);
          } catch (updateError) {
            const errorMsg = `Failed to update customer tags for ${email}: ${updateError.message}`;
            Logger.log(`❌ [${timestamp}] === ERROR updating customer tags ===`);
            Logger.log(`   Email: ${email}`);
            Logger.log(`   Customer ID: ${customerId}`);
            Logger.log(`   Error: ${updateError.message}`);
            Logger.log(`   Stack: ${updateError.stack || 'No stack trace'}`);
            errors.push(email);
            context.errors.push({ email, customerId, error: errorMsg, stack: updateError.stack });
            context.errorCount++;
          }
        } else {
          Logger.log(`⏭️ [${timestamp}] Skipping - customer already has correct tag status`);
        }
      } catch (emailError) {
        const errorMsg = `Error processing email ${email}: ${emailError.message}`;
        Logger.log(`❌ [${timestamp}] === ERROR processing email ===`);
        Logger.log(`   Email: ${email}`);
        Logger.log(`   Error: ${emailError.message}`);
        Logger.log(`   Stack: ${emailError.stack || 'No stack trace'}`);
        errors.push(email);
        context.errors.push({ email, error: errorMsg, stack: emailError.stack });
        context.errorCount++;
      }
    });

    const duration = new Date().getTime() - startTime;
    Logger.log(`\n${'='.repeat(60)}`);
    Logger.log(`📊 [${timestamp}] === PROCESSING SUMMARY ===`);
    Logger.log(`   Total emails: ${context.emailCount}`);
    Logger.log(`   Successfully processed: ${context.processedCount}`);
    Logger.log(`   Errors: ${context.errorCount}`);
    Logger.log(`   Duration: ${duration}ms`);
    Logger.log(`${'='.repeat(60)}\n`);

    if (errors.length > 0) {
      Logger.log(`⚠️ [${timestamp}] Errors encountered:`);
      errors.forEach((email, idx) => {
        Logger.log(`   ${idx + 1}. ${email}`);
      });
      ui.alert(`⚠️ The following emails had errors:\n${errors.join(", ")}`);
    }

    const actionVerb = operation === 'add' ? 'added' : 'removed';
    const actionPrep = operation === 'add' ? 'to' : 'from';

    if (processedList.length === 0) {
      Logger.log(`ℹ️ [${timestamp}] No tags were ${actionVerb} - all customers already had correct tag status`);
      ui.alert(`ℹ️ No tags were ${actionVerb}. All customers already had the correct tag status.`);
      return;
    }

    if (operation === 'add' && processedList.length > 0) {
      const confirmSend = ui.alert(
        `Veteran tags have been ${actionVerb} ${actionPrep} ${processedList.length} of ${emailRange.length} customer profiles.\n\nClick OK to send email to those ${processedList.length} eligible player(s), or Cancel to stop here and send the email yourself.`,
        ui.ButtonSet.OK_CANCEL
      );

      if (confirmSend === ui.Button.CANCEL || confirmSend === ui.Button.CLOSE) {
        ui.alert(`Veteran tags ${actionVerb}, but players were not emailed. Please remember to email them manually (or run this script again) so players don't send last-minute emails of confusion!`);
        return;
      }
      try {
        Logger.log(`📧 [${timestamp}] Sending veteran emails to ${processedList.length} player(s)...`);
        sendVeteranEmail(processedList, sport, day, division, season, year, leadershipEmailAddress);
        Logger.log(`✅ [${timestamp}] Successfully sent emails`);
        ui.alert(`✅ Veteran tags ${actionVerb} successfully and ${processedList.length} players have been emailed with instructions!`);
      } catch(e) {
        const errorContext = {
          function: functionName,
          operation: 'sending_veteran_emails',
          emailCount: processedList.length,
          error: e.message,
          errorName: e.name,
          stack: e.stack
        };
        
        Logger.log(`❌ [${timestamp}] === ERROR sending veteran emails ===`);
        Logger.log(`   Operation: Sending emails to ${processedList.length} players`);
        Logger.log(`   Error: ${e.message}`);
        Logger.log(`   Error type: ${e.name}`);
        Logger.log(`   Stack: ${e.stack || 'No stack trace'}`);
        
        try {
          const DEBUG_EMAIL = PropertiesService.getScriptProperties().getProperty('DEBUG_EMAIL');
          if (DEBUG_EMAIL) {
            MailApp.sendEmail({
              to: DEBUG_EMAIL,
              subject: `🚨 ${functionName}: Email Sending Error`,
              htmlBody: `
                <h2>🚨 Email Sending Error in ${functionName}</h2>
                <p><strong>Timestamp:</strong> ${timestamp}</p>
                <p><strong>Operation:</strong> Sending veteran emails</p>
                <p><strong>Email Count:</strong> ${processedList.length}</p>
                <p><strong>Error:</strong> ${e.message}</p>
                <h3>Stack Trace:</h3>
                <pre>${e.stack || 'No stack trace'}</pre>
              `
            });
          }
        } catch (emailError) {
          Logger.log(`❌ Failed to send error email: ${emailError.message}`);
        }
        
        ui.alert(`⚠️ Not all players could be emailed! Please see the following errors: ${e.message}`);
      }
    } else {
      Logger.log(`✅ [${timestamp}] Operation completed successfully`);
      ui.alert(`✅ Veteran tags ${actionVerb} successfully ${actionPrep} ${processedList.length} customer profile(s)!`);
    }
    
  } catch (error) {
    const duration = new Date().getTime() - startTime;
    const errorContext = {
      function: functionName,
      operation: 'unexpected_error',
      durationMs: duration,
      context: context,
      error: error.message,
      errorName: error.name,
      stack: error.stack
    };
    
    Logger.log(`💥 [${timestamp}] === UNEXPECTED ERROR in ${functionName} ===`);
    Logger.log(`   Duration: ${duration}ms`);
    Logger.log(`   Operation: ${operation}`);
    Logger.log(`   Error: ${error.message}`);
    Logger.log(`   Error type: ${error.name}`);
    Logger.log(`   Stack trace: ${error.stack || 'No stack trace available'}`);
    Logger.log(`   Context: ${JSON.stringify(context, null, 2)}`);
    
    try {
      const DEBUG_EMAIL = PropertiesService.getScriptProperties().getProperty('DEBUG_EMAIL');
      if (DEBUG_EMAIL) {
        MailApp.sendEmail({
          to: DEBUG_EMAIL,
          subject: `🚨 ${functionName}: Unexpected Error`,
          htmlBody: `
            <h2>🚨 Unexpected Error in ${functionName}</h2>
            <p><strong>Timestamp:</strong> ${timestamp}</p>
            <p><strong>Duration:</strong> ${duration}ms</p>
            <p><strong>Operation:</strong> ${operation}</p>
            <p><strong>Error:</strong> ${error.message}</p>
            <p><strong>Error Type:</strong> ${error.name}</p>
            <h3>Stack Trace:</h3>
            <pre>${error.stack || 'No stack trace available'}</pre>
            <h3>Context:</h3>
            <pre>${JSON.stringify(context, null, 2)}</pre>
          `
        });
      }
    } catch (emailError) {
      Logger.log(`❌ Failed to send error email: ${emailError.message}`);
    }
    
    ui.alert(`❌ Unexpected error in ${functionName}: ${error.message}\n\nCheck the logs for details.`);
  } finally {
    const duration = new Date().getTime() - startTime;
    const endTimestamp = new Date().toISOString();
    Logger.log(`🏁 [${endTimestamp}] === EXITING ${functionName} ===`);
    Logger.log(`   Duration: ${duration}ms`);
    Logger.log(`   Processed: ${context.processedCount}/${context.emailCount}`);
    Logger.log(`   Errors: ${context.errorCount}`);
  }
}

// ✅ **Wrapper Functions**
function addVeteranTagToCustomerEmails() {
  processVeteranTags('add');
}

function removeVeteranTagFromCustomerEmails() {
  processVeteranTags('remove');
}
