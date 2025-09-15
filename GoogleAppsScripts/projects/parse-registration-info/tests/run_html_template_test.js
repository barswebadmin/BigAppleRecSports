#!/usr/bin/env node

/**
 * Node.js test runner for HTML template variables validation
 * Tests that template variables are properly resolved without undefined/null values
 */

const fs = require('fs');
const path = require('path');
const { performance } = require('perf_hooks');

// Mock Google Apps Script environment
global.console = console;
global.Logger = {
  log: (message) => console.log(`[Logger] ${message}`)
};

// Load required files
const projectRoot = path.join(__dirname, '..');

function loadGasFile(relativePath) {
  const fullPath = path.join(projectRoot, relativePath);
  if (!fs.existsSync(fullPath)) {
    throw new Error(`File not found: ${fullPath}`);
  }
  const content = fs.readFileSync(fullPath, 'utf8');
  return content;
}

try {
  console.log('📦 Loading test dependencies...');

  // Load dependencies in order
  const files = [
    'src/core/portedFromProductCreateSheet/createShopifyProduct.gs',
    'tests/testHtmlTemplateVariables.gs'
  ];

  for (const file of files) {
    try {
      const content = loadGasFile(file);
      console.log(`✅ Loaded: ${file}`);

      // Remove Google Apps Script specific syntax and evaluate
      const processedContent = content
        .replace(/\/\/\/ <reference.*?\/>/g, '') // Remove reference comments
        .replace(/@requires.*$/gm, '')          // Remove @requires comments
        .replace(/function\s+(\w+)\s*\(/g, 'global.$1 = function(') // Make functions global
        .replace(/^(\s*)const\s+(\w+)\s*=/gm, '$1global.$2 =')     // Make constants global
        .replace(/^(\s*)let\s+(\w+)\s*=/gm, '$1global.$2 =')       // Make let variables global
        .replace(/^(\s*)var\s+(\w+)\s*=/gm, '$1global.$2 =');      // Make var variables global

      eval(processedContent);

    } catch (error) {
      console.error(`❌ Error loading ${file}:`, error.message);
      throw error;
    }
  }

  console.log('\n🧪 Running HTML Template Variables Tests...');
  const startTime = performance.now();

  // Run the test
  global.testHtmlTemplateVariables();

  const endTime = performance.now();
  const duration = (endTime - startTime).toFixed(2);

  console.log(`\n✅ All HTML template tests completed successfully in ${duration}ms`);
  process.exit(0);

} catch (error) {
  console.error('\n❌ HTML Template Test Failed:', error.message);
  console.error('Stack trace:', error.stack);
  process.exit(1);
}
