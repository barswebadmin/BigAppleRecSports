/**
 * Comprehensive tests for product creation parsing logic
 * Based on exact user specifications with ALL expected fields
 */

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

describe('Product Creation Parsing Tests - ALL FIELDS', () => {
  
  describe('Pickleball Sunday WTNB+ Social Buddy Sign-up - COMPLETE TEST', () => {
    const testData = {
      A: "Pickleball",
      B: "SUNDAY\n\nWTNB+\nSocial\nBuddy-Sign Up",
      C: "Total # of Weeks: 8\nRegular Season: 7 weeks\nNewbie Night: n/a\nTournament Date: Dec 7\nClosing Party: Date TBD\n\nSkipping 11/9 and 11/30\n\n# of Teams: 9\n# of Players: 72",
      D: "October 12",
      E: "Dec 7", 
      F: "$145",
      G: "12-3PM",
      H: "John Jay College",
      I: "pickleball.wtnb@bigapplerecsports.com",
      J: "6/8 attendance from Summer 2025",
      K: "",
      L: "SAME AS SPRING/SUMMER 2025 REGISTRATION",
      M: "Sept 18th 7PM", // Early registration
      N: "Sept 17th 7PM", // Vet registration  
      O: "Sept 19th 7PM"  // Open registration
    };

    it('should parse ALL product creation fields correctly', () => {
      const parsed = parseSourceRowEnhanced_(testData, []);
      const productData = convertToProductCreationFormat_(parsed, 14);
      
      // ALL EXPECTED VALUES from user specification:
      assert.equal(productData.sport, 'Pickleball');
      assert.equal(productData.day, 'Sunday');
      assert.equal(productData.sportSubCategory, 'N/A');
      assert.equal(productData.division, 'WTNB+');
      assert.equal(productData.season, 'Fall');
      assert.equal(productData.year, 2025);
      assert.equal(productData.socialOrAdvanced, 'Social');
      assert.equal(productData.types, 'Buddy Sign-up');
      assert.equal(productData.newPlayerOrientationDateTime, '');
      assert.equal(productData.scoutNightDateTime, '');
      assert.equal(productData.openingPartyDate, '');
      assert.equal(productData.seasonStartDate, '10/12/25');
      assert.equal(productData.seasonEndDate, '12/7/25');
      assert.equal(productData.offDatesCommaSeparated, '');
      assert.equal(productData.rainDate, '');
      assert.equal(productData.closingPartyDate, '');
      assert.equal(productData.sportStartTime, '12:00 PM');
      assert.equal(productData.sportEndTime, '3:00 PM');
      assert.equal(productData.alternativeStartTime, '');
      assert.equal(productData.alternativeEndTime, '');
      assert.equal(productData.location, 'John Jay College (59th and 10th)');
      assert.equal(productData.price, '$145');
      assert.equal(productData.vetRegistrationStartDateTime, 'Wednesday, 9/17/25 at 7 PM');
      assert.equal(productData.earlyRegistrationStartDateTime, 'Thursday, 9/18/25 at 7 PM');
      assert.equal(productData.openRegistrationStartDateTime, 'Friday, 9/19/25 at 7 PM');
      assert.equal(productData.totalInventory, 72);
    });

    it('should display confirmation correctly', () => {
      const parsed = parseSourceRowEnhanced_(testData, []);
      const productData = convertToProductCreationFormat_(parsed, 14);
      const display = buildConfirmationDisplay_(productData);
      
      // Expected display from user specification
      const expectedDisplay = `🛍️ Create Shopify Product - All Parsed Fields

=== BASIC INFO ===
Sport: Pickleball
Day: Sunday
Division: WTNB+
Season: Fall
Year: 2025
Social or Advanced: Social
Type(s): Buddy Sign-up

=== DATES & TIMES ===
Season Start Date: 10/12/2025
Season End Date: 12/7/2025
Sport Start Time: 12:00 PM
Sport End Time: 3:00 PM
Off Dates: 11/9, 11/30

=== SPECIAL EVENTS ===
New Player Orientation Date: None
Opening Party Date: None
Closing Party Date: TBD

=== LOCATION & PRICING ===
Location: John Jay College (59th and 10th)
Price: $145
Total Inventory: 72

=== REGISTRATION WINDOWS ===
Veteran Registration Start: 9/17/2025 7:00 PM
Early Registration Start: 9/18/2025 7:00 PM
Open Registration Start: 9/19/2025 7:00 PM

Create this product in Shopify with the above parsed data?`;

      assert.equal(display.trim(), expectedDisplay.trim());
    });
  });

  describe('Kickball Saturday Open Social Randomized - COMPLETE TEST', () => {
    const testData = {
      A: "Kickball",
      B: "SATURDAY\n\nOpen\nSocial\nRandomized",
      C: "Total # of Weeks: 8\nOpening Party: 9/13/25\nRegular Season: 8 weeks\nRain Date: 11/22/25\nClosing Party: 11/15/25*\n\n# of Teams: 12\n# of Players: 192 (16 players per team)\n\nGame Duration: 45 min",
      D: "9/20/2025",
      E: "11/15/2025",
      F: "$115", 
      G: "1-3pm",
      H: "Dewitt Clinton Park",
      I: "",
      J: "Saturday Open Summer 2025",
      K: "",
      L: "",
      M: "8/31/25 @ 7pm", // Early registration
      N: "8/30/25 @ 7pm", // Vet registration
      O: "9/1/25 @ 7pm"   // Open registration
    };

    it('should parse ALL product creation fields correctly', () => {
      const parsed = parseSourceRowEnhanced_(testData, []);
      const productData = convertToProductCreationFormat_(parsed, 8);
      
      // ALL EXPECTED VALUES from user specification:
      assert.equal(productData.sport, 'Kickball');
      assert.equal(productData.day, 'Saturday');
      assert.equal(productData.sportSubCategory, 'N/A');
      assert.equal(productData.division, 'Open');
      assert.equal(productData.season, 'Fall');
      assert.equal(productData.year, 2025);
      assert.equal(productData.socialOrAdvanced, 'Social');
      assert.equal(productData.types, 'Randomized Teams');
      assert.equal(productData.newPlayerOrientationDateTime, '');
      assert.equal(productData.scoutNightDateTime, '');
      assert.equal(productData.openingPartyDate, '9/13/25');
      assert.equal(productData.seasonStartDate, '9/20/25');
      assert.equal(productData.seasonEndDate, '11/15/25');
      assert.equal(productData.offDatesCommaSeparated, '');
      assert.equal(productData.rainDate, '11/22/25');
      assert.equal(productData.closingPartyDate, '11/15/25');
      assert.equal(productData.sportStartTime, '1:00 PM');
      assert.equal(productData.sportEndTime, '3:00 PM');
      assert.equal(productData.alternativeStartTime, '');
      assert.equal(productData.alternativeEndTime, '');
      assert.equal(productData.location, 'Dewitt Clinton Park (52nd St & 11th Ave)');
      assert.equal(productData.price, '$115');
      assert.equal(productData.vetRegistrationStartDateTime, 'Saturday, 8/30/25 at 7 PM');
      assert.equal(productData.earlyRegistrationStartDateTime, 'Sunday, 8/31/25 at 7 PM');
      assert.equal(productData.openRegistrationStartDateTime, 'Monday, 9/1/25 at 7 PM');
      assert.equal(productData.totalInventory, 192);
    });

    it('should display confirmation correctly', () => {
      const parsed = parseSourceRowEnhanced_(testData, []);
      const productData = convertToProductCreationFormat_(parsed, 8);
      const display = buildConfirmationDisplay_(productData);
      
      // Expected display from user specification
      const expectedDisplay = `🛍️ Create Shopify Product - All Parsed Fields

=== BASIC INFO ===
Sport: Kickball
Day: Saturday
Division: Open
Season: Fall
Year: 2025
Social or Advanced: Social
Type(s): Randomized Teams

=== DATES & TIMES ===
Season Start Date: 9/20/2025
Season End Date: 11/15/2025
Sport Start Time: 1:00 PM
Sport End Time: 3:00 PM
Off Dates: (empty)

=== SPECIAL EVENTS ===
New Player Orientation: None
Scout Night: None
Opening Party Date: 9/13/2025
Rain Date: 11/22/2025
Closing Party Date: 11/15/2025

=== LOCATION & PRICING ===
Location: Dewitt Clinton Park (52nd St & 11th Ave)
Price: $115
Total Inventory: 192

=== REGISTRATION WINDOWS ===
Veteran Registration Start: 8/30/2025 7:00 PM
Early Registration Start: 8/31/2025 7:00 PM
Open Registration Start: 9/1/2025 7:00 PM

Create this product in Shopify with the above parsed data?`;

      assert.equal(display.trim(), expectedDisplay.trim());
    });
  });

  describe('Bowling Sunday Open Multiple Types - COMPLETE TEST', () => {
    const testData = {
      A: "Bowling",
      B: "SUNDAY\n\nOpen\n\nBuddy-Sign Up\nRandomized",
      C: "2 sessions; 350-364 players, 50-52 teams, 7 players max\nTeams are randomly assigned\nPlayers are able to sign-up with one buddy\nTimes: 12:45-2:45PM & 3:00-5:00PM\n\nNOTE: SKIPPING 11/9 to accommodate for all sports charity awards event.",
      D: "9/21/25",
      E: "11/16/25",
      F: "$145",
      G: "Times: 12:45-2:45PM & 3:00-5:00PM",
      H: "Frames Bowling Lounge",
      I: "sunday-bowling@bigapplerecsports.com",
      J: "Spring 2025 – qualify if players attendnace is max 2 missed sessions",
      K: "9/21, 9/28, 10/5, 10/12, 10/19, 10/26, 11/2, 11/9, 11/16",
      L: "SAME AS SPRING/SUMMER 2025 REGISTRATION",
      M: "Weds, Sept. 3rd, 6pm", // Early registration  
      N: "Tues, Sept. 2nd, 6pm", // Vet registration
      O: "Thurs, Sept. 4th, 6pm" // Open registration
    };

    it('should parse ALL product creation fields correctly', () => {
      const parsed = parseSourceRowEnhanced_(testData, []);
      const productData = convertToProductCreationFormat_(parsed, 5);
      
      // ALL EXPECTED VALUES from user specification:
      assert.equal(productData.sport, 'Bowling');
      assert.equal(productData.day, 'Sunday');
      assert.equal(productData.sportSubCategory, 'N/A');
      assert.equal(productData.division, 'Open');
      assert.equal(productData.season, 'Fall');
      assert.equal(productData.year, 2025);
      assert.equal(productData.socialOrAdvanced, ''); // Not shown for bowling
      assert.equal(productData.types, 'Randomized Teams, Buddy Sign-up');
      assert.equal(productData.newPlayerOrientationDateTime, ''); // Not shown for bowling
      assert.equal(productData.scoutNightDateTime, '');
      assert.equal(productData.openingPartyDate, '');
      assert.equal(productData.seasonStartDate, '9/21/25');
      assert.equal(productData.seasonEndDate, '11/16/25');
      assert.equal(productData.offDatesCommaSeparated, '11/9');
      assert.equal(productData.rainDate, '');
      assert.equal(productData.closingPartyDate, '');
      assert.equal(productData.sportStartTime, '12:45 PM');
      assert.equal(productData.sportEndTime, '2:45 PM');
      assert.equal(productData.alternativeStartTime, '3:00 PM');
      assert.equal(productData.alternativeEndTime, '5:00 PM');
      assert.equal(productData.location, 'Frames Bowling Lounge (40th St and 9th Ave)');
      assert.equal(productData.price, '$145');
      assert.equal(productData.vetRegistrationStartDateTime, 'Tuesday, 9/2/25 at 6 PM');
      assert.equal(productData.earlyRegistrationStartDateTime, 'Wednesday, 9/3/25 at 6 PM');
      assert.equal(productData.openRegistrationStartDateTime, 'Thursday, 9/4/25 at 6 PM');
      assert.equal(productData.totalInventory, 364);
    });

    it('should display confirmation correctly - BOWLING SPECIFIC RULES', () => {
      const parsed = parseSourceRowEnhanced_(testData, []);
      const productData = convertToProductCreationFormat_(parsed, 5);
      const display = buildConfirmationDisplay_(productData);
      
      // Expected display from user specification (bowling specific)
      const expectedDisplay = `Confirm Product Creation
🛍️ Create Shopify Product - All Parsed Fields

=== BASIC INFO ===
Sport: Bowling
Day: Sunday
Division: Open
Season: Fall
Year: 2025
Type(s): Randomized Teams, Buddy Sign-up

=== DATES & TIMES ===
Season Start Date: 9/21/2025
Season End Date: 11/16/2025
Sport Start Time: 12:45 PM
Sport End Time: 2:45 PM
Alternative Start Time: 3:00 PM
Alternative End Time: 5:00 PM
Off Dates: 11/9

=== SPECIAL EVENTS ===
Opening Party Date: None
Closing Party Date: None

=== LOCATION & PRICING ===
Location: Frames Bowling Lounge (40th St and 9th Ave)
Price: $145
Total Inventory: 364

=== REGISTRATION WINDOWS ===
Veteran Registration Start: 9/2/25 6:00 PM
Early Registration Start: 9/3/25 6:00 PM
Open Registration Start: 9/4/25 6:00 PM

Create this product in Shopify with the above parsed data?`;

      // Verify bowling doesn't show social/advanced or new player orientation
      assert(!display.includes('Social or Advanced:'));
      assert(!display.includes('New Player Orientation:'));
      
      // Verify alternative times are shown
      assert(display.includes('Alternative Start Time: 3:00 PM'));
      assert(display.includes('Alternative End Time: 5:00 PM'));
      
      assert.equal(display.trim(), expectedDisplay.trim());
    });
  });

  describe('Dodgeball Monday Big Ball - MISSING REQUIRED FIELD TEST', () => {
    const testData = {
      A: "Dodgeball",
      B: "MONDAY\n\nOpen\nSocial Big Ball\nRandomized - Buddy Sign Ups",
      C: "Newbie Night/Open Play - 10/6/25\n\nNo games on Indigineous Peoples Day 10/13",
      D: "10-20-2025",
      E: "12/8/2025",
      F: "$120",
      G: "6:30-10",
      H: "Hartley House\n413 W 46th Street",
      I: "chance.hamlin@bigapplerecsports.com\ntenni.tenerelli@bigapplerecsports.com",
      J: "Spring 2025 Vet Status",
      K: "",
      L: "",
      M: "Weds, Sept. 3rd, 6pm", // Early registration
      N: "Tues, Sept. 2nd, 7pm", // Vet registration
      O: "Thurs, Sept. 4th, 6pm" // Open registration
      // NOTE: Missing total inventory in the data!
    };

    it('should parse ALL fields correctly but detect missing totalInventory', () => {
      const parsed = parseSourceRowEnhanced_(testData, []);
      const productData = convertToProductCreationFormat_(parsed, 14);
      
      // ALL EXPECTED VALUES from user specification:
      assert.equal(productData.sport, 'Dodgeball');
      assert.equal(productData.day, 'Monday');
      assert.equal(productData.sportSubCategory, 'Big Ball');
      assert.equal(productData.division, 'Open');
      assert.equal(productData.season, 'Fall');
      assert.equal(productData.year, 2025);
      assert.equal(productData.socialOrAdvanced, 'Mixed Social/Advanced');
      assert.equal(productData.types, 'Randomized Teams, Buddy Sign-up');
      assert.equal(productData.newPlayerOrientationDateTime, '10/6/2025 6:30 PM');
      assert.equal(productData.scoutNightDateTime, '');
      assert.equal(productData.openingPartyDate, '');
      assert.equal(productData.seasonStartDate, '10/20/2025');
      assert.equal(productData.seasonEndDate, '12/8/2025');
      assert.equal(productData.offDatesCommaSeparated, '10/13');
      assert.equal(productData.rainDate, '');
      assert.equal(productData.closingPartyDate, '');
      assert.equal(productData.sportStartTime, '6:30 PM');
      assert.equal(productData.sportEndTime, '10:00 PM');
      assert.equal(productData.alternativeStartTime, '');
      assert.equal(productData.alternativeEndTime, '');
      assert.equal(productData.location, 'Hartley House (46th St & 9th Ave)');
      assert.equal(productData.price, '$120');
      assert.equal(productData.vetRegistrationStartDateTime, 'Tuesday, 9/2/25 at 7 PM');
      assert.equal(productData.earlyRegistrationStartDateTime, 'Wednesday, 9/3/25 at 6 PM');
      assert.equal(productData.openRegistrationStartDateTime, 'Thursday, 9/4/25 at 6 PM');
      assert.equal(productData.totalInventory, ''); // MISSING!
    });

    it('should show error display for missing required fields', () => {
      const parsed = parseSourceRowEnhanced_(testData, []);
      const productData = convertToProductCreationFormat_(parsed, 14);
      const validation = validateRequiredFields_(productData);
      
      assert.equal(validation.isValid, false);
      assert(validation.missingFields.includes('Total Inventory'));
      
      const display = buildErrorDisplay_(productData, validation.missingFields);
      
      // Expected error display from user specification
      const expectedDisplay = `Cannot Shopify Product - Not all Required Fields are Present. Parsed Info Found:

=== BASIC INFO ===
Sport: Dodgeball
Day: Monday
Sport Sub-Category: Big Ball
Division: Open
Season: Fall
Year: 2025
Social or Advanced: Social
Type(s): Randomized Teams, Buddy Sign-up

=== DATES & TIMES ===
Season Start Date: 10/20/2025
Season End Date: 12/8/2025
Sport Start Time: 6:30 PM
Sport End Time: 10:00 PM
Off Dates: 10/13

=== SPECIAL EVENTS ===
New Player Orientation: 10/6/2025 6:30 PM
Opening Party Date: None
Closing Party Date: None

=== LOCATION & PRICING ===
Location: Hartley House (46th St & 9th Ave)
Price: $120
Total Inventory: [Not Found]

=== REGISTRATION WINDOWS ===
Veteran Registration Start: 9/2/25 7:00 PM
Early Registration Start: 9/3/25 6:00 PM
Open Registration Start: 9/4/25 6:00 PM`;

      // Verify dodgeball shows sport sub-category
      assert(display.includes('Sport Sub-Category: Big Ball'));
      
      // Verify missing field is marked
      assert(display.includes('Total Inventory: [Not Found]'));
      
      // Verify error starts correctly
      assert(display.startsWith('Cannot'));
      
      assert.equal(display.trim(), expectedDisplay.trim());
    });
  });

  describe('Interactive Update Flow Tests', () => {
    it('should provide numbered list of fields for editing', () => {
      const testData = {
        sport: 'Dodgeball',
        day: 'Monday',
        division: 'Open',
        season: 'Fall',
        year: 2025,
        price: 120,
        totalInventory: '', // Missing
        location: 'Hartley House (46th St & 9th Ave)'
      };
      
      const editableFields = getEditableFieldsList_(testData);
      
      assert(editableFields.some(field => field.includes('1. Sport: Dodgeball')));
      assert(editableFields.some(field => field.includes('Price: $120')));
      assert(editableFields.some(field => field.includes('Total Inventory: [Not Found]')));
    });

    it('should update field value when user provides input', () => {
      const testData = {
        sport: 'Dodgeball',
        totalInventory: '',
        price: 120
      };
      
      const updated = updateFieldValue_(testData, 14, '150'); // Update total inventory (field 14)
      
      assert.equal(updated.totalInventory, 150);
      assert.equal(updated.price, 120); // Unchanged
      assert.equal(updated.sport, 'Dodgeball'); // Unchanged
    });
  });
});

