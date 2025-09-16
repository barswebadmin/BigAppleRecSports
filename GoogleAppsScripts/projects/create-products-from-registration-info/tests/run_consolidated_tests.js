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
loadGasFile('config/constants.gs');
loadGasFile('helpers/formatValidators.gs');
loadGasFile('helpers/normalizers.gs');
loadGasFile('helpers/textUtils.gs');
loadGasFile('parsers/_rowParser.gs');
loadGasFile('parsers/parseColBLeagueBasicInfo_.gs');
loadGasFile('parsers/parseColCLeagueDetails_.gs');
loadGasFile('parsers/parseColDESeasonDates.gs');
loadGasFile('parsers/parseColFPrice_.gs');
loadGasFile('parsers/parseColGLeagueTimes_.gs');
loadGasFile('parsers/parseColMNORegistrationDates_.gs');
loadGasFile('parsers/parseColHLocation_.gs');
loadGasFile('shared-utilities/dateUtils.gs');
loadGasFile('validators/fieldValidation.gs');

// New modular files
loadGasFile('data/productDataProcessing.gs');
loadGasFile('ui/productCreationDialogs.gs');
loadGasFile('sheet/cellMapping.gs');
loadGasFile('utils/formatting.gs');
loadGasFile('api/backendCommunication.gs');
loadGasFile('core/portedFromProductCreateSheet/shopifyProductCreation.gs');

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
