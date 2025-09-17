/**
 * Column C (League Details) parsing functions
 * Handles parsing of league details, special dates, inventory info, and other details
 *
 * @fileoverview Parse column C content for league details, dates, and inventory
 * @requires ../config/constants.gs
 * @requires ../helpers/textUtils.gs
 * @requires ../helpers/normalizers.gs
 * @requires ../helpers/dateParsers.gs
 */

// Import references for editor support
/// <reference path="../config/constants.gs" />
/// <reference path="../helpers/textUtils.gs" />
/// <reference path="../helpers/normalizers.gs" />
/// <reference path="../helpers/dateParsers.gs" />

/**
 * Parse column C content for league details and special information
 * @param {string} columnCData - Raw column C content
 * @returns {{closingPartyDate: Date|string|null, offDates: Array<Date>, tournamentDate: Date|null, totalInventory: number|null, typesHint: Array<string>}} Parsed league details
 */
function parseColCLeagueDetails_(columnCData) {
  // Initialize return values
  let closingPartyDate = null;
  let offDates = [];
  let tournamentDate = null;
  let totalInventory = null;
  let typesHint = [];

  // Handle null, undefined, or empty input
  if (!columnCData || typeof columnCData !== 'string' || !columnCData.trim()) {
    return {
      closingPartyDate,
      offDates,
      tournamentDate,
      totalInventory
    };
  }

  const lines = columnCData.split('\n').map(line => line.trim()).filter(line => line.length > 0);

  for (const line of lines) {
    const lowerLine = line.toLowerCase();

    // Parse closing party date
    if (lowerLine.includes('closing party')) {
      const colonIndex = line.indexOf(':');
      if (colonIndex > -1) {
        const dateStr = line.substring(colonIndex + 1).trim();
        if (dateStr.toLowerCase().includes('tbd') || dateStr.toLowerCase().includes('to be determined')) {
          closingPartyDate = 'TBD';
        } else {
          // Try to parse as date using parseFlexibleDate_
          const parsedDate = parseFlexibleDate_(dateStr, true);
          if (parsedDate) {
            closingPartyDate = parsedDate;
          }
        }
      }
    }

    // Parse tournament date
    if (lowerLine.includes('tournament date')) {
      const colonIndex = line.indexOf(':');
      if (colonIndex > -1) {
        const dateStr = line.substring(colonIndex + 1).trim();
        if (dateStr && !dateStr.toLowerCase().includes('tbd') && dateStr !== '') {
          // Try to parse as date using parseFlexibleDate_
          const parsedDate = parseFlexibleDate_(dateStr, true);
          if (parsedDate) {
            tournamentDate = parsedDate;
          }
        }
      }
    }

    // Parse off dates (skipping dates)
    if (lowerLine.includes('skipping') || lowerLine.includes('no games') || lowerLine.includes('off')) {
      // Extract date from "Skipping MM/DD" or similar patterns
      const skipMatch = line.match(/skipping\s+(.+)/i);
      if (skipMatch) {
        const dateStr = skipMatch[1].trim();
        const parsedDate = parseFlexibleDate_(dateStr, true);
        if (parsedDate) {
          offDates.push(parsedDate);
        }
      }
    }

    // Parse total inventory: handle patterns like "# of Players: N" and ranges like "350-364 players"
    if (lowerLine.includes('players')) {
      // Range pattern: e.g., 350-364 players
      const rangeMatch = line.match(/(\d+)\s*-\s*(\d+)\s*players/i);
      if (rangeMatch) {
        const a = Number.parseInt(rangeMatch[1], 10);
        const b = Number.parseInt(rangeMatch[2], 10);
        const maxVal = Math.max(a, b);
        if (!Number.isNaN(maxVal)) totalInventory = maxVal;
      }
      // Single pattern with label: # of Players: N  OR  players: N
      const playersMatch = line.match(/(?:#\s*of\s*players|players)\s*[:\-]?\s*(\d+)/i);
      if (playersMatch) {
        const val = Number.parseInt(playersMatch[1], 10);
        if (!Number.isNaN(val)) totalInventory = val;
      }
      // Single pattern without label: e.g., "192 players"
      const simplePlayers = line.match(/(^|\b)(\d{2,4})\s*players\b/i);
      if (simplePlayers) {
        const val2 = Number.parseInt(simplePlayers[2], 10);
        if (!Number.isNaN(val2)) {
          totalInventory = totalInventory != null ? Math.max(totalInventory, val2) : val2;
        }
      }
    }

    // Detect buddy sign-up capability to hint types
    if (lowerLine.includes('buddy')) {
      if (typesHint.indexOf('Buddy Sign-up') === -1) typesHint.push('Buddy Sign-up');
    }

    // Detect randomized teams hint
    if (lowerLine.includes('random')) {
      if (typesHint.indexOf('Randomized Teams') === -1) typesHint.push('Randomized Teams');
    }
  }

  return {
    closingPartyDate,
    offDates,
    tournamentDate,
    totalInventory,
    typesHint
  };
}
