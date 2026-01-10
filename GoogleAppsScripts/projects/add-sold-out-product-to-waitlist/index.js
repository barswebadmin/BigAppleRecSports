/**
 * Unified Entry Point for Google Apps Script
 * All trigger functions exported here
 */

// Import all GAS entry points
import './src/core/doPost';

// Note: All trigger functions (doPost) are declared in their respective files
// and will be available in global scope after esbuild removes the import/export statements
