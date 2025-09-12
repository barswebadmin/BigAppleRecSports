# Shared Utilities

This directory contains common functions and utilities that can be shared across multiple Google Apps Scripts.

## Why was this empty?

Google Apps Script doesn't have a built-in module system like Node.js, so sharing code between scripts requires manual copying or using Google Apps Script libraries. I created this directory as a place to:

1. **Store common functions** that you use across multiple scripts
2. **Maintain consistency** in how you handle common operations
3. **Provide templates** for frequently used patterns

## How to use shared utilities:

### Option 1: Copy & Paste (Recommended for small functions)
1. Copy the function from a file in this directory
2. Paste it into your Google Apps Script
3. Modify as needed

### Option 2: Google Apps Script Libraries (For complex shared code)
1. Create a separate Google Apps Script project for the library
2. Deploy it as a library
3. Include it in other scripts

## Common Utilities Included:

- `apiUtils.gs` - Common API request functions
- `dateUtils.gs` - Date formatting and manipulation  
- `secretsUtils.gs` - Secret management helper functions

## Usage Examples:

```javascript
// Example from apiUtils.gs
function makeApiRequest(url, options) {
  // Copy this function into your script and use it
}

// Example from dateUtils.gs  
function formatDateForShopify(date) {
  // Copy this function into your script and use it
}

// Example from secretsUtils.gs
function getSecret(key) {
  // Copy this function into your script and use it
}
```
