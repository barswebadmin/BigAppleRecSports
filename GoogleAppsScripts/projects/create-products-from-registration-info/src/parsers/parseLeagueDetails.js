/**
 * League Details parsing functions
 * Handles parsing of league details, special dates, inventory info, and other details
 *
 * @fileoverview Parse league details content for dates and inventory
 * @requires ../config/constants.gs
 * @requires ../helpers/textUtils.gs
 * @requires ../helpers/normalizers.gs
 * @requires ../helpers/dateParsers.gs
 */

import { parseFlexibleDate } from '../helpers/dateParsers.js';

/**
 * Parse league details content for special information
 * Expected format (newline-separated):
 * - Total # of Weeks: {n}
 * - Newbie Night: M/d/yy {or none} (optional)
 * - Scout Night: M/d/yy {or none} (optional)
 * - Opening Party: M/d/yy {or none}
 * - Regular Season: {n} weeks {or none}
 * - Rain Date: {M/d/yy or none}
 * - Closing Party: {m/d/yy or none}
 * - Off Dates: {m/d one or multiple, comma separated if multiple, or none}
 * - # of Players: 120 (15 players per team) {may or may not have parenthetical}
 * - Game Duration: 45 min
 * 
 * @param {string} leagueDetailsData - Raw league details content
 * @returns {{totalWeeks: number|null, newPlayerOrientationDateTime: Date|string|null, scoutNightDateTime: Date|string|null, openingPartyDate: Date|string|null, rainDate: Date|string|null, closingPartyDate: Date|string|null, offDates: Array<Date>, totalInventory: number|null, gameDuration: string|null}} Parsed league details
 */
