/**
 * Tests for go-live request functionality
 * Tests response handling, message parsing, and UI alerts based on response codes
 */

/**
 * Test successful go-live request (200-299 response codes)
 */
function testGoLiveRequest_Success() {
  console.log('Testing go-live request success scenarios...');
  
  const testCases = [
    {
      name: '200 OK with message',
      responseCode: 200,
      responseText: '{"message": "Product successfully scheduled for go-live at 2025-01-15T10:00:00Z"}',
      expectedMessage: 'Product successfully scheduled for go-live at 2025-01-15T10:00:00Z',
      shouldUncheckCheckbox: false
    },
    {
      name: '201 Created with message',
      responseCode: 201,
      responseText: '{"message": "Product created and scheduled for publication"}',
      expectedMessage: 'Product created and scheduled for publication',
      shouldUncheckCheckbox: false
    },
    {
      name: '204 No Content with empty response',
      responseCode: 204,
      responseText: '',
      expectedMessage: 'No message provided',
      shouldUncheckCheckbox: false
    },
    {
      name: '200 OK with no message field',
      responseCode: 200,
      responseText: '{"status": "success", "data": {}}',
      expectedMessage: 'No message provided',
      shouldUncheckCheckbox: false
    }
  ];
  
  testCases.forEach(testCase => {
    console.log(`  Testing: ${testCase.name}`);
    
    const result = parseGoLiveResponse_(testCase.responseCode, testCase.responseText);
    
    if (result.success === true && 
        result.message === testCase.expectedMessage && 
        result.shouldUncheckCheckbox === testCase.shouldUncheckCheckbox) {
      console.log(`    ✅ ${testCase.name} passed`);
    } else {
      console.log(`    ❌ ${testCase.name} failed. Expected: success=true, message="${testCase.expectedMessage}", uncheck=${testCase.shouldUncheckCheckbox}. Got: success=${result.success}, message="${result.message}", uncheck=${result.shouldUncheckCheckbox}`);
    }
  });
}

/**
 * Test failed go-live request (400+ response codes)
 */
function testGoLiveRequest_Failure() {
  console.log('Testing go-live request failure scenarios...');
  
  const testCases = [
    {
      name: '400 Bad Request with error message',
      responseCode: 400,
      responseText: '{"message": "Invalid product URL provided"}',
      expectedMessage: 'Invalid product URL provided',
      shouldUncheckCheckbox: true
    },
    {
      name: '404 Not Found with error message',
      responseCode: 404,
      responseText: '{"message": "Product not found in Shopify"}',
      expectedMessage: 'Product not found in Shopify',
      shouldUncheckCheckbox: true
    },
    {
      name: '500 Internal Server Error with error message',
      responseCode: 500,
      responseText: '{"message": "Internal server error occurred"}',
      expectedMessage: 'Internal server error occurred',
      shouldUncheckCheckbox: true
    },
    {
      name: '400 Bad Request with no message field',
      responseCode: 400,
      responseText: '{"error": "Bad request"}',
      expectedMessage: 'No message provided',
      shouldUncheckCheckbox: true
    },
    {
      name: '500 Internal Server Error with plain text response',
      responseCode: 500,
      responseText: 'Internal Server Error',
      expectedMessage: 'Internal Server Error',
      shouldUncheckCheckbox: true
    }
  ];
  
  testCases.forEach(testCase => {
    console.log(`  Testing: ${testCase.name}`);
    
    const result = parseGoLiveResponse_(testCase.responseCode, testCase.responseText);
    
    if (result.success === false && 
        result.message === testCase.expectedMessage && 
        result.shouldUncheckCheckbox === testCase.shouldUncheckCheckbox) {
      console.log(`    ✅ ${testCase.name} passed`);
    } else {
      console.log(`    ❌ ${testCase.name} failed. Expected: success=false, message="${testCase.expectedMessage}", uncheck=${testCase.shouldUncheckCheckbox}. Got: success=${result.success}, message="${result.message}", uncheck=${result.shouldUncheckCheckbox}`);
    }
  });
}

/**
 * Test edge cases and unexpected response codes
 */
function testGoLiveRequest_EdgeCases() {
  console.log('Testing go-live request edge cases...');
  
  const testCases = [
    {
      name: '300 Multiple Choices (redirect)',
      responseCode: 300,
      responseText: '{"message": "Multiple choices available"}',
      expectedMessage: 'Unexpected response code 300: Multiple choices available',
      shouldUncheckCheckbox: true
    },
    {
      name: '301 Moved Permanently',
      responseCode: 301,
      responseText: '{"message": "Resource moved"}',
      expectedMessage: 'Unexpected response code 301: Resource moved',
      shouldUncheckCheckbox: true
    },
    {
      name: '302 Found (redirect)',
      responseCode: 302,
      responseText: '{"message": "Resource found"}',
      expectedMessage: 'Unexpected response code 302: Resource found',
      shouldUncheckCheckbox: true
    },
    {
      name: 'Invalid JSON response',
      responseCode: 200,
      responseText: 'Invalid JSON {',
      expectedMessage: 'Invalid JSON {',
      shouldUncheckCheckbox: false
    },
    {
      name: 'Null response text',
      responseCode: 200,
      responseText: null,
      expectedMessage: 'No message provided',
      shouldUncheckCheckbox: false
    },
    {
      name: 'Empty response text',
      responseCode: 200,
      responseText: '',
      expectedMessage: 'No message provided',
      shouldUncheckCheckbox: false
    }
  ];
  
  testCases.forEach(testCase => {
    console.log(`  Testing: ${testCase.name}`);
    
    const result = parseGoLiveResponse_(testCase.responseCode, testCase.responseText);
    
    if (result.message === testCase.expectedMessage && 
        result.shouldUncheckCheckbox === testCase.shouldUncheckCheckbox) {
      console.log(`    ✅ ${testCase.name} passed`);
    } else {
      console.log(`    ❌ ${testCase.name} failed. Expected: message="${testCase.expectedMessage}", uncheck=${testCase.shouldUncheckCheckbox}. Got: message="${result.message}", uncheck=${result.shouldUncheckCheckbox}`);
    }
  });
}

