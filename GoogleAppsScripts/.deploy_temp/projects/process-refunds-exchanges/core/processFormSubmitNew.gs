// /**
//  * ========================================================================
//  * UNIFIED FORM SUBMISSION HANDLER
//  * ========================================================================
//  * 
//  * This function supports 4 modes:
//  * - 'prodGs': Production mode using Google Apps Script logic (sends to Slack only)
//  * - 'debugGs': Debug mode using Google Apps Script logic (sends to Slack only + debug emails)
//  * - 'prodApi': Production mode using backend API (sends to Slack only)
//  * - 'debugApi': Debug mode using backend API (sends to Slack only + debug emails)
//  * 
//  * 🔧 CONFIGURATION: Change MODE in Utils.gs to switch between modes
//  * 
//  * ⚠️ IMPORTANT: All modes only send to Slack for manual processing.
//  *    Actual refund processing happens through Slack button interactions.
//  * ========================================================================
//  */

// function processFormSubmit(e) {
//   try {
//     // ========================================================================
//     // EXTRACT FORM DATA (common for all modes)
//     // ========================================================================
    
//     const getFieldValueByKeyword = (keyword) => {
//       const entry = Object.entries(e.namedValues).find(([key]) =>
//         key.toLowerCase().includes(keyword.toLowerCase())
//       );
//       return entry?.[1]?.[0]?.trim() || "";
//     };

//     const requestorName = {
//       first: getFieldValueByKeyword("first name"),
//       last: getFieldValueByKeyword("last name")
//     };

//     const requestorEmail = getFieldValueByKeyword("email");
//     const rawOrderNumber = getFieldValueByKeyword("order number");
//     const refundAnswer = getFieldValueByKeyword("do you want a refund");
//     const refundOrCredit = refundAnswer.toLowerCase().includes("refund") ? "refund" : "credit";
//     const requestNotes = getFieldValueByKeyword("note");
    
//     // Normalize order number (add # if missing) - using function from Utils.gs
//     const formattedOrderNumber = normalizeOrderNumber(rawOrderNumber);
    
//     // Debug logging for debug modes
//     if (MODE === 'debugGs' || MODE === 'debugApi') {
//       Logger.log(`🔍 [${MODE}] Form Data Extracted:`);
//       Logger.log(`   - Requestor: ${requestorName.first} ${requestorName.last}`);
//       Logger.log(`   - Email: ${requestorEmail}`);
//       Logger.log(`   - Order: ${rawOrderNumber} → ${formattedOrderNumber}`);
//       Logger.log(`   - Type: ${refundOrCredit}`);
//       Logger.log(`   - Notes: ${requestNotes}`);
//     }
    
//     // ========================================================================
//     // ROUTE TO APPROPRIATE HANDLER BASED ON MODE
//     // ========================================================================
    
//     if (MODE === 'prodGs' || MODE === 'debugGs') {
//       // Use original Google Apps Script logic (sends to Slack only)
//       processWithGoogleAppsScript(
//         formattedOrderNumber,
//         rawOrderNumber,
//         requestorName,
//         requestorEmail,
//         refundOrCredit,
//         requestNotes,
//         MODE === 'debugGs'
//       );
//     } else if (MODE === 'prodApi' || MODE === 'debugApi') {
//       // Use backend API to validate and send to Slack (no actual refund processing)
//       processWithBackendAPIValidation(
//         formattedOrderNumber,
//         rawOrderNumber,
//         requestorName,
//         requestorEmail,
//         refundOrCredit,
//         requestNotes,
//         MODE === 'debugApi'
//       );
//     } else {
//       throw new Error(`Invalid MODE: ${MODE}. Must be one of: prodGs, debugGs, prodApi, debugApi`);
//     }
    
//   } catch (error) {
//     const errorMessage = `Unexpected error in processFormSubmit [${MODE}]: ${error.toString()}`;
//     Logger.log(`⚠️ ${errorMessage}`);
    
