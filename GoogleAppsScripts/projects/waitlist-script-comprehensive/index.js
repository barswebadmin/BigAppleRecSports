/**
 * Unified Entry Point for Google Apps Script
 * All trigger functions and menu callbacks exported here
 */

// Import all GAS entry points
import './src/core/doGet';
import './src/core/doPost';
import './src/core/onOpen';
import './src/core/processFormSubmit';
import './src/workflows/pullOffWaitlist';

// Note: All trigger functions (doGet, doPost, onOpen, processFormSubmit, pullOffWaitlist)
// are declared in their respective files and will be available in global scope
// after esbuild removes the import/export statements

