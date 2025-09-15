/**
 * Parse B-column data including day and flags
 * Extracts day, division, sport sub-category, social/advanced, and types
 *
 * @fileoverview B-column comprehensive parser for day and categorization data
 */

// Import references for editor support

/**
 * Parse B column data to extract day and flags
 * @param {string} bColumnData - Raw B column data containing day and flags
 * @param {Array<string>} unresolved - Array to collect parsing issues
 * @returns {{day: string, division: string, sportSubCategory: string, socialOrAdvanced: string, types: Array<string>}} Parsed B column data
 */

// biome-ignore lint/correctness/noUnusedVariables: <it is called in the flow from menu item click>
function parseColBLeagueDetails_(bColumnData, unresolved, sportName) {
  // Split B column into lines
  const bLines = splitLines_(bColumnData);

  // Extract day from first line
  const dayRaw = bLines[0] || '';
  const dayOfPlay = normalizeDay_(dayRaw);

  if (dayOfPlay && unresolved) {
    const index = unresolved.indexOf("dayOfPlay");
    if (index > -1) unresolved.splice(index, 1);
  }

  // ---------- Division ----------
  let division = '';
  let divisionElementIndex = -1;

  // Look through bLines elements for division keywords
  for (let i = 0; i < bLines.length; i++) {
    const line = bLines[i].toLowerCase().trim();
    if (line.includes('open')) {
      division = 'Open';
      divisionElementIndex = i;
      break;
    } else if (line.includes('wtnb')) {
      division = 'WTNB+';
      divisionElementIndex = i;
      break;
    }
  }

  // If division found, remove element from bLines and field from unresolved
  if (division && divisionElementIndex !== -1) {
    bLines.splice(divisionElementIndex, 1);
    const unresolvedIndex = unresolved.indexOf("division");
    if (unresolvedIndex > -1) unresolved.splice(unresolvedIndex, 1);
  }

  // ---------- Social or Advanced ----------
  let socialOrAdvanced = '';
  let socialAdvancedElementIndex = -1;

  // For Dodgeball, check if any line contains sport sub-category keywords and use that line for socialOrAdvanced
  if (sportName === 'Dodgeball') {
    for (let i = 0; i < bLines.length; i++) {
      const line = bLines[i].toLowerCase().trim();

      // Check if this line contains sport sub-category keywords
      if (line.includes('small') || line.includes('no-sting') || line.includes('no sting') ||
          line.includes('big') || line.includes('8.5') || line.includes('foam')) {
        socialOrAdvanced = bLines[i].trim(); // Use the sport sub-category line for socialOrAdvanced
        socialAdvancedElementIndex = i;
        break;
      }
    }

    // If no sport sub-category line found, fall back to social/advanced keyword search
    if (!socialOrAdvanced) {
      for (let i = 0; i < bLines.length; i++) {
        const line = bLines[i].toLowerCase();
        if (line.includes('social') || line.includes('advanced') || line.includes('competitive') || line.includes('intermediate')) {
          socialOrAdvanced = bLines[i].trim();
          socialAdvancedElementIndex = i;
          break;
        }
      }
    }
  } else {
    // Non-Dodgeball logic: Search for elements containing social/advanced/competitive/intermediate keywords
    for (let i = 0; i < bLines.length; i++) {
      const line = bLines[i].toLowerCase();
      if (line.includes('social') || line.includes('advanced') || line.includes('competitive') || line.includes('intermediate')) {
        // Check if this element contains multiple keywords
        const hasSocial = line.includes('social');
        const hasAdvanced = line.includes('advanced') || line.includes('competitive');

        if (hasSocial && hasAdvanced) {
          socialOrAdvanced = 'Mixed Social/Advanced';
        } else {
          socialOrAdvanced = bLines[i].trim();
        }

        socialAdvancedElementIndex = i;
        break;
      }
    }
  }

  // If socialOrAdvanced found, remove element from bLines and field from unresolved
  // For Dodgeball, don't remove the element since sportSubCategory may be on the same line
  if (socialOrAdvanced && socialAdvancedElementIndex !== -1) {
    if (sportName !== "Dodgeball") {
      bLines.splice(socialAdvancedElementIndex, 1);
    }
    const unresolvedIndex = unresolved.indexOf("socialOrAdvanced");
    if (unresolvedIndex > -1) unresolved.splice(unresolvedIndex, 1);
  }

  // ---------- Sport Sub-Category (Dodgeball only) ----------
  let sportSubCategory = '';
  let sportSubCategoryElementIndex = -1;

  // Only check sport sub-category for Dodgeball
  if (sportName === 'Dodgeball') {
    for (let i = 0; i < bLines.length; i++) {
      const line = bLines[i].toLowerCase().trim();

      if (line.includes('small') || line.includes('no-sting') || line.includes('no sting')) {
        sportSubCategory = 'Small Ball';
        sportSubCategoryElementIndex = i;
        break;
      } else if (line.includes('big') || line.includes('8.5')) {
        sportSubCategory = 'Big Ball';
        sportSubCategoryElementIndex = i;
        break;
      } else if (line.includes('foam')) {
        sportSubCategory = 'Foam';
        sportSubCategoryElementIndex = i;
        break;
      }
    }

    // If sportSubCategory found, remove element from bLines and field from unresolved
    if (sportSubCategory && sportSubCategoryElementIndex !== -1) {
      bLines.splice(sportSubCategoryElementIndex, 1);
      const unresolvedIndex = unresolved.indexOf("sportSubCategory");
      if (unresolvedIndex > -1) unresolved.splice(unresolvedIndex, 1);
    }
  }

  // ---------- Types ----------
  let types = [];
  let foundDraftOrNewbie = false;

  for (let i = 0; i < bLines.length; i++) {
    const line = bLines[i].toLowerCase().trim();

    // Check in priority order
    if (line.includes('draft')) {
      types = ['Draft'];
      foundDraftOrNewbie = true;
      break;
    }

    // Check for 'with * new' pattern (with or without 'a')
    if (/with.*new/i.test(line)) {
      types = ['Sign up with a newbie (randomized otherwise)'];
      foundDraftOrNewbie = true;
      break;
    }
  }


  // If we haven't found draft or buddy-with-newbie-only, continue looking for other types
  if (!foundDraftOrNewbie) {
    let hasRandom = false;
    let hasBuddy = false;

    for (let i = 0; i < bLines.length; i++) {
      const line = bLines[i].toLowerCase().trim();

      if (line.includes('random')) {
        hasRandom = true;
      }

      if (line.includes('buddy') || line.includes('friend') || line.includes('partner')) {
        hasBuddy = true;
      }
    }

    // Build types array based on what we found
    if (hasRandom && hasBuddy) {
      types = ['Randomized Teams, Buddy Sign-up'];
    } else if (hasRandom) {
      types = ['Randomized Teams'];
    } else if (hasBuddy) {
      types = ['Buddy Sign-up'];
    }
  }

  // Remove types from unresolved if any types were found
  if (types.length > 0 && unresolved) {
    const typesIndex = unresolved.indexOf("types");
    if (typesIndex > -1) unresolved.splice(typesIndex, 1);
  }


  return {
    dayOfPlay,
    division,
    sportSubCategory,
    socialOrAdvanced,
    types
  };
}
