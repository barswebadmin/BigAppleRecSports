/**
 * Configuration constants for parse-registration-info
 * Target spreadsheet settings and data mappings
 */


/***** COMPREHENSIVE PRODUCT CREATE FIELDS *****/
// All possible fields that can be tracked during product creation parsing
// Based on expected_product_json_payload.js structure
const comprehensiveProductCreateFields = [
  // Top-level required fields
  "sportName",
  "division",
  "season",
  "year",
  "dayOfPlay",
  "location",

  // Optional league info nested fields
  "sportSubCategory",
  "socialOrAdvanced",
  "types",

  // Important dates nested fields
  "newPlayerOrientationDateTime",
  "scoutNightDateTime",
  "openingPartyDate",
  "seasonStartDate",
  "seasonEndDate",
  "offDates",
  "rainDate",
  "closingPartyDate",
  "vetRegistrationStartDateTime",
  "earlyRegistrationStartDateTime",
  "openRegistrationStartDateTime",

  // Time fields
  "leagueStartTime",
  "leagueEndTime",
  "alternativeStartTime",
  "alternativeEndTime",

  // Inventory info nested fields
  "price",
  "totalInventory",
  "numberVetSpotsToReleaseAtGoLive"
];

/***** SPORT-SPECIFIC IRRELEVANT FIELDS *****/
// Fields that will never be present for specific sports
// These should be excluded from validation checks for the productCreateData
const irrelevantFieldsForSport = {
  "Kickball": [
    "sportSubCategory",
    "alternativeStartTime",
    "alternativeEndTime",
    "openingPartyDate"
  ],
  "Dodgeball": [
    "scoutNightDateTime",
    "rainDate",
    "alternativeStartTime",
    "alternativeEndTime",
    "openingPartyDate"
  ],
  "Bowling": [
    "sportSubCategory",
    "socialOrAdvanced",
    "newPlayerOrientationDateTime",
    "scoutNightDateTime",
    "openingPartyDate",
    "rainDate"
  ],
  "Pickleball": [
    "sportSubCategory",
    "newPlayerOrientationDateTime",
    "scoutNightDateTime",
    "rainDate",
    "alternativeStartTime",
    "alternativeEndTime",
    "openingPartyDate"
  ]
};

/***** PRODUCT FIELD ENUMS *****/
// Comprehensive enum values for all product fields
// Sport-specific enums use nested objects with sport names as keys
const productFieldEnums = {
  "sportName": ["Dodgeball", "Kickball", "Bowling", "Pickleball"],
  "division": ["WTNB+", "Open"],
  "season": ["Fall", "Winter", "Summer", "Spring"],
  "dayOfPlay": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
  "location": {
    "Dodgeball": [
      "Elliott Center (26th St & 9th Ave)",
      "PS3 Charrette School (Grove St & Hudson St)",
      "Village Community School (10th St & Greenwich St)",
      "Hartley House (46th St & 9th Ave)",
      "Dewitt Clinton Park (52nd St & 11th Ave)"
    ],
    "Kickball": [
      "Gansevoort Peninsula Athletic Park, Pier 53 (Gansevoort St & 11th)",
      "Chelsea Park (27th St & 9th Ave)",
      "Dewitt Clinton Park (52nd St & 11th Ave)"
    ],
    "Pickleball": [
      "Gotham Pickleball (46th and Vernon in LIC)",
      "John Jay College (59th and 10th)",
      "Pickle1 (7 Hanover Square in LIC)"
    ],
    "Bowling": [
      "Frames Bowling Lounge (40th St and 9th Ave)",
      "Bowlero Chelsea Piers (60 Chelsea Piers)"
    ]
  },
  "sportSubCategory": ["Big Ball", "Small Ball", "Foam"],
  "socialOrAdvanced": ["Social", "Advanced", "Mixed Social/Advanced", "Competitive/Advanced", "Intermediate/Advanced"],
  "types": ["Draft", "Randomized Teams", "Buddy Sign-up", "Sign up with a newbie (randomized otherwise)"]
};
