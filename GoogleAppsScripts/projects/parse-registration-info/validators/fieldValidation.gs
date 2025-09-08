/**
 * Field validation functions for parse-registration-info
 * Check required fields and data integrity
 * 
 * @fileoverview Field validation and header mapping
 * @requires ../config/constants.gs
 * @requires ../helpers/textUtils.gs
 */

// Import references for editor support
/// <reference path="../config/constants.gs" />
/// <reference path="../helpers/textUtils.gs" />

/**
 * Check that all required fields are present and valid
 */
function checkRequiredFields_(parsed, targetHeadersRaw, unresolved) {
  const missing = [];
  const targetHeadersNorm = targetHeadersRaw.map(normalizeHeader_);
  
  for (const reqHeader of REQUIRED_TARGET_HEADERS) {
    const reqIdx = targetHeadersNorm.indexOf(normalizeHeader_(reqHeader));
    // Find the object key we intend to write for this header
    // (reverse lookup using headerMapping)
    const objKey = headerMapping[reqHeader];
    if (reqIdx === -1) continue; // header not present in the target sheet
    
    const val = parsed[objKey];
    const isBlank =
      val === '' ||
      val == null ||
      (val instanceof Date && isNaN(val.valueOf())); // invalid date
      
    if (isBlank) missing.push(reqHeader);
  }
  
  return { missing, maybe: unresolved.slice() };
}

/**
 * Build fuzzy header index for column mapping
 */
function buildFuzzyHeaderIndex_(targetHeadersRaw) {
  const index = {
    headers: targetHeadersRaw.map((h, i) => ({
      raw: h,
      norm: normalizeHeader_(h),
      col: i + 1 // 1-based
    })),
    
    bestFor(query, opts = {}) {
      const threshold = opts.threshold || 0.7;
      const queryNorm = normalizeHeader_(query);
      
      let bestMatch = null;
      let bestScore = 0;
      
      for (const header of this.headers) {
        // Exact match gets priority
        if (header.norm === queryNorm) {
          return { ...header, score: 1.0 };
        }
        
        // Fuzzy matching
        const score = _simpleSimilarity(queryNorm, header.norm);
        if (score > bestScore && score >= threshold) {
          bestScore = score;
          bestMatch = { ...header, score };
        }
      }
      
      return bestMatch;
    }
  };
  
  return index;
}

/**
 * Get target index map for existing data
 */
function getTargetIndexMap_(targetSheet, headerRow) {
  const map = new Map();
  const lastRow = targetSheet.getLastRow();
  
  if (lastRow <= headerRow) return map;
  
  // Get all data including headers
  const allData = targetSheet.getRange(headerRow, 1, lastRow - headerRow + 1, targetSheet.getLastColumn()).getValues();
  const headers = allData[0];
  
  // Find key columns
  const sportCol = headers.findIndex(h => normalizeHeader_(h).includes('sport'));
  const dayCol = headers.findIndex(h => normalizeHeader_(h).includes('day'));
  const divisionCol = headers.findIndex(h => normalizeHeader_(h).includes('division'));
  const readyCol = headers.findIndex(h => normalizeHeader_(h).includes('ready'));
  
  // Process data rows
  for (let i = 1; i < allData.length; i++) {
    const row = allData[i];
    const sport = sportCol >= 0 ? (row[sportCol] || '').toString().trim() : '';
    const day = dayCol >= 0 ? (row[dayCol] || '').toString().trim() : '';
    const division = divisionCol >= 0 ? (row[divisionCol] || '').toString().trim() : '';
    const ready = readyCol >= 0 ? (row[readyCol] || '').toString().toLowerCase() === 'true' : false;
    
    if (sport || day) {
      const key = makeKey_(sport, day, division);
      map.set(key, {
        row: headerRow + i,
        readyTrue: ready,
        sport,
        day,
        division
      });
    }
  }
  
  return map;
}
