/**
 * Parse B-column flags and categorization data
 * Extracts division, sport sub-category, social/advanced, and types
 * 
 * @fileoverview B-column flags and categorization parser
 * @requires ../helpers/textUtils.gs
 */

// Import references for editor support
/// <reference path="../helpers/textUtils.gs" />

/**
 * Parse flags from B column lines and notes text
 * @param {Array<string>} linesFromB - Lines from B column
 * @param {Array<string>} unresolved - Array to collect parsing issues
 * @param {string} notesText - Additional notes text
 * @returns {{division: string, sportSubCategory: string, socialOrAdvanced: string, types: Array<string>}} Parsed flags
 */
function parseBFlags_(linesFromB, unresolved, notesText) {
  const joined = ' ' + linesFromB.join(' ').replace(/\s+/g, ' ') + ' ';
  const text = (notesText || '') + ' ' + joined; // unify signals from B + C

  // ---------- Division ----------
  // Default
  let division = 'N/A';
  const divSrc = text.toLowerCase();

  if (/\b(wtnb|tnb|bipoc)\b/i.test(divSrc)) {
    division = 'WTNB+';
  } else if (/\bopen\b/i.test(divSrc)) {
    division = 'Open';
  } else {
    // fuzzy division: look for near "open" or "wtnb"
    const CANDS = ['Open', 'WTNB+'];
    let best = '', scBest = 0;
    for (const cand of CANDS) {
      const sc = _simpleSimilarity(divSrc, cand);
      if (sc > scBest) { scBest = sc; best = cand; }
    }
    if (scBest >= 0.7) {
      unresolved.push(`Division might be "${best}" (similarity ${scBest.toFixed(2)}) → populated in target`);
      division = best;
    } else {
      unresolved.push('Division not detected → omitted (left blank)');
      division = ''; // treat N/A as blank for required checks
    }
  }

  // ---------- Social or Advanced ----------
  let socialOrAdvanced = '';
  if (/\bsocial\b/i.test(text)) socialOrAdvanced = 'Social';
  if (/\badvanced|competitive|comp\b/i.test(text)) socialOrAdvanced = 'Advanced';
  if (!socialOrAdvanced) {
    // fuzzy: check proximity to tokens
    const tokens = ['Social', 'Advanced'];
    let best = '', scBest = 0;
    for (const cand of tokens) {
      const sc = _simpleSimilarity(text, cand);
      if (sc > scBest) { scBest = sc; best = cand; }
    }
    if (scBest >= 0.75) {
      unresolved.push(`Social/Advanced might be "${best}" (similarity ${scBest.toFixed(2)}) → populated in target`);
      socialOrAdvanced = best;
    }
  }

  // ---------- Sport Sub-Category (Dodgeball) ----------
  // Normalize several variants → canonical set
  let sportSubCategory = 'N/A';
  if (/\bno[-\s]?sting\b/i.test(text) || /\bsmall\s*ball\b/i.test(text)) sportSubCategory = 'Small Ball';
  if (/\bbig\s*ball\b/i.test(text)) sportSubCategory = 'Big Ball';
  if (/\bfoam\b/i.test(text)) sportSubCategory = 'Foam';
  if (sportSubCategory === 'N/A') {
    const SUBS = ['Small Ball','Big Ball','Foam'];
    let best = '', scBest = 0;
    for (const cand of SUBS) {
      const sc = _simpleSimilarity(text, cand);
      if (sc > scBest) { scBest = sc; best = cand; }
    }
    if (scBest >= 0.7) {
      unresolved.push(`Sport Sub-Category might be "${best}" (similarity ${scBest.toFixed(2)}) → populated in target`);
      sportSubCategory = best;
    } else {
      // not required; leave as 'N/A' (or '' if you prefer)
      sportSubCategory = 'N/A';
    }
  }

  // ---------- Types (merge B + C) ----------
  const typesSet = new Set();

  // Draft
  if (/\bdraft\b/i.test(text)) typesSet.add('Draft');

  // Randomized
  if (/\brandomized\b/i.test(text)) typesSet.add('Randomized Teams');

  if (hasBuddySignup_(text)) {
    typesSet.add('Buddy Sign-up');
  }

  // Captain signup
  if (/\bcaptain\s*signup\b/i.test(text)) {
    typesSet.add('Captain Signup');
  }

  return {
    division,
    sportSubCategory,
    socialOrAdvanced,
    types: Array.from(typesSet)
  };
}

/**
 * Check for buddy signup patterns in text
 */
function hasBuddySignup_(text) {
  const patterns = [
    /buddy/i,                         // "buddy" in any form, case-insensitive
    /\bbuddy\s*signup\b/i,            // explicit "buddy signup"
    /\bsign\s*up\s*with\s*friend/i,   // "sign up with friend"
    /\bfriend\s*signup/i,             // "friend signup"
    /\bpartner\s*signup/i             // "partner signup"
  ];
  
  return patterns.some(pattern => pattern.test(text));
}
