/**
 * Consolidated test runner for all Google Apps Script functions
 * Uses the new consolidated test files for better organization
 */

const fs = require('fs');
const path = require('path');
const { strict: assert } = require('assert');

// Mock Google Apps Script environment
global.Logger = { log: console.log };
global.SpreadsheetApp = {
  getUi: () => ({
    alert: (title, message, buttons) => ({ getSelectedButton: () => 'OK' }),
    prompt: (title, message, buttons) => ({
      getSelectedButton: () => 'OK',
      getResponseText: () => 'create'
    }),
    Button: { OK: 'OK', CANCEL: 'CANCEL', YES: 'YES', NO: 'NO' },
    ButtonSet: { OK: 'OK', OK_CANCEL: 'OK_CANCEL', YES_NO: 'YES_NO' }
  })
};

// Load required GAS modules by evaluating them in global scope
function loadGasFile(filePath) {
  const fullPath = path.resolve(__dirname, '../src', filePath);
  if (fs.existsSync(fullPath)) {
    const content = fs.readFileSync(fullPath, 'utf8');
    // biome-ignore lint/security/noGlobalEval: <not a risk and necessary>
    eval(content);
    console.log(`✅ Loaded: ${filePath}`);
  } else {
    console.log(`❌ Not found: ${filePath}`);
  }
}

// Load all required source files
console.log('📚 Loading source files...\n');

// Core files
loadGasFile('config/constants.js');
loadGasFile('helpers/formatValidators.js');
loadGasFile('helpers/normalizers.js');
loadGasFile('helpers/textUtils.js');
loadGasFile('parsers/_rowParser.js');
loadGasFile('parsers/parseColBLeagueBasicInfo_.js');
loadGasFile('parsers/parseColCLeagueDetails_.js');
loadGasFile('parsers/parseColDESeasonDates.js');
loadGasFile('parsers/parseColFPrice_.js');
loadGasFile('parsers/parseColGLeagueTimes_.js');
loadGasFile('parsers/parseColMNORegistrationDates_.js');
loadGasFile('parsers/parseColHLocation_.js');
// dateUtils moved to top-level GoogleAppsScripts/shared-utilities in repo root
// For the consolidated runner, we can skip this or load the shared utils if needed
const sharedUtilsPath = path.resolve(__dirname, '../../shared-utilities/dateUtils.js');
if (fs.existsSync(sharedUtilsPath)) {
  const content = fs.readFileSync(sharedUtilsPath, 'utf8');
  // biome-ignore lint/security/noGlobalEval: safe in test harness
  eval(content);
  console.log('✅ Loaded: shared-utilities/dateUtils.gs (top-level)');
} else {
  console.log('ℹ️  Skipping shared-utilities/dateUtils.gs (not found)');
}
loadGasFile('validators/fieldValidation.js');

// New modular files
loadGasFile('data/productDataProcessing.js');
loadGasFile('ui/productCreationDialogs.js');
loadGasFile('sheet/cellMapping.js');
loadGasFile('utils/formatting.js');
loadGasFile('api/backendCommunication.js');
loadGasFile('core/portedFromProductCreateSheet/shopifyProductCreation.js');

// Load consolidated test files to define test entrypoints
function loadTestFile(filePath) {
  const fullPath = path.resolve(__dirname, filePath);
  if (fs.existsSync(fullPath)) {
    let content = fs.readFileSync(fullPath, 'utf8');
    // Ensure test-defined functions are attached to global for invocation below
    content = content.replace(/function\s+(\w+)\s*\(/g, 'global.$1 = function(');
    // biome-ignore lint/security/noGlobalEval: test harness
    eval(content);
    console.log(`✅ Loaded test: ${filePath}`);
  } else {
    console.log(`❌ Test not found: ${filePath}`);
  }
}

loadTestFile('test_parsers.js');
loadTestFile('test_ui_and_workflow.js');
loadTestFile('test_utilities.js');
loadTestFile('test_backend_response_handling.js');
loadTestFile('test_go_live_request.js');

console.log('\n🧪 Running consolidated tests...\n');

// Run consolidated test suites
try {
  console.log('='.repeat(60));
  console.log('TEST SUITE 1: PARSERS');
  console.log('='.repeat(60));
  runParserTests();
  
  console.log('\n' + '='.repeat(60));
  console.log('TEST SUITE 2: UI AND WORKFLOW');
  console.log('='.repeat(60));
  runUIAndWorkflowTests();
  
  console.log('\n' + '='.repeat(60));
  console.log('TEST SUITE 3: UTILITIES');
  console.log('='.repeat(60));
  runUtilityTests();
  
  console.log('\n' + '='.repeat(60));
  console.log('TEST SUITE 4: BACKEND RESPONSE HANDLING');
  console.log('='.repeat(60));
  runBackendResponseTests();
  
  console.log('\n' + '='.repeat(60));
  console.log('TEST SUITE 5: GO-LIVE REQUEST');
  console.log('='.repeat(60));
  runGoLiveRequestTests();
  
  console.log('\n' + '='.repeat(60));
  console.log('🎉 ALL CONSOLIDATED TESTS COMPLETED SUCCESSFULLY!');
  console.log('='.repeat(60));
  
} catch (error) {
  console.log(`❌ Test suite failed: ${error.message}`);
  console.log(error.stack);
  process.exit(1);
}