//     // Send error notification to appropriate debug email
//     const debugEmail = (MODE === 'prodApi' || MODE === 'debugApi') ? DEBUG_EMAIL_2 : DEBUG_EMAIL;
    
//     MailApp.sendEmail({
//       to: debugEmail,
//       subject: `⚠️ BARS Refund Form - Unexpected Error [${MODE}]`,
//       htmlBody: `
//         <h3>⚠️ Unexpected Error in Form Processing</h3>
//         <p><strong>Mode:</strong> ${MODE}</p>
//         <p><strong>Error:</strong> ${errorMessage}</p>
//         <p><strong>Stack:</strong> <pre>${error.stack || 'No stack trace available'}</pre></p>
//         <p><strong>Form Data:</strong> <pre>${JSON.stringify(e.namedValues, null, 2)}</pre></p>
//         <p><strong>⚠️ Action Required:</strong> Check logs and process manually</p>
//       `
//     });
//   }
// }

// // ========================================================================
// // GOOGLE APPS SCRIPT PROCESSING FUNCTION
// // ========================================================================

// function processWithGoogleAppsScript(formattedOrderNumber, rawOrderNumber, requestorName, requestorEmail, refundOrCredit, requestNotes, isDebug) {
//   try {
//     if (isDebug) {
//       Logger.log(`🚀 [debugGs] Processing with Google Apps Script logic (Slack only)...`);
//     }
    
//     // Use the original Google Apps Script logic
//     const fetchedOrder = fetchShopifyOrderDetails({ orderName: formattedOrderNumber, email: null });
    
//     if (isDebug) {
//       Logger.log(`📋 [debugGs] Order fetched:`);
//       Logger.log(JSON.stringify(fetchedOrder, null, 2));
//     }
    
//     // Send to Slack using original logic
//     sendInitialRefundRequestToSlack(
//       fetchedOrder,
//       rawOrderNumber,
//       requestorName,
//       requestorEmail,
//       refundOrCredit,
//       requestNotes
//     );
    
//     if (isDebug) {
//       Logger.log(`✅ [debugGs] Successfully sent to Slack with Google Apps Script logic`);
      
//       // Send debug email notification
//       MailApp.sendEmail({
//         to: DEBUG_EMAIL,
//         subject: `✅ BARS Refund Form - Debug Processing Complete [debugGs]`,
//         htmlBody: `
//           <h3>✅ Debug Processing Complete - Google Apps Script Mode</h3>
//           <p><strong>Requestor:</strong> ${requestorName.first} ${requestorName.last}</p>
//           <p><strong>Email:</strong> ${requestorEmail}</p>
//           <p><strong>Order:</strong> ${formattedOrderNumber}</p>
//           <p><strong>Refund Type:</strong> ${refundOrCredit}</p>
//           <p><strong>Notes:</strong> ${requestNotes}</p>
//           <p><strong>✅ Status:</strong> Successfully sent to Slack for manual processing</p>
//           <p><strong>📝 Note:</strong> No automatic refund processing - awaiting Slack button interaction</p>
//         `
//       });
//     }
    
//   } catch (error) {
//     const errorMessage = `Error in Google Apps Script processing: ${error.toString()}`;
//     Logger.log(`❌ ${errorMessage}`);
    
//     MailApp.sendEmail({
//       to: DEBUG_EMAIL,
//       subject: `❌ BARS Refund Form - Google Apps Script Error [${isDebug ? 'debugGs' : 'prodGs'}]`,
//       htmlBody: `
//         <h3>❌ Google Apps Script Processing Failed</h3>
//         <p><strong>Mode:</strong> ${isDebug ? 'debugGs' : 'prodGs'}</p>
//         <p><strong>Error:</strong> ${errorMessage}</p>
//         <p><strong>Order:</strong> ${formattedOrderNumber}</p>
//         <p><strong>Requestor:</strong> ${requestorName.first} ${requestorName.last} (${requestorEmail})</p>
//         <p><strong>⚠️ Action Required:</strong> Manual processing needed</p>
//       `
//     });
//   }
// }

