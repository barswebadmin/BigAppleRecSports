/**
 * ========================================================================
 * SEND LAMBDA WEBHOOK — POST refund request to ShopifyRefundHandler lambda
 * ========================================================================
 *
 * Fires alongside the existing backend processing. Reads the lambda's
 * Function URL from Script Properties (NOT in code) so dev/prod URLs aren't
 * checked in. No-ops with a Logger warning if the property isn't set, so
 * deploys before the URL is configured are safe.
 *
 * Set the URL in Project Settings → Script Properties:
 *     Key:   LAMBDA_REFUND_HANDLER_URL
 *     Value: https://<id>.lambda-url.us-east-1.on.aws/
 * ========================================================================
 */

/**
 * Parse a raw timestamp string to ISO 8601. Returns null on bad input or missing value.
 * Used by processFormSubmit.js and doPost.js (GAS global scope).
 */
function tryParseIso(raw) {
  if (!raw) return null;
  try { return new Date(raw).toISOString(); } catch (_) { return null; }
}

/**
 * Build the JSON body the lambda's `RefundRequest` pydantic model expects.
 *
 * Canonical (snake_case) field map ↔ pydantic:
 *   action        : "evaluate_refund"  (route discriminator)
 *   order_number  : str                (with or without leading '#')
 *   email         : str                (surfaced as a warning if blank/invalid)
 *   first_name    : str
 *   last_name     : str
 *   refund_to     : str                ("original_method" | "store_credit")
 *   submitted_at  : datetime|null      (ISO 8601 with Z → TZ-aware UTC)
 *   notes         : str|null
 *
 * Callers are responsible for canonicalizing `refundTo` before calling.
 */
function buildLambdaRefundPayload(formattedOrderNumber, rawOrderNumber, requestorName, requestorEmail, refundTo, requestNotes, requestSubmittedAt) {
  return {
    action: 'evaluate_refund',
    // The lambda normalizes "1234" or "#1234"; send the formatted ("#"-prefixed)
    // version since that's what Shopify's search-by-name expects.
    order_number: formattedOrderNumber || rawOrderNumber || '',
    email: (requestorEmail || '').trim(),
    first_name: (requestorName && requestorName.first || '').trim(),
    last_name: (requestorName && requestorName.last || '').trim(),
    refund_to: refundTo,
    submitted_at: requestSubmittedAt || null,
    notes: requestNotes || null,
  };
}

/**
 * POST a refund-request payload to the ShopifyRefundHandler lambda.
 *
 * Pure transport: caller builds the payload (typically via
 * ``buildLambdaRefundPayload`` to match the pydantic ``RefundRequest`` model)
 * and we just POST it. Never throws — logs the outcome and emails DEBUG_EMAIL
 * on failure so the existing backend flow continues even if this errors.
 *
 * @param {Object} payload - JSON-serializable payload matching RefundRequest
 * @returns {{status: number, body: string} | null}
 */
function sendLambdaWebhook(payload) {
  const propKey = 'LAMBDA_REFUND_HANDLER_URL';
  const url = PropertiesService.getScriptProperties().getProperty(propKey);
  if (!url) {
    Logger.log(`⚠️ ${propKey} not set in Script Properties — skipping lambda webhook`);
    return null;
  }

  Logger.log(`📤 POSTing refund request to lambda → ${url}`);
  Logger.log(`   Payload: ${JSON.stringify(payload, null, 2)}`);

  try {
    const res = UrlFetchApp.fetch(url, {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify(payload),
      muteHttpExceptions: true,
    });
    const status = res.getResponseCode();
    const body = res.getContentText();
    Logger.log(`📥 Lambda responded ${status}: ${body}`);

    if (status < 200 || status >= 300) {
      Logger.log(`❌ Lambda webhook returned ${status} — backend flow still proceeded`);
      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: `⚠️ BARS Refund Lambda — non-2xx response (${status})`,
        htmlBody: `
          <h3>Lambda webhook returned non-2xx</h3>
          <p><strong>Status:</strong> ${status}</p>
          <p><strong>URL:</strong> ${url}</p>
          <p><strong>Payload:</strong> <pre>${JSON.stringify(payload, null, 2)}</pre></p>
          <p><strong>Response body:</strong> <pre>${body}</pre></p>
        `,
      });
    }

    return { status, body };
  } catch (error) {
    Logger.log(`❌ Lambda webhook failed: ${error.toString()}`);
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: '⚠️ BARS Refund Lambda — request threw',
      htmlBody: `
        <h3>Lambda webhook threw</h3>
        <p><strong>Error:</strong> ${error.toString()}</p>
        <p><strong>Stack:</strong> <pre>${error.stack || '(none)'}</pre></p>
        <p><strong>Payload:</strong> <pre>${JSON.stringify(payload, null, 2)}</pre></p>
      `,
    });
    return null;
  }
}

/**
 * Manual end-to-end test using REAL data from the sheet.
 *
 * Set TEST_ROW_NUMBER to any row you want to replay, then run this function
 * from the Apps Script editor: select ``testSendLambdaWebhookFromRow`` in the
 * function dropdown → Run. Watch the execution log.
 */