export function parseLeagueDetails(leagueDetailsData) {
  // Initialize return values
  let totalWeeks = null;
  let newPlayerOrientationDateTime = null;
  let scoutNightDateTime = null;
  let openingPartyDate = null;
  let rainDate = null;
  let closingPartyDate = null;
  let offDates = [];
  let totalInventory = null;
  let gameDuration = null;

  // Handle null, undefined, or empty input
  if (!leagueDetailsData || typeof leagueDetailsData !== 'string' || !leagueDetailsData.trim()) {
    return {
      totalWeeks,
      newPlayerOrientationDateTime,
      scoutNightDateTime,
      openingPartyDate,
      rainDate,
      closingPartyDate,
      offDates,
      totalInventory,
      gameDuration
    };
  }

  const lines = leagueDetailsData.split('\n').map(line => line.trim()).filter(line => line.length > 0);

  for (const line of lines) {
    const lowerLine = line.toLowerCase();

    // Parse total # of weeks
    if (lowerLine.includes('total') && lowerLine.includes('weeks')) {
      const weeksMatch = line.match(/(\d+)/);
      if (weeksMatch) {
        totalWeeks = Number.parseInt(weeksMatch[1], 10);
      }
    }

    // Parse newbie night (new player orientation)
    if (lowerLine.includes('newbie night')) {
      const colonIndex = line.indexOf(':');
      if (colonIndex > -1) {
        const dateStr = line.substring(colonIndex + 1).trim();
        if (dateStr.toLowerCase() === 'none' || dateStr === '') {
          newPlayerOrientationDateTime = null;
        } else if (dateStr.toLowerCase().includes('tbd') || dateStr.toLowerCase().includes('to be determined')) {
          newPlayerOrientationDateTime = 'TBD';
        } else {
          const parsedDate = parseFlexibleDate(dateStr, true);
          if (parsedDate) {
            newPlayerOrientationDateTime = parsedDate;
          }
        }
      }
    }

    // Parse scout night
    if (lowerLine.includes('scout night')) {
      const colonIndex = line.indexOf(':');
      if (colonIndex > -1) {
        const dateStr = line.substring(colonIndex + 1).trim();
        if (dateStr.toLowerCase() === 'none' || dateStr === '') {
          scoutNightDateTime = null;
        } else if (dateStr.toLowerCase().includes('tbd') || dateStr.toLowerCase().includes('to be determined')) {
          scoutNightDateTime = 'TBD';
        } else {
          const parsedDate = parseFlexibleDate(dateStr, true);
          if (parsedDate) {
            scoutNightDateTime = parsedDate;
          }
        }
      }
    }

    // Parse opening party date
    if (lowerLine.includes('opening party')) {
      const colonIndex = line.indexOf(':');
      if (colonIndex > -1) {
        const dateStr = line.substring(colonIndex + 1).trim();
        if (dateStr.toLowerCase() === 'none' || dateStr === '') {
          openingPartyDate = null;
        } else if (dateStr.toLowerCase().includes('tbd') || dateStr.toLowerCase().includes('to be determined')) {
          openingPartyDate = 'TBD';
        } else {
          const parsedDate = parseFlexibleDate(dateStr, true);
          if (parsedDate) {
            openingPartyDate = parsedDate;
          }
        }
      }
    }

    // Parse rain date
    if (lowerLine.includes('rain date')) {
      const colonIndex = line.indexOf(':');
      if (colonIndex > -1) {
        const dateStr = line.substring(colonIndex + 1).trim();
        if (dateStr.toLowerCase() === 'none' || dateStr === '') {
          rainDate = null;
        } else if (dateStr.toLowerCase().includes('tbd') || dateStr.toLowerCase().includes('to be determined')) {
          rainDate = 'TBD';
        } else {
          const parsedDate = parseFlexibleDate(dateStr, true);
          if (parsedDate) {
            rainDate = parsedDate;
          }
        }
      }
    }

    // Parse closing party date
    if (lowerLine.includes('closing party')) {
      const colonIndex = line.indexOf(':');
      if (colonIndex > -1) {
        const dateStr = line.substring(colonIndex + 1).trim();
        if (dateStr.toLowerCase() === 'none' || dateStr === '') {
          closingPartyDate = null;
        } else if (dateStr.toLowerCase().includes('tbd') || dateStr.toLowerCase().includes('to be determined')) {
          closingPartyDate = 'TBD';
        } else {
          const parsedDate = parseFlexibleDate(dateStr, true);
          if (parsedDate) {
            closingPartyDate = parsedDate;
          }
        }
      }
    }

    // Parse off dates - support comma-separated dates
    if (lowerLine.includes('off dates')) {
      const colonIndex = line.indexOf(':');
      if (colonIndex > -1) {
        const datesStr = line.substring(colonIndex + 1).trim();
        if (datesStr.toLowerCase() !== 'none' && datesStr !== '') {
          // Split by comma and parse each date
          const dateTokens = datesStr.split(',').map(s => s.trim());
          for (const token of dateTokens) {
            const parsedDate = parseFlexibleDate(token, true);
            if (parsedDate) {
              offDates.push(parsedDate);
            }
          }
        }
      }
    }

    // Parse # of players (ignore parenthetical)
    if (lowerLine.includes('# of players') || lowerLine.includes('number of players')) {
      const colonIndex = line.indexOf(':');
      if (colonIndex > -1) {
        const playersStr = line.substring(colonIndex + 1).trim();
        // Remove parenthetical if present
        const cleanedStr = playersStr.replace(/\s*\([^)]*\)\s*/g, '').trim();
        if (cleanedStr.toLowerCase() !== 'none' && cleanedStr !== '') {
          const playersMatch = cleanedStr.match(/(\d+)/);
          if (playersMatch) {
            totalInventory = Number.parseInt(playersMatch[1], 10);
          }
        }
      }
    }

    // Parse game duration
    if (lowerLine.includes('game duration')) {
      const colonIndex = line.indexOf(':');
      if (colonIndex > -1) {
        const durationStr = line.substring(colonIndex + 1).trim();
        if (durationStr.toLowerCase() !== 'none' && durationStr !== '') {
          gameDuration = durationStr;
        }
      }
    }
  }

  return {
    totalWeeks,
    newPlayerOrientationDateTime,
    scoutNightDateTime,
    openingPartyDate,
    rainDate,
    closingPartyDate,
    offDates,
    totalInventory,
    gameDuration
  };
}
