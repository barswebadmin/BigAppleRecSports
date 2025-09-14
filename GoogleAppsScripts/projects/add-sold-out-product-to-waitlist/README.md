# Add Sold Out Product to Waitlist - Refactored Structure

> 📚 **Documentation**: See [README.md](../../../README.md#google-apps-scripts) for GAS overview and [README_EXT/2_DEPLOYMENT.md#google-apps-scripts-deployment](../../../README_EXT/2_DEPLOYMENT.md#google-apps-scripts-deployment) for deployment

## Overview
This Google Apps Script project manages waitlist form options when products sell out. The code has been refactored for better organization and readability.

## File Structure

### Core Files
- **`doPost.js`** - HTTP endpoint that receives webhook requests
- **`handleIncomingPostRequest.js`** - Main orchestrator that coordinates the entire process
- **`addProductOptionToWaitlistForm.js`** - Form insertion logic and utility functions

### Helper Modules
- **`validation.js`** - Input validation and duplicate checking
- **`formHelpers.js`** - Google Forms API interactions and form management
- **`labelFormatting.js`** - Label creation and formatting
- **`sortingLogic.js`** - Complex sorting algorithm for waitlist options

### Testing
- **`test_parsing.js`** - Test functions for all modules

## Data Flow

1. **HTTP Request** → `doPost()` receives webhook
2. **Validation** → `handleIncomingPostRequest()` validates input
3. **Label Creation** → `createFormattedLabel()` formats the option text
4. **Form Access** → `getFormAndItem()` gets the Google Form
5. **Duplicate Check** → `checkForDuplicateOption()` prevents duplicates
6. **Sorting** → `sortWaitlistLabels()` applies complex sorting logic
7. **Form Update** → `addProductOptionToWaitlistForm()` inserts new choices

## Key Functions

### `handleIncomingPostRequest(params)`
Main orchestrator that:
- Validates required fields (`productUrl` + at least one other field)
- Creates formatted label
- Checks for duplicates
- Manages sorting and form updates

### `validateIncomingData(params)`
Ensures:
- `productUrl` is present and non-empty
- At least one of `sport`, `day`, `division`, or `otherIdentifier` is provided

### `sortWaitlistLabels(labels)`
Complex sorting algorithm:
1. Sports first (alphabetical)
2. Then by day (chronological)
3. Then by division (reverse alphabetical: Open → WTNB+ → WTNB)
4. Then by other identifier (alphabetical)
5. Non-sports items last with year/month logic

### `addProductOptionToWaitlistForm(formItem, sortedLabels)`
Handles the actual form insertion for both Multiple Choice and List form types.

## Testing

Run tests in Google Apps Script console:
```javascript
runAllTests();                    // Run all tests
testCreateFormattedLabel();       // Test label formatting
testValidateIncomingData();       // Test validation logic
testSortWaitlistLabels();         // Test sorting algorithm
testReturnToDefaultLive();        // Test form reset (live)
```

## Constants

- **`QUESTION_TITLE`**: The form question to update
- **`NO_WAITLISTS_SENTINEL`**: Default option when no waitlists exist

## Error Handling

- Validates input data and throws descriptive errors
- Handles Google Forms API errors
- Returns appropriate HTTP responses via `doPost`
- Backend checks for "already exists" errors for duplicate detection