function testSendLambdaWebhookFromRow() {
  const TEST_ROW_NUMBER = 2; // ← set to the row number you want to replay (1 = header)

  const sheet = _findSheetByGid(SHEET_ID, SHEET_GID);
  const { rowNumber, namedValues, headers, values } = _readRowAsNamedValues(sheet, TEST_ROW_NUMBER);
  Logger.log(`📋 Replaying row ${rowNumber}`);
  Logger.log(`   Headers: ${headers.join(' | ')}`);
  Logger.log(`   Values:  ${values.map((v) => String(v).slice(0, 60)).join(' | ')}`);

  const requestorName = {
    first: _pickFieldByKeyword(namedValues, 'first name'),
    last: _pickFieldByKeyword(namedValues, 'last name'),
  };
  const requestorEmail = _pickFieldByKeyword(namedValues, 'email');
  const rawOrderNumber = _pickFieldByKeyword(namedValues, 'order number');
  const refundAnswer = _pickFieldByKeyword(namedValues, 'do you want a refund');
  const refundTo = refundAnswer.toLowerCase().includes('refund') ? 'original_method' : 'store_credit';
  const requestNotes = _pickFieldByKeyword(namedValues, 'note');
  const tsRaw = _pickFieldByKeyword(namedValues, 'timestamp') || values[0];
  const submittedAt = tryParseIso(tsRaw) || new Date().toISOString();
  const formattedOrderNumber = normalizeOrderNumber(rawOrderNumber);

  Logger.log(`📦 Extracted payload:
   name:       ${requestorName.first} ${requestorName.last}
   email:      ${requestorEmail}
   order:      ${rawOrderNumber} → ${formattedOrderNumber}
   type:       ${refundTo}
   notes:      ${requestNotes ? requestNotes.slice(0, 80) : '(none)'}
   submitted:  ${submittedAt}`);

  const result = sendLambdaWebhook(
    buildLambdaRefundPayload(
      formattedOrderNumber, rawOrderNumber, requestorName, requestorEmail,
      refundTo, requestNotes, submittedAt,
    )
  );
  _logLambdaResult(result);
}

/**
 * Synthetic-payload test — smoke check that the lambda is reachable and
 * parses the schema without depending on the spreadsheet state.
 * Edit the constants below to point at any real order.
 */
function testSendLambdaWebhook() {
  const TEST_ORDER_NUMBER = '#1234';                            // ← real BARS order
  const TEST_EMAIL = 'joe.randazzo@gendigital.com';             // ← your email
  const TEST_FIRST_NAME = 'Joe';
  const TEST_LAST_NAME = 'Randazzo';
  const TEST_REFUND_TO = 'store_credit';                        // "original_method" | "store_credit"

  Logger.log('🧪 Running testSendLambdaWebhook with synthetic payload');
  const result = sendLambdaWebhook(
    buildLambdaRefundPayload(
      TEST_ORDER_NUMBER,
      TEST_ORDER_NUMBER.replace(/^#/, ''),
      { first: TEST_FIRST_NAME, last: TEST_LAST_NAME },
      TEST_EMAIL,
      TEST_REFUND_TO,
      'manual test from Apps Script editor',
      new Date().toISOString(),
    )
  );
  _logLambdaResult(result);
}

// ── Helpers shared by both test functions ────────────────────────────────────

function _findSheetByGid(spreadsheetId, gid) {
  const target = Number(gid);
  const sheet = SpreadsheetApp.openById(spreadsheetId).getSheets().find((s) => s.getSheetId() === target);
  if (!sheet) {
    throw new Error(`No sheet with gid=${gid} in spreadsheet ${spreadsheetId}`);
  }
  return sheet;
}

function _readRowAsNamedValues(sheet, rowNumber) {
  const lastCol = sheet.getLastColumn();
  const headers = sheet.getRange(1, 1, 1, lastCol).getValues()[0].map(String);
  const values = sheet.getRange(rowNumber, 1, 1, lastCol).getValues()[0];
  const namedValues = {};
  for (let i = 0; i < headers.length; i++) {
    namedValues[headers[i]] = [values[i]];
  }
  return { rowNumber, namedValues, headers, values };
}

function _pickFieldByKeyword(namedValues, keyword) {
  const needle = keyword.toLowerCase();
  const entry = Object.entries(namedValues).find(([k]) => k.toLowerCase().includes(needle));
  const v = entry && entry[1] && entry[1][0];
  return v != null && v !== '' ? String(v).trim() : '';
}

function _logLambdaResult(result) {
  if (!result) {
    Logger.log('⛔ No result — either LAMBDA_REFUND_HANDLER_URL is unset or the request threw. Check the lines above.');
    return;
  }
  Logger.log(`✅ Lambda returned ${result.status}`);
  try {
    const parsed = JSON.parse(result.body);
    Logger.log(`📋 Parsed response keys: ${Object.keys(parsed).join(', ')}`);
    Logger.log(`   order_found: ${parsed.order_found}`);
    Logger.log(`   validation_passed: ${parsed.validation_passed}`);
    Logger.log(`   warnings: ${JSON.stringify(parsed.warnings || [])}`);
    Logger.log(`   sport/day/division: ${parsed.sport} / ${parsed.day} / ${parsed.division}`);
    if (parsed.estimated_refund_to_original) {
      Logger.log(`   original_method: ${parsed.estimated_refund_to_original.message}`);
    }
    if (parsed.estimated_store_credit) {
      Logger.log(`   store_credit: ${parsed.estimated_store_credit.message}`);
    }
  } catch (e) {
    Logger.log(`(non-JSON body) ${result.body}`);
  }
}
