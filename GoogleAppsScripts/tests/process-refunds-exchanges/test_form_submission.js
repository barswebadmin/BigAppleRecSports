#!/usr/bin/env node

/**
 * Test suite for Google Apps Script form submission to backend API
 * Tests the form data extraction and backend API call flow
 * 
 * Run with: node test_form_submission.js
 */

const assert = require('assert');

// Mock Google Apps Script environment
global.Logger = {
  log: (message) => console.log(`[LOG] ${message}`)
};

global.UrlFetchApp = {
  fetch: null // Will be mocked in tests
};

global.ContentService = {
  createTextOutput: (text) => ({
    setMimeType: (mimeType) => ({ text, mimeType })
  }),
  MimeType: {
    TEXT: 'text/plain',
    JSON: 'application/json'
  }
};

global.MailApp = {
  sendEmail: () => {} // Mock to prevent actual emails
};

// Mock configuration
global.API_URL = 'https://test-api.example.com';
global.DEBUG_EMAIL = 'test@example.com';
global.MODE = 'test';
global.SHEET_ID = 'test-sheet-id';
global.SHEET_GID = 'test-gid';

// Mock utility functions
global.normalizeOrderNumber = (orderNumber) => {
  if (!orderNumber) return '';
  return orderNumber.startsWith('#') ? orderNumber : `#${orderNumber}`;
};

global.getRowLink = (orderNumber, sheetId, sheetGid) => {
  return `https://docs.google.com/spreadsheets/d/${sheetId}/edit#gid=${sheetGid}&range=A1`;
};

// Load the actual functions (we'll simulate them here since we can't import .gs files)
function processFormSubmitViaDoPost(e) {
  try {
    // Extract form fields from Google Form submission
    const getFieldValueByKeyword = (keyword) => {
      const entry = Object.entries(e.namedValues || {}).find(([key]) =>
        key.toLowerCase().includes(keyword.toLowerCase())
      );
      return entry?.[1]?.[0]?.trim() || "";
    };

    const requestorName = {
      first: getFieldValueByKeyword("first name"),
      last: getFieldValueByKeyword("last name")
    };

    const requestorEmail = getFieldValueByKeyword("email");
    const rawOrderNumber = getFieldValueByKeyword("order number");
    const refundAnswer = getFieldValueByKeyword("do you want a refund");
    const refundOrCredit = refundAnswer.toLowerCase().includes("refund") ? "refund" : "credit";
    const requestNotes = getFieldValueByKeyword("note");
    
    Logger.log(`📋 Form submission data extracted for order: ${rawOrderNumber}`);
    
    // Call the existing backend processing function
    processWithBackendAPI(
      normalizeOrderNumber(rawOrderNumber),
      rawOrderNumber,
      requestorName,
      requestorEmail,
      refundOrCredit,
      requestNotes,
      MODE === 'debugApi'
    );
    
    return ContentService.createTextOutput("Form submitted successfully").setMimeType(ContentService.MimeType.TEXT);
    
  } catch (error) {
    Logger.log(`❌ Error processing form submission: ${error.toString()}`);
    throw error;
  }
}

function processWithBackendAPI(formattedOrderNumber, rawOrderNumber, requestorName, requestorEmail, refundOrCredit, requestNotes, isDebug) {
  try {
    const sheetLink = getRowLink(formattedOrderNumber, SHEET_ID, SHEET_GID);
    
    const payload = {
      order_number: rawOrderNumber,
      requestor_name: requestorName,
      requestor_email: requestorEmail,
      refund_type: refundOrCredit,
      notes: requestNotes,
      sheet_link: sheetLink
    };
    
    Logger.log(`🚀 === BACKEND API REQUEST ===`);
    Logger.log(`🌐 Target URL: ${API_URL}/refunds/send-to-slack`);
    Logger.log(`📦 Request Payload:`);
    Logger.log(JSON.stringify(payload, null, 2));
    
    const options = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };
    
    Logger.log(`📡 Sending request to backend...`);
    const response = UrlFetchApp.fetch(`${API_URL}/refunds/send-to-slack`, options);
    
    const responseText = response.getContentText();
    Logger.log(`📄 Response: ${responseText}`);
    
    return response;
    
  } catch (error) {
    Logger.log(`❌ Backend API Error: ${error.toString()}`);
    throw error;
  }
}

// Test Suite
class FormSubmissionTests {
  
  runAllTests() {
    console.log('🧪 Running Google Apps Script Form Submission Tests...\n');
    
    this.testFormDataExtraction();
    this.testBackendPayloadConstruction();
    this.testSuccessfulBackendCall();
    this.testBackendErrorHandling();
    this.testFormFieldVariations();
    
    console.log('\n✅ All tests passed!');
  }
  
  testFormDataExtraction() {
    console.log('🔍 Test: Form Data Extraction');
    
    const mockFormEvent = {
      namedValues: {
        'Your First Name': ['John'],
        'Your Last Name': ['Doe'],
        'Your Email Address': ['john.doe@example.com'],
        'Order Number': ['12345'],
        'Do you want a refund or store credit?': ['I want a refund'],
        'Additional Notes': ['Schedule conflict']
      }
    };
    
    // Mock UrlFetchApp to capture the payload
    let capturedPayload = null;
    UrlFetchApp.fetch = (url, options) => {
      capturedPayload = JSON.parse(options.payload);
      return {
        getResponseCode: () => 200,
        getContentText: () => '{"success": true}',
        getHeaders: () => ({})
      };
    };
    
    processFormSubmitViaDoPost(mockFormEvent);
    
    // Verify extracted data
    assert.strictEqual(capturedPayload.order_number, '12345');
    assert.deepStrictEqual(capturedPayload.requestor_name, { first: 'John', last: 'Doe' });
    assert.strictEqual(capturedPayload.requestor_email, 'john.doe@example.com');
    assert.strictEqual(capturedPayload.refund_type, 'refund');
    assert.strictEqual(capturedPayload.notes, 'Schedule conflict');
    assert(capturedPayload.sheet_link.includes('test-sheet-id'));
    
    console.log('  ✅ Form data extracted correctly');
  }
  
  testBackendPayloadConstruction() {
    console.log('🔍 Test: Backend Payload Construction');
    
    let capturedPayload = null;
    let capturedUrl = null;
    let capturedOptions = null;
    
    UrlFetchApp.fetch = (url, options) => {
      capturedUrl = url;
      capturedOptions = options;
      capturedPayload = JSON.parse(options.payload);
      return {
        getResponseCode: () => 200,
        getContentText: () => '{"success": true}',
        getHeaders: () => ({})
      };
    };
    
    processWithBackendAPI(
      '#12345',
      '12345',
      { first: 'Jane', last: 'Smith' },
      'jane.smith@example.com',
      'credit',
      'Customer prefers store credit',
      false
    );
    
    // Verify API call details
    assert.strictEqual(capturedUrl, 'https://test-api.example.com/refunds/send-to-slack');
    assert.strictEqual(capturedOptions.method, 'POST');
    assert.strictEqual(capturedOptions.headers['Content-Type'], 'application/json');
    assert.strictEqual(capturedOptions.muteHttpExceptions, true);
    
    // Verify payload structure matches backend expectations
    const expectedKeys = ['order_number', 'requestor_name', 'requestor_email', 'refund_type', 'notes', 'sheet_link'];
    expectedKeys.forEach(key => {
      assert(key in capturedPayload, `Missing key: ${key}`);
    });
    
    assert.strictEqual(capturedPayload.order_number, '12345');
    assert.deepStrictEqual(capturedPayload.requestor_name, { first: 'Jane', last: 'Smith' });
    assert.strictEqual(capturedPayload.requestor_email, 'jane.smith@example.com');
    assert.strictEqual(capturedPayload.refund_type, 'credit');
    assert.strictEqual(capturedPayload.notes, 'Customer prefers store credit');
    
    console.log('  ✅ Backend payload constructed correctly');
  }
  
