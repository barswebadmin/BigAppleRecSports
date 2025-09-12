/**
 * HTTP POST endpoint
 * Expects JSON payload with { productUrl, sport, day, division, otherIdentifier }
 */
const doPost = (e) => {
  try {
    const body = e?.postData?.contents || '{}';
    const { productUrl, sport, day, division, otherIdentifier } = JSON.parse(body);

    const result = handleIncomingPostRequest({ productUrl, sport, day, division, otherIdentifier });

    return ContentService
      .createTextOutput(JSON.stringify({ status: 'ok', result }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    const errorMessage = String(err);
    const statusCode = errorMessage.includes('already exists') ? 409 : 500;

    const response = ContentService
      .createTextOutput(JSON.stringify({ status: 'error', message: errorMessage }))
      .setMimeType(ContentService.MimeType.JSON);

    // Note: Google Apps Script doesn't allow setting HTTP status codes directly
    // The backend will need to check the error message for "already exists"
    return response;
  }
};
