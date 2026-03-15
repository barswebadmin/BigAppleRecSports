/**
 * Parse day of week and type of play/league data
 * Extracts day, division, level of play, team assignment, and dodgeball ball type
 *
 * Format expected:
 * - Line 1: Day of week (case insensitive)
 * - Line 2: Empty or dodgeball ball type (bigBall, smallBall, foam - Dodgeball only)
 * - Line 3: Division (Open or WTNB+, case insensitive, with or without +)
 * - Line 4: Level of play (Social, Advanced, Competitive/Advanced, Intermediate/Advanced, or null)
 * - Line 5: Team assignment (randomized, randomizedWithBuddy, draft, ladder, or none, case insensitive)
 *
 * @fileoverview Parser for day and categorization data
 */

import { splitLines } from '../helpers/textUtils.js';
import { normalizeDay } from '../helpers/normalizers.js';

/**
 * Parse data to extract day and league info
 * @param {string} leagueBasicInfoData - Raw data containing day and league info
 * @param {string} sportName - Sport name for conditional logic
 * @returns {{dayOfPlay: string, division: string, levelOfPlay: {raw: string, formatted: string}|null, teamAssignment: {raw: string, formatted: string}|null, dodgeballBallType: string|null}} Parsed data
 */

// biome-ignore lint/correctness/noUnusedVariables: <it is called in the flow from menu item click>
export function parseLeagueBasicInfo(leagueBasicInfoData, sportName) {
  // Split data into lines
  const bLines = splitLines(leagueBasicInfoData).map(line => line.trim()).filter(line => line.length > 0);

  // Extract day from first line (case insensitive)
  const dayRaw = bLines[0] || '';
  const dayOfPlay = normalizeDay(dayRaw);

  // ---------- Dodgeball Ball Type (Dodgeball only) ----------
  let dodgeballBallType = null;
  if (sportName === 'Dodgeball') {
    for (let i = 1; i < bLines.length; i++) {
      const line = bLines[i].toLowerCase().trim();
      if (line === 'bigball' || line === 'big ball') {
        dodgeballBallType = 'Big Ball';
        break;
      } else if (line === 'smallball' || line === 'small ball') {
        dodgeballBallType = 'Small Ball';
        break;
      } else if (line === 'foam') {
        dodgeballBallType = 'Foam';
        break;
      }
    }
  }

  // ---------- Division ----------
  // Look for division in the lines (Open or WTNB+)
  let division = '';
  for (let i = 1; i < bLines.length; i++) {
    const line = bLines[i].toLowerCase().trim();
    if (line === 'open') {
      division = 'Open';
      break;
    } else if (line.includes('wtnb')) {
      division = 'WTNB+';
      break;
    }
  }

  // ---------- Level of Play ----------
  // Look for level of play keywords, return with raw and formatted values
  let levelOfPlay = null;
  for (let i = 1; i < bLines.length; i++) {
    const line = bLines[i].toLowerCase().trim();
    
    if (line === 'social') {
      levelOfPlay = { raw: bLines[i].trim(), formatted: 'Social' };
      break;
    } else if (line === 'advanced') {
      levelOfPlay = { raw: bLines[i].trim(), formatted: 'Advanced' };
      break;
    } else if (line === 'competitive/advanced' || line === 'competitive / advanced') {
      levelOfPlay = { raw: bLines[i].trim(), formatted: 'Competitive/Advanced' };
      break;
    } else if (line === 'intermediate/advanced' || line === 'intermediate / advanced') {
      levelOfPlay = { raw: bLines[i].trim(), formatted: 'Intermediate/Advanced' };
      break;
    }
  }

  // ---------- Team Assignment ----------
  // Look for team assignment keywords: randomized, randomizedWithBuddy, draft, ladder
  // Return with raw and formatted values
  let teamAssignment = null;
  for (let i = 1; i < bLines.length; i++) {
    const line = bLines[i].toLowerCase().trim().replace(/[\s-]/g, '');
    const rawLine = bLines[i].trim();
    
    if (line === 'randomizedbuddy' || line === 'randomizedwithbuddy') {
      teamAssignment = { raw: rawLine, formatted: 'randomizedWithBuddy' };
      break;
    } else if (line === 'randomized') {
      teamAssignment = { raw: rawLine, formatted: 'randomized' };
      break;
    } else if (line === 'draft') {
      teamAssignment = { raw: rawLine, formatted: 'draft' };
      break;
    } else if (line === 'ladder') {
      teamAssignment = { raw: rawLine, formatted: 'ladder' };
      break;
    } else if (line === 'none') {
      teamAssignment = { raw: rawLine, formatted: 'none' };
      break;
    }
  }

  return {
    dayOfPlay,
    division,
    levelOfPlay,
    teamAssignment,
    dodgeballBallType
  };
}
