/**
 * Location parsing with strict enum validation
 * Validates against allowed location values for each sport
 * Case and whitespace insensitive matching, returns full formatted value
 *
 * @fileoverview Location parsing with strict validation
 */

// Location enums by sport - full formatted values for descriptionHtml
const LOCATION_ENUMS = {
  "Dodgeball": [
    "Elliott Center (26th St & 9th Ave)",
    "PS3 Charrette School (Grove St & Hudson St)",
    "Village Community School (10th St & Greenwich St)",
    "Hartley House (46th St & 9th Ave)",
    "DeWitt Clinton Park (52nd St & 11th Ave)"
  ],
  "Kickball": [
    "Gansevoort Peninsula Athletic Park, Pier 53 (Gansevoort St & 11th)",
    "Chelsea Park (27th St & 9th Ave)",
    "DeWitt Clinton Park (52nd St & 11th Ave)"
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
};

// Mapping of sheet values (case/whitespace insensitive) to formatted values
const LOCATION_ALIASES = {
  "dewitt": "DeWitt Clinton Park (52nd St & 11th Ave)",
  "dewittclintonpark": "DeWitt Clinton Park (52nd St & 11th Ave)",
  "gansevoort": "Gansevoort Peninsula Athletic Park, Pier 53 (Gansevoort St & 11th)",
  "gansevoortpeninsulaathleticpark": "Gansevoort Peninsula Athletic Park, Pier 53 (Gansevoort St & 11th)",
  "chelseapark": "Chelsea Park (27th St & 9th Ave)",
  "elliottcenter": "Elliott Center (26th St & 9th Ave)",
  "ps3": "PS3 Charrette School (Grove St & Hudson St)",
  "ps3charretteschool": "PS3 Charrette School (Grove St & Hudson St)",
  "villagecomm": "Village Community School (10th St & Greenwich St)",
  "villagecommunityschool": "Village Community School (10th St & Greenwich St)",
  "hartley": "Hartley House (46th St & 9th Ave)",
  "hartleyhouse": "Hartley House (46th St & 9th Ave)",
  "gotham": "Gotham Pickleball (46th and Vernon in LIC)",
  "gothampickleball": "Gotham Pickleball (46th and Vernon in LIC)",
  "johnjay": "John Jay College (59th and 10th)",
  "johnjaycollege": "John Jay College (59th and 10th)",
  "pickle1": "Pickle1 (7 Hanover Square in LIC)",
  "frames": "Frames Bowling Lounge (40th St and 9th Ave)",
  "framesbowlinglounge": "Frames Bowling Lounge (40th St and 9th Ave)",
  "bowlero": "Bowlero Chelsea Piers (60 Chelsea Piers)",
  "bowlerochelseapiers": "Bowlero Chelsea Piers (60 Chelsea Piers)"
};

/**
 * Parse and validate location string with case/whitespace insensitive matching
 * Returns both raw and formatted values for descriptionHtml
 *
 * @param {string} locationInput - The raw location string content
 * @param {string} sportName - The sport name to get valid locations for
 * @returns {{location: {raw: string, formatted: string}|null}} Parsed location object or null if invalid
 */
export function parseLocation(locationInput, sportName) {
  // Handle null, undefined, or empty input
  if (!locationInput || typeof locationInput !== 'string' || !locationInput.trim()) {
    return { location: null };
  }

  const inputStr = locationInput.trim();

  // Get valid locations for this sport
  const validLocations = LOCATION_ENUMS[sportName];
  
  if (!validLocations || validLocations.length === 0) {
    console.warn(`No valid locations defined for sport: ${sportName}`);
    return { location: null };
  }

  // Normalize input: lowercase and remove all whitespace
  const normalizedInput = inputStr.toLowerCase().replace(/\s+/g, '');

  // Try to find match in aliases first
  const aliasMatch = LOCATION_ALIASES[normalizedInput];
  if (aliasMatch) {
    // Verify this location is valid for the sport
    if (validLocations.includes(aliasMatch)) {
      return {
        location: {
          raw: inputStr,
          formatted: aliasMatch
        }
      };
    }
  }

  // Try exact match (case/whitespace insensitive) against valid locations
  const exactMatch = validLocations.find(loc => {
    const normalizedLoc = loc.toLowerCase().replace(/\s+/g, '');
    return normalizedLoc === normalizedInput;
  });

  if (exactMatch) {
    return {
      location: {
        raw: inputStr,
        formatted: exactMatch
      }
    };
  }

  // No match found
  console.warn(`Invalid location "${inputStr}" for sport ${sportName}. Must be one of: ${validLocations.join(', ')}`);
  return { location: null };
}