// // ========================================================================
// // BACKEND API VALIDATION FUNCTION (SLACK ONLY)
// // ========================================================================

// function processWithBackendAPIValidation(formattedOrderNumber, rawOrderNumber, requestorName, requestorEmail, refundOrCredit, requestNotes, isDebug) {
//   try {
//     if (isDebug) {
//       Logger.log(`🚀 [debugApi] Processing with Backend API validation (Slack only)...`);
//     }
    
//     // First, validate the order and email via backend API
//     const orderResult = getOrderDetails2(formattedOrderNumber, requestorEmail);
    
//     if (!orderResult.success) {
//       // Order not found or email doesn't match - send error notification
//       const errorMessage = `Order ${formattedOrderNumber} not found or email doesn't match ${requestorEmail}. Error: ${orderResult.message}`;
      
//       MailApp.sendEmail({
//         to: isDebug ? DEBUG_EMAIL_2 : DEBUG_EMAIL_2,
//         subject: `❌ BARS Refund Form - Order Validation Failed [${isDebug ? 'debugApi' : 'prodApi'}]`,
//         htmlBody: `
//           <h3>❌ Refund Request Failed - Order Validation Error</h3>
//           <p><strong>Mode:</strong> ${isDebug ? 'debugApi' : 'prodApi'}</p>
//           <p><strong>Requestor:</strong> ${requestorName.first} ${requestorName.last}</p>
//           <p><strong>Email:</strong> ${requestorEmail}</p>
//           <p><strong>Order:</strong> ${formattedOrderNumber}</p>
//           <p><strong>❌ Error:</strong> ${errorMessage}</p>
//           <p><strong>⚠️ Action Required:</strong> Verify order number and email address</p>
//         `
//       });
      
//       if (isDebug) {
//         Logger.log(`❌ [debugApi] Order validation failed: ${errorMessage}`);
//       }
//       return;
//     }
    
//     if (isDebug) {
//       Logger.log(`✅ [debugApi] Order validation successful`);
//       Logger.log(`📋 [debugApi] Order details:`, JSON.stringify(orderResult.data, null, 2));
//     }
    
//     // Now send to Slack using backend API (notification only, no processing)
//     const slackResult = sendRefundRequestToSlackViaAPI(
//       formattedOrderNumber,
//       requestorName,
//       requestorEmail,
//       refundOrCredit,
//       requestNotes,
//       orderResult.data
//     );
    
//     if (slackResult.success) {
//       // ✅ SUCCESS - Send success notification
//       if (isDebug) {
//         MailApp.sendEmail({
//           to: DEBUG_EMAIL_2,
//           subject: `✅ BARS Refund Form - API Validation Complete [debugApi]`,
//           htmlBody: `
//             <h3>✅ Debug Processing Complete - Backend API Mode</h3>
//             <p><strong>Requestor:</strong> ${requestorName.first} ${requestorName.last}</p>
//             <p><strong>Email:</strong> ${requestorEmail}</p>
//             <p><strong>Order:</strong> ${formattedOrderNumber}</p>
//             <p><strong>Refund Type:</strong> ${refundOrCredit}</p>
//             <p><strong>Notes:</strong> ${requestNotes}</p>
//             <p><strong>✅ Status:</strong> Successfully validated and sent to Slack</p>
//             <p><strong>📝 Note:</strong> No automatic refund processing - awaiting Slack button interaction</p>
//             <p><strong>🤖 Backend Features:</strong> Order validation, rich Slack formatting</p>
//           `
//         });
//       }
      
//       if (isDebug) {
//         Logger.log(`✅ [debugApi] Successfully sent to Slack via backend API`);
//       }
      
