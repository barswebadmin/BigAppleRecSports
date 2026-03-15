// sendToLambda.js — fire-and-forget POST to Lambda after form processing

const LAMBDA_URL = "https://tn2iit2rvsjqpqr6yhnsufefle0cfayt.lambda-url.us-east-1.on.aws/";

/**
 * POST form result to Lambda. Called after calendar + email work is done.
 *
 * @param {object} payload
 * @param {string}   payload.firstName
 * @param {string}   payload.lastName
 * @param {string}   payload.email
 * @param {boolean}  payload.success          - true if all invites added + email sent
 * @param {string[]} payload.confirmedSessions - sessions successfully added to calendar
 * @param {string[]} payload.selectedSessions  - sessions the user originally selected
 * @param {string[]} [payload.errors]          - any error messages if success is false
 * @param {object}   [payload.rawFormResponse] - full serialized form response for debugging
 */
export function sendToLambda(payload) {
  console.log("sendToLambda →", JSON.stringify(payload, null, 2));

  let resp;
  try {
    resp = UrlFetchApp.fetch(LAMBDA_URL, {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify(payload),
      muteHttpExceptions: true,
    });
  } catch (err) {
    console.error("sendToLambda: network error:", err.message);
    return;
  }

  console.log("sendToLambda ← status:", resp.getResponseCode());
  console.log("sendToLambda ← body:", resp.getContentText());
}
