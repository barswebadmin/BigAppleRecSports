/**
 * ========================================================================
 * LAMBDA WEBHOOK — POST refund request to ShopifyRefundHandler lambda
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
 * Build the JSON body the lambda's `RefundRequest` pydantic model expects.
 *
 * Field map ↔ pydantic:
 *   order_number      : str           (with or without leading '#')
 *   email_address     : EmailStr      (must be a valid email)
 *   first_name        : str
 *   last_name         : str
 *   refund_or_credit  : str           ("refund" | "credit")
 *   created_at        : datetime|null (ISO 8601 with Z → TZ-aware UTC)
 *   notes             : str|null
 */
function buildLambdaRefundPayload(formattedOrderNumber, rawOrderNumber, requestorName, requestorEmail, refundOrCredit, requestNotes, requestSubmittedAt) {
  return {
    // The lambda's get_order_by_name normalizes either "1234" or "#1234"; we
    // send the formatted ("#"-prefixed) version since that's what Shopify's
    // search-by-name expects.
    order_number: formattedOrderNumber || rawOrderNumber || '',
    email_address: (requestorEmail || '').trim(),
    first_name: (requestorName && requestorName.first || '').trim(),
    last_name: (requestorName && requestorName.last || '').trim(),
    refund_or_credit: refundOrCredit || 'credit',
    // requestSubmittedAt is already an ISO 8601 string built via
    // `new Date(...).toISOString()` in processFormSubmit.js — TZ-aware UTC.
    // The lambda treats a naive string as America/New_York, but Z-suffixed
    // strings pass through unchanged.
    created_at: requestSubmittedAt || null,
    notes: requestNotes || null,
  };
}

/**
 * POST a refund-request payload to the ShopifyRefundHandler lambda.
 *
 * Pure transport: caller builds the payload (typically via
 * ``buildLambdaRefundPayload`` to match the pydantic ``RefundRequest`` model)
 * and we just POST it. Mirrors the AWS-side ``slack_sink.maybe_post_to_slack``:
 * one function, takes a dict, fires it off.
 *
 * Never throws — logs the outcome and emails DEBUG_EMAIL on failure. The
 * existing backend flow MUST continue to run even if this errors.
 *
 * @param {Object} payload - JSON-serializable payload matching RefundRequest
 * @returns {{status: number, body: string} | null}
 */
function postRefundRequestToLambda(payload) {
  // Property key is inlined intentionally — no top-level constants in this file.
  // Read from Script Properties at call time so a property update lands without
  // needing a redeploy / cold restart of the script.
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

    // Non-2xx → log loudly so we notice during early rollout.
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
 * Manual end-to-end test using REAL data from the most recent form submission
 * (last row in the refund-request sheet where column A is non-empty).
 *
 * Picks the same fields ``processFormSubmit`` does — keyword-matched against
 * the form's column headers — so the synthetic payload matches what a real
 * trigger fires. Useful for replaying the latest submission through the
 * lambda without touching the form.
 *
 * Run from the Apps Script editor: select ``testLambdaWebhookFromLastRow``
 * in the function dropdown → Run. Watch the execution log.
 */
function testLambdaWebhookFromLastRow() {
  const sheet = _findSheetByGid(SHEET_ID, SHEET_GID);
  const lastRow = _findLastRowWithColA(sheet);
  if (!lastRow) {
    Logger.log('⛔ No data rows found — sheet only has a header or is empty');
    return;
  }

  const { rowNumber, namedValues, headers, values } = _readRowAsNamedValues(sheet, lastRow);
  Logger.log(`📋 Replaying row ${rowNumber} (most recent submission with col A populated)`);
  Logger.log(`   Headers: ${headers.join(' | ')}`);
  Logger.log(`   Values:  ${values.map((v) => String(v).slice(0, 60)).join(' | ')}`);

  // Field extraction mirrors processFormSubmit.js exactly — same keyword matches,
  // same normalization. Diverging here would make this test less load-bearing.
  const requestorName = {
    first: _pickFieldByKeyword(namedValues, 'first name'),
    last: _pickFieldByKeyword(namedValues, 'last name'),
  };
  const requestorEmail = _pickFieldByKeyword(namedValues, 'email');
  const rawOrderNumber = _pickFieldByKeyword(namedValues, 'order number');
  const refundAnswer = _pickFieldByKeyword(namedValues, 'do you want a refund');
  const refundOrCredit = refundAnswer.toLowerCase().includes('refund') ? 'refund' : 'credit';
  const requestNotes = _pickFieldByKeyword(namedValues, 'note');

  // Timestamp lives in column A — header is typically "Timestamp" but read it
  // by position too just in case it's been renamed.
  const tsRaw = _pickFieldByKeyword(namedValues, 'timestamp') || values[0];
  const submittedAt = tsRaw instanceof Date
    ? tsRaw.toISOString()
    : tsRaw ? new Date(tsRaw).toISOString() : new Date().toISOString();

  const formattedOrderNumber = normalizeOrderNumber(rawOrderNumber);

  Logger.log(`📦 Extracted payload:
   name:       ${requestorName.first} ${requestorName.last}
   email:      ${requestorEmail}
   order:      ${rawOrderNumber} → ${formattedOrderNumber}
   type:       ${refundOrCredit}
   notes:      ${requestNotes ? requestNotes.slice(0, 80) : '(none)'}
   submitted:  ${submittedAt}`);

  const result = postRefundRequestToLambda(
    buildLambdaRefundPayload(
      formattedOrderNumber, rawOrderNumber, requestorName, requestorEmail,
      refundOrCredit, requestNotes, submittedAt,
    )
  );
  _logLambdaResult(result);
}

/**
 * Synthetic-payload test — useful for "is the lambda reachable / does its
 * deployed code parse the schema" smoke check without depending on the
 * spreadsheet state. Edit constants to point at any order #.
 */
function testLambdaWebhook() {
  const TEST_ORDER_NUMBER = '#1234';                            // ← real BARS order
  const TEST_EMAIL = 'joe.randazzo@gendigital.com';             // ← your email
  const TEST_FIRST_NAME = 'Joe';
  const TEST_LAST_NAME = 'Randazzo';
  const TEST_REFUND_OR_CREDIT = 'credit';                       // "refund" | "credit"

  Logger.log('🧪 Running testLambdaWebhook with synthetic payload');
  const result = postRefundRequestToLambda(
    buildLambdaRefundPayload(
      TEST_ORDER_NUMBER,
      TEST_ORDER_NUMBER.replace(/^#/, ''),
      { first: TEST_FIRST_NAME, last: TEST_LAST_NAME },
      TEST_EMAIL,
      TEST_REFUND_OR_CREDIT,
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

function _findLastRowWithColA(sheet) {
  // sheet.getLastRow() can over-report (counts trailing blanks left by deletes).
  // Walk backward from there until column A has a value.
  let row = sheet.getLastRow();
  while (row > 1) {
    const colA = sheet.getRange(row, 1).getValue();
    if (colA !== '' && colA !== null && colA !== undefined) return row;
    row--;
  }
  return null;
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
      Logger.log(`   refund_to_original: ${parsed.estimated_refund_to_original.message}`);
    }
    if (parsed.estimated_store_credit) {
      Logger.log(`   store_credit: ${parsed.estimated_store_credit.message}`);
    }
  } catch (e) {
    Logger.log(`(non-JSON body) ${result.body}`);
  }
}