/**
 * Test payload construction for go-live request
 */
function testGoLiveRequest_Payload() {
  console.log('Testing go-live request payload construction...');
  
  const testCases = [
    {
      name: 'Valid product URL and date',
      productUrl: 'https://shop.example.com/products/test-product',
      goLiveTime: new Date('2025-01-15T10:00:00Z'),
      expectedPayload: {
        productUrl: 'https://shop.example.com/products/test-product',
        goLiveTime: '2025-01-15T10:00:00.000Z'
      }
    },
    {
      name: 'Valid product URL and different date',
      productUrl: 'https://shopify.com/products/another-product',
      goLiveTime: new Date('2025-02-20T14:30:00Z'),
      expectedPayload: {
        productUrl: 'https://shopify.com/products/another-product',
        goLiveTime: '2025-02-20T14:30:00.000Z'
      }
    }
  ];
  
  testCases.forEach(testCase => {
    console.log(`  Testing: ${testCase.name}`);
    
    const payload = constructGoLivePayload_(testCase.productUrl, testCase.goLiveTime);
    
    if (JSON.stringify(payload) === JSON.stringify(testCase.expectedPayload)) {
      console.log(`    ✅ ${testCase.name} passed`);
    } else {
      console.log(`    ❌ ${testCase.name} failed. Expected: ${JSON.stringify(testCase.expectedPayload)}. Got: ${JSON.stringify(payload)}`);
    }
  });
}

/**
 * Test checkbox validation logic
 */
function testCheckboxValidation() {
  console.log('Testing checkbox validation logic...');
  
  const testCases = [
    {
      name: 'All required fields present',
      productUrl: 'https://shop.example.com/products/test',
      earlyVariantId: 'gid://shopify/ProductVariant/123',
      openVariantId: 'gid://shopify/ProductVariant/456',
      expectedValid: true
    },
    {
      name: 'Missing product URL',
      productUrl: '',
      earlyVariantId: 'gid://shopify/ProductVariant/123',
      openVariantId: 'gid://shopify/ProductVariant/456',
      expectedValid: false
    },
    {
      name: 'Missing early variant ID',
      productUrl: 'https://shop.example.com/products/test',
      earlyVariantId: '',
      openVariantId: 'gid://shopify/ProductVariant/456',
      expectedValid: false
    },
    {
      name: 'Missing open variant ID',
      productUrl: 'https://shop.example.com/products/test',
      earlyVariantId: 'gid://shopify/ProductVariant/123',
      openVariantId: '',
      expectedValid: false
    },
    {
      name: 'All fields missing',
      productUrl: '',
      earlyVariantId: '',
      openVariantId: '',
      expectedValid: false
    }
  ];
  
  testCases.forEach(testCase => {
    console.log(`  Testing: ${testCase.name}`);
    
    const isValid = validateGoLiveRequirements_(testCase.productUrl, testCase.earlyVariantId, testCase.openVariantId);
    
    if (isValid === testCase.expectedValid) {
      console.log(`    ✅ ${testCase.name} passed`);
    } else {
      console.log(`    ❌ ${testCase.name} failed. Expected: ${testCase.expectedValid}. Got: ${isValid}`);
    }
  });
}

/**
 * Helper function to parse go-live response (extracted from sendGoLiveRequest_)
 */
function parseGoLiveResponse_(responseCode, responseText) {
  // Parse response body to extract message
  let responseMessage = 'No message provided';
  try {
    if (responseText && responseText.trim()) {
      const responseData = JSON.parse(responseText);
      responseMessage = responseData.message || responseMessage;
    }
  } catch (parseError) {
    responseMessage = responseText || responseMessage;
  }
  
  if (responseCode >= 200 && responseCode < 300) {
    return {
      success: true,
      message: responseMessage,
      shouldUncheckCheckbox: false
    };
  } else if (responseCode >= 400) {
    return {
      success: false,
      message: responseMessage,
      shouldUncheckCheckbox: true
    };
  } else {
    return {
      success: false,
      message: `Unexpected response code ${responseCode}: ${responseMessage}`,
      shouldUncheckCheckbox: true
    };
  }
}

/**
 * Helper function to construct go-live payload
 */
function constructGoLivePayload_(productUrl, goLiveTime) {
  return {
    productUrl: productUrl,
    goLiveTime: goLiveTime.toISOString()
  };
}

/**
 * Helper function to validate go-live requirements
 */
function validateGoLiveRequirements_(productUrl, earlyVariantId, openVariantId) {
  return !!(productUrl && earlyVariantId && openVariantId);
}

/**
 * Run all go-live request tests
 */
function runGoLiveRequestTests() {
  console.log('🧪 Running go-live request tests...\n');
  
  testGoLiveRequest_Success();
  testGoLiveRequest_Failure();
  testGoLiveRequest_EdgeCases();
  testGoLiveRequest_Payload();
  testCheckboxValidation();
  
  console.log('\n✅ All go-live request tests completed');
}