// Helper function stubs that need to be implemented
function parseSourceRowEnhanced_(data, unresolved) {
  throw new Error('parseSourceRowEnhanced_ not implemented - need to load actual parsing functions');
}

function convertToProductCreationFormat_(parsed, rowNumber) {
  throw new Error('convertToProductCreationFormat_ not implemented');
}

function buildConfirmationDisplay_(productData) {
  throw new Error('buildConfirmationDisplay_ not implemented');
}

function validateRequiredFields_(productData) {
  throw new Error('validateRequiredFields_ not implemented');
}

function buildErrorDisplay_(productData, missingFields) {
  throw new Error('buildErrorDisplay_ not implemented');
}

function getEditableFieldsList_(productData) {
  throw new Error('getEditableFieldsList_ not implemented');
}

function updateFieldValue_(productData, fieldNumber, newValue) {
  throw new Error('updateFieldValue_ not implemented');
}

if (require.main === module) {
  console.log('Running comprehensive product creation tests...');
  console.log('Note: This will fail until the actual parsing functions are loaded.');
}

module.exports = {
  parseSourceRowEnhanced_,
  convertToProductCreationFormat_,
  buildConfirmationDisplay_,
  validateRequiredFields_,
  buildErrorDisplay_,
  getEditableFieldsList_,
  updateFieldValue_
};