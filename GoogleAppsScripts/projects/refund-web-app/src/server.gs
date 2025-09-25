var MODE = 'dev';
var NGROK_URL = 'https://9f09dea8f27c.ngrok-free.app';

/**
 * Web app entrypoint: serves HTML UI
 */
/** biome-ignore-all lint/correctness/noUnusedVariables: <these are called by the web app> */
function doGet() {
  return HtmlService
    .createHtmlOutputFromFile('index')
    .setTitle('Refund Web App')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function getBackendBaseUrl_() {
  var props = PropertiesService.getScriptProperties();
  var url = MODE === 'dev' ? NGROK_URL : props.getProperty('BACKEND_API_URL_PROD');
  if (!url) {
    throw new Error('Missing BACKEND_API_URL script property');
  }
  return url.replace(/\/$/, '');
}

/**
 * Calls backend to get refund quote
 * @param {string} email
 * @param {string} orderNumber
 * @return {Object}
 */
function getRefundQuote(email, orderNumber) {
  var url = getBackendBaseUrl_() + '/refunds/request';
  var payload = {
    email: email,
    order_number: orderNumber
  };
  var res = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });
  var status = res.getResponseCode();
  if (status < 200 || status >= 300) {
    throw new Error('Quote failed: ' + status + ' ' + res.getContentText());
  }
  return JSON.parse(res.getContentText());
}

/**
 * Calls backend to process refund
 * @param {Object} quoteContext e.g. { email, order_number, quote_id }
 * @return {Object}
 */
function processRefund(quoteContext) {
  var url = getBackendBaseUrl_() + '/refunds/process';
  var res = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(quoteContext),
    muteHttpExceptions: true
  });
  var status = res.getResponseCode();
  if (status < 200 || status >= 300) {
    throw new Error('Process failed: ' + status + ' ' + res.getContentText());
  }
  return JSON.parse(res.getContentText());
}


