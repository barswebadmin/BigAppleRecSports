/**
 * Configuration constants for parse-registration-info
 * Target spreadsheet settings and data mappings
 */

/***** TARGET SPREADSHEET CONFIG *****/
const TARGET_SPREADSHEET_ID = '1w9Hj4JMmjTIQM5c8FbXuKnTMjVOLipgXaC6WqeSV_vc';
const TARGET_SPREADSHEET_URL = 'https://docs.google.com/spreadsheets/d/' + TARGET_SPREADSHEET_ID + '/edit'
const TARGET_SPREADSHEET_NAME = 'BARS 2025 Product and Variant Creation'
const TARGET_HEADER_ROW = 1; // headers are on row 1 in the target
const SOURCE_LISTING_START_ROW = 3; // source headers end at row 2; data from row 2+

/***** CANONICAL LOCATIONS *****/
// Canonical, allowed locations (must map to one of these)
const CANONICAL_LOCATIONS = [
  "Elliott Center (26th St & 9th Ave)",
  "PS3 Charrette School (Grove St & Hudson St)",
  "Village Community School (10th St & Greenwich St)",
  "Hartley House (46th St & 9th Ave)",
  "Dewitt Clinton Park (52nd St & 11th Ave)",
  "Gansevoort Peninsula Athletic Park, Pier 53 (Gansevoort St & 11th)",
  "Chelsea Park (27th St & 9th Ave)",
  "Gotham Pickleball (46th and Vernon in LIC)",
  "John Jay College (59th and 10th)",
  "Pickle1 (7 Hanover Square in LIC)",
  "Frames Bowling Lounge (40th St and 9th Ave)",
  "Bowlero Chelsea Piers (60 Chelsea Piers)",
];

/***** HEADER MAPPING *****/
// Target header mapping (destination header -> object key)
const headerMapping = {
  "sport": "sport",
  "day": "day",
  "sport sub-category": "sportSubCategory",
  "division": "division",
  "season": "season",
  "year": "year",
  "social or advanced": "socialOrAdvanced",
  "type(s)": "types",
  "new player orientation date/time": "newPlayerOrientationDateTime",
  "scout night date/time": "scoutNightDateTime",
  "opening party date": "openingPartyDate",
  "season start date": "seasonStartDate",
  "season end date": "seasonEndDate",
  "alternative start time\n(optional)": "alternativeStartTime",
  "alternative end time\n(optional)": "alternativeEndTime",
  "off dates, separated by comma (leave blank if none)\n\nmake sure this is in the format m/d/yy": "offDatesCommaSeparated",
  "rain date": "rainDate",
  "closing party date": "closingPartyDate",
  "sport start time": "sportStartTime",
  "sport end time": "sportEndTime",
  "location": "location",
  "price": "price",
  "veteran registration start date/time\n(leave blank if no vet registration applies for this season)": "vetRegistrationStartDateTime",
  "early registration start date/time": "earlyRegistrationStartDateTime",
  "open registration start date/time": "openRegistrationStartDateTime",
  "total inventory": "totalInventory",
};

/***** REQUIRED TARGET HEADERS *****/
// Required destination headers (exactly as they appear in the sheet)
const REQUIRED_TARGET_HEADERS = [
  "sport",
  "day",
  "sport sub-category",
  "division",
  "season",
  "year",
  "type(s)",
  "season start date",
  "season end date",
  "sport start time",
  "sport end time",
  "location",
  "price",
  "early registration start date/time",
  "open registration start date/time",
  "total inventory",
];
