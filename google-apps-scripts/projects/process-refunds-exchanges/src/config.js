// =============================================================================
// PROJECT-SPECIFIC CONFIGURATION
// process-refunds-exchanges
// =============================================================================
//
// Environment-specific values live in Script Properties, not in code
// (Project Settings → Script Properties). Required keys:
//
//   SHEET_ID           refund-request spreadsheet id (e.g. 11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw)
//   SHEET_GID          refund-request tab gid        (e.g. 1435845892)
//   SHOPIFY_LOGIN_URL  customer login link for emails (e.g. https://shopify.com/55475535966/account)
//   DEBUG_EMAIL        where error/debug mail is sent (e.g. web@bigapplerecsports.com)
//   LAMBDA_REFUND_HANDLER_URL  ShopifyRefundHandler Function URL (read in sendLambdaWebhook.js)
//
// Read once at script load; the same global names are used across the project's
// src files (GAS implicit cross-file global scope).
// =============================================================================

const _SCRIPT_PROPS = PropertiesService.getScriptProperties();

const SHEET_ID = _SCRIPT_PROPS.getProperty('SHEET_ID');
const SHEET_GID = _SCRIPT_PROPS.getProperty('SHEET_GID');
const SHOPIFY_LOGIN_URL = _SCRIPT_PROPS.getProperty('SHOPIFY_LOGIN_URL');
const DEBUG_EMAIL = _SCRIPT_PROPS.getProperty('DEBUG_EMAIL');

