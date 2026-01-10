/**
 * Unified Entry Point for Google Apps Script
 * All trigger functions exported here
 */

// Import all GAS entry points
import './src/doPost.js';
import './src/menu.js';

// Note: All trigger functions (doGet, doPost, onOpen, showInstructions) are declared in their respective files
// and will be available in global scope after esbuild removes the import/export statements