//     } else {
//       // ❌ FAILED - Send error notification
//       MailApp.sendEmail({
//         to: DEBUG_EMAIL_2,
//         subject: `❌ BARS Refund Form - Slack Notification Failed [${isDebug ? 'debugApi' : 'prodApi'}]`,
//         htmlBody: `
//           <h3>❌ Backend API Slack Notification Failed</h3>
//           <p><strong>Mode:</strong> ${isDebug ? 'debugApi' : 'prodApi'}</p>
//           <p><strong>Requestor:</strong> ${requestorName.first} ${requestorName.last}</p>
//           <p><strong>Email:</strong> ${requestorEmail}</p>
//           <p><strong>Order:</strong> ${formattedOrderNumber}</p>
//           <p><strong>Refund Type:</strong> ${refundOrCredit}</p>
//           <p><strong>Notes:</strong> ${requestNotes}</p>
//           <p><strong>❌ Error:</strong> ${slackResult.message}</p>
//           <p><strong>⚠️ Action Required:</strong> Manual Slack notification needed</p>
//         `
//       });
      
//       if (isDebug) {
//         Logger.log(`❌ [debugApi] Slack notification failed: ${slackResult.message}`);
//       }
//     }
    
//   } catch (error) {
//     const errorMessage = `Error in backend API validation: ${error.toString()}`;
//     Logger.log(`❌ ${errorMessage}`);
    
//     MailApp.sendEmail({
//       to: DEBUG_EMAIL_2,
//       subject: `❌ BARS Refund Form - API Validation Error [${isDebug ? 'debugApi' : 'prodApi'}]`,
//       htmlBody: `
//         <h3>❌ Backend API Validation Error</h3>
//         <p><strong>Mode:</strong> ${isDebug ? 'debugApi' : 'prodApi'}</p>
//         <p><strong>Error:</strong> ${errorMessage}</p>
//         <p><strong>Order:</strong> ${formattedOrderNumber}</p>
//         <p><strong>Requestor:</strong> ${requestorName.first} ${requestorName.last} (${requestorEmail})</p>
//         <p><strong>⚠️ Action Required:</strong> Check backend API and process manually</p>
//       `
//     });
//   }
// }

// // ========================================================================
// // SLACK NOTIFICATION VIA BACKEND API
// // ========================================================================

// function sendRefundRequestToSlackViaAPI(orderNumber, requestorName, requestorEmail, refundOrCredit, requestNotes, orderData) {
//   try {
//     Logger.log(`🚀 Sending refund request to Slack via backend API for order ${orderNumber}...`);
    
//     // Use the backend API to send Slack notification (not process refund)
//     const url = `${BACKEND_API_URL}/orders/${encodeURIComponent(orderNumber)}/slack-notification`;
    
//     const payload = {
//       requestor_name: requestorName,
//       requestor_email: requestorEmail,
//       refund_type: refundOrCredit,
//       notes: requestNotes,
//       order_data: orderData
//     };
    
//     const response = UrlFetchApp.fetch(url, {
//       method: 'POST',
//       headers: {
//         'Content-Type': 'application/json',
//         "ngrok-skip-browser-warning": "true"
//       },
//       payload: JSON.stringify(payload)
//     });

//     const responseData = JSON.parse(response.getContentText());
    
//     if (response.getResponseCode() === 200) {
//       Logger.log(`✅ Slack notification sent successfully`);
//       return {
//         success: true,
//         data: responseData
//       };
//     } else {
//       Logger.log(`❌ Slack notification failed: ${responseData.detail || 'Unknown error'}`);
//       return {
//         success: false,
//         message: responseData.detail || 'Failed to send Slack notification'
//       };
//     }
    
//   } catch (error) {
//     Logger.log(`Error sending Slack notification: ${error.toString()}`);
//     return {
//       success: false,
//       message: `Error sending Slack notification: ${error.toString()}`
//     };
//   }
// }

