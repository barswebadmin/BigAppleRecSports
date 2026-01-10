/**
 * Unified Entry Point for Google Apps Script
 * All trigger functions exported here
 */

// Import all GAS entry points
import './src/Add Menu Item to UI';
import './src/Add Vet Tags to Customers';
import './src/sendVeteranEmail';

// Note: All trigger functions (onOpen, addVeteranTagToCustomerEmails, etc.)
// are declared in their respective files and will be available in global scope
// after esbuild removes the import/export statements
