/**
 * Unified Entry Point for Google Apps Script
 * All trigger functions and menu callbacks exported here
 */

// Import all GAS entry points
import './core/doGet';
import './core/doPost';
import './core/onOpen';
import './core/processFormSubmit';
import './workflows/pullOffWaitlist';

// Note: All trigger functions (doGet, doPost, onOpen, processFormSubmit, pullOffWaitlist)
// are declared in their respective files and will be available in global scope
// after esbuild removes the import/export statements

