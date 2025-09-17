/**
 * Text processing and normalization helpers for parse-registration-info
 */


/**
 * Split text into lines and clean them
 * @param {string} text - Text to split
 * @returns {Array<string>} Array of lines - if single line, returns [text], if multiple lines, returns split array
 */
function splitLines_(text) {
  if (!text) return [];

  // Check if text contains line breaks
  if (!/\r?\n/.test(text)) {
    // Single line - return as array with one element
    const trimmed = text.trim();
    return trimmed ? [trimmed] : [];
  }

  // Multiple lines - split and filter
  return text.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
}

/**
 * Simple similarity function for fuzzy matching
 */
function _simpleSimilarity(a, b) {
  if (!a || !b) return 0;
  const longer = a.length > b.length ? a : b;
  const shorter = a.length > b.length ? b : a;
  if (longer.length === 0) return 1;
  return (longer.length - _editDistance(longer, shorter)) / longer.length;
}

/**
 * Calculate edit distance between two strings
 */
function _editDistance(a, b) {
  const matrix = [];
  for (let i = 0; i <= b.length; i++) {
    matrix[i] = [i];
  }
  for (let j = 0; j <= a.length; j++) {
    matrix[0][j] = j;
  }
  for (let i = 1; i <= b.length; i++) {
    for (let j = 1; j <= a.length; j++) {
      if (b.charAt(i - 1) === a.charAt(j - 1)) {
        matrix[i][j] = matrix[i - 1][j - 1];
      } else {
        matrix[i][j] = Math.min(
          matrix[i - 1][j - 1] + 1,
          matrix[i][j - 1] + 1,
          matrix[i - 1][j] + 1
        );
      }
    }
  }
  return matrix[b.length][a.length];
}

/**
 * Normalize header text for fuzzy matching
 */
function normalizeHeader_(header) {
  return (header || '').toLowerCase().replace(/[^a-z0-9]/g, '');
}

/**
 * Create a unique key for sport/day/division combinations
 */
function makeKey_(sport, day, division) {
  return `${sport}|${day}|${division || ''}`.toLowerCase();
}

/**
 * Extract player count from details text
 */
function extractPlayersFromDetails_(details, unresolved) {
  const text = (details || '').replace(/\s+/g, ' ');

  // 1) Range like "350-364 players" → take max
  let m = text.match(/\b(\d{1,5})\s*[-–—]\s*(\d{1,5})\s*players?\b/i);
  if (m) {
    const result = Math.max(Number(m[1]), Number(m[2]));
    if (result && unresolved) {
      const index = unresolved.indexOf("totalInventory");
      if (index > -1) unresolved.splice(index, 1);
    }
    return result;
  }

  // 2) Explicit count formats
  //    a) "60 players" (number BEFORE the word)
  m = text.match(/\b(\d{1,5})\s*players?\b/i);
  if (m) {
    const result = Number(m[1]);
    if (result && unresolved) {
      const index = unresolved.indexOf("totalInventory");
      if (index > -1) unresolved.splice(index, 1);
    }
    return result;
  }

  //    b) "Players: 60" or "# of Players: 60" (number AFTER the word)
  m = text.match(/(?:#\s*of\s*)?players?\s*[:\-]\s*(\d{1,5})/i);
  if (m) {
    const result = Number(m[1]);
    if (result && unresolved) {
      const index = unresolved.indexOf("totalInventory");
      if (index > -1) unresolved.splice(index, 1);
    }
    return result;
  }

  // 3) Teams x players-per-team → multiply (e.g., "6 teams of 10" => 60)
  m = text.match(/\b(\d{1,4})\s*teams?\s*of\s*(\d{1,4})\b/i);
  if (m) {
    const result = Number(m[1]) * Number(m[2]);
    if (result && unresolved) {
      const index = unresolved.indexOf("totalInventory");
      if (index > -1) unresolved.splice(index, 1);
    }
    return result;
  }

  // 4) "364 (X players per team)" keep the first big number
  m = text.match(/\b(\d{1,5})\s*\(\s*\d+\s*players?\s*per\s*team/i);
  if (m) {
    const result = Number(m[1]);
    if (result && unresolved) {
      const index = unresolved.indexOf("totalInventory");
      if (index > -1) unresolved.splice(index, 1);
    }
    return result;
  }

  // 5) Very last resort: a number *immediately after* "players"
  //    (tighten the window to avoid picking dates like 11/9)
  m = text.match(/\bplayers?\b[^0-9]{0,5}(\d{1,5})(?!\/)/i);
  if (m) {
    const result = Number(m[1]);
    if (result && unresolved) {
      const index = unresolved.indexOf("totalInventory");
      if (index > -1) unresolved.splice(index, 1);
    }
    return result;
  }

  // Total inventory not found - leave "totalInventory" in unresolved array
  return '';
}