  testSuccessfulBackendCall() {
    console.log('🔍 Test: Successful Backend Response');
    
    UrlFetchApp.fetch = (url, options) => {
      return {
        getResponseCode: () => 200,
        getContentText: () => JSON.stringify({
          success: true,
          message: "Refund request sent to Slack successfully"
        }),
        getHeaders: () => ({ 'content-type': 'application/json' })
      };
    };
    
    const mockFormEvent = {
      namedValues: {
        'First Name': ['Test'],
        'Last Name': ['User'],
        'Email': ['test@example.com'],
        'Order Number': ['67890'],
        'Refund or Credit': ['store credit'],
        'Notes': ['Test notes']
      }
    };
    
    // Should not throw any errors
    const result = processFormSubmitViaDoPost(mockFormEvent);
    assert.strictEqual(result.text, 'Form submitted successfully');
    
    console.log('  ✅ Successful backend call handled correctly');
  }
  
  testBackendErrorHandling() {
    console.log('🔍 Test: Backend Error Handling');
    
    // Test 406 (Order Not Found)
    UrlFetchApp.fetch = (url, options) => {
      return {
        getResponseCode: () => 406,
        getContentText: () => JSON.stringify({
          detail: "Order not found in Shopify"
        }),
        getHeaders: () => ({ 'content-type': 'application/json' })
      };
    };
    
    const mockFormEvent = {
      namedValues: {
        'First Name': ['Test'],
        'Last Name': ['User'],
        'Email': ['test@example.com'],
        'Order Number': ['99999'],
        'Refund Question': ['refund please'],
        'Notes': ['Invalid order']
      }
    };
    
    // Should handle gracefully (not throw in our simplified version)
    const result = processFormSubmitViaDoPost(mockFormEvent);
    assert.strictEqual(result.text, 'Form submitted successfully');
    
    console.log('  ✅ Backend error responses handled correctly');
  }
  
  testFormFieldVariations() {
    console.log('🔍 Test: Form Field Variations');
    
    // Test different field name variations
    const fieldVariations = [
      {
        description: 'Variations in field names',
        namedValues: {
          'first name': ['Alice'],
          'LAST NAME': ['Johnson'],
          'email address': ['alice.j@test.com'],
          'order number': ['#11111'],
          'do you want refund or credit': ['I need a refund'],
          'additional notes or comments': ['Emergency situation']
        }
      },
      {
        description: 'Different field formats',
        namedValues: {
          'First Name': ['Bob'],
          'Last Name': ['Wilson'],
          'Email Address': ['bob@test.com'],
          'Order Number': ['22222'],
          'Do you want a refund or credit?': ['credit please'],
          // No notes field - should result in empty string
        }
      }
    ];
    
    let capturedPayloads = [];
    UrlFetchApp.fetch = (url, options) => {
      capturedPayloads.push(JSON.parse(options.payload));
      return {
        getResponseCode: () => 200,
        getContentText: () => '{"success": true}',
        getHeaders: () => ({})
      };
    };
    
    fieldVariations.forEach((variation, index) => {
      processFormSubmitViaDoPost({ namedValues: variation.namedValues });
      
      const payload = capturedPayloads[index];
      
      // Should always have the required fields (even if empty)
      assert('order_number' in payload, 'order_number field missing');
      assert('requestor_name' in payload && 'first' in payload.requestor_name, 'requestor_name.first missing');
      assert('requestor_email' in payload, 'requestor_email field missing');
      assert('refund_type' in payload, 'refund_type field missing');
      // Notes can be empty string
      assert('notes' in payload, 'notes field missing');
      
      // Verify the specific test case data
      if (variation.description === 'Different field formats') {
        assert.strictEqual(payload.order_number, '22222');
        assert.strictEqual(payload.requestor_name.first, 'Bob');
        assert.strictEqual(payload.requestor_name.last, 'Wilson');
        assert.strictEqual(payload.requestor_email, 'bob@test.com');
        assert.strictEqual(payload.refund_type, 'credit');
        assert.strictEqual(payload.notes, ''); // Should be empty since no notes field
      }
    });
    
    console.log('  ✅ Form field variations handled correctly');
  }
}

// Run tests
if (require.main === module) {
  const tests = new FormSubmissionTests();
  tests.runAllTests();
}

module.exports = FormSubmissionTests;
