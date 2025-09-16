/**
 * Parses location from column H using simple contains logic.
 * Much simpler than the previous fuzzy matching approach.
 *
 * @fileoverview Location parsing for column H
 * @requires ../config/constants.gs
 */

// Import references for editor support
/// <reference path="../config/constants.gs" />

/**
 * Parses the location string from column H using simple case-insensitive contains logic.
 *
 * @param {string} hColumnData - The raw string content from column H.
 * @param {string} sportName - The sport name to get valid locations for.
 * @returns {{location: string | null}} Parsed location or null
 */
function parseColHLocation_(hColumnData, sportName) {
  let location = null;

  const inputStr = (hColumnData || '').trim();
  if (!inputStr) {
    return { location };
  }

  // Get sport-specific locations from productFieldEnums
  const validLocations = productFieldEnums.location?.[sportName]
    ? productFieldEnums.location[sportName]
    : [];

  if (validLocations.length === 0) {
    // No valid locations for this sport - return null
    location = inputStr;
    return { location };
  }

  // Convert input to lowercase for case-insensitive matching
  const lowerInput = inputStr.toLowerCase();

  // Simple contains logic (case insensitive)
  for (const enumLocation of validLocations) {
    let found = false;

    // frames -> frames string from enum
    if (lowerInput.includes('frames') && enumLocation.toLowerCase().includes('frames')) {
      location = enumLocation;
      found = true;
    }
    // dewitt -> dewitt string from enum
    else if (lowerInput.includes('dewitt') && enumLocation.toLowerCase().includes('dewitt')) {
      location = enumLocation;
      found = true;
    }
    // ganse -> gansevoort from enum
    else if (lowerInput.includes('ganse') && enumLocation.toLowerCase().includes('gansevoort')) {
      location = enumLocation;
      found = true;
    }
    // chelsea park -> chelsea park from enum
    else if (lowerInput.includes('chelsea park') && enumLocation.toLowerCase().includes('chelsea park')) {
      location = enumLocation;
      found = true;
    }
    // vcs or village community -> village community school from enum
    else if ((lowerInput.includes('vcs') || lowerInput.includes('village community')) &&
             enumLocation.toLowerCase().includes('village community')) {
      location = enumLocation;
      found = true;
    }
    // hartley -> hartley house from enum
    else if (lowerInput.includes('hartley') && enumLocation.toLowerCase().includes('hartley')) {
      location = enumLocation;
      found = true;
    }
    // ps3 (removing non-alphanumeric) or charette -> PS3 from enum
    else if ((removeNonAlphanumeric_(lowerInput).includes('ps3') || lowerInput.includes('charrette')) &&
             enumLocation.toLowerCase().includes('ps3')) {
      location = enumLocation;
      found = true;
    }
    // john jay -> john jay from enum
    else if (lowerInput.includes('john jay') && enumLocation.toLowerCase().includes('john jay')) {
      location = enumLocation;
      found = true;
    }
    // gotham pickle -> gotham pickle from enum
    else if (lowerInput.includes('gotham pickle') && enumLocation.toLowerCase().includes('gotham pickle')) {
      location = enumLocation;
      found = true;
    }
    // pickle 1 or pickle1 -> pickle1 from enum
    else if ((lowerInput.includes('pickle 1') || lowerInput.includes('pickle1')) &&
             enumLocation.toLowerCase().includes('pickle1')) {
      location = enumLocation;
      found = true;
    }
  }

  // If no match found, location remains null
  return { location };
}

/**
 * Helper function to remove non-alphanumeric characters from a string
 * @param {string} str - The input string
 * @returns {string} String with only alphanumeric characters (lowercase)
 */
function removeNonAlphanumeric_(str) {
  return str.replace(/[^a-zA-Z0-9]/g, '').toLowerCase();
}
