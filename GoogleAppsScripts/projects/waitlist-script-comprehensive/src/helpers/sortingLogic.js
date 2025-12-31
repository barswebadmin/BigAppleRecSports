/**
 * Waitlist option sorting logic
 */

/**
 * Sort waitlist options according to specified logic:
 * 1. Alphabetical by sport
 * 2. Chronological by day  
 * 3. Reverse alphabetical by division
 * 4. Alphabetical by otherIdentifier
 * Items without sport go to bottom, with additional sorting by year/month
 */
export const sortWaitlistLabels = (labels) => {
  const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const DIVISIONS = ['Open', 'WTNB+', 'WTNB', 'wtnb'];
  
  return labels.sort((a, b) => {
    const parsedA = parseLabelForSorting(a);
    const parsedB = parseLabelForSorting(b);

    // Items with sport go first
    if (parsedA.hasSport && !parsedB.hasSport) return -1;
    if (!parsedA.hasSport && parsedB.hasSport) return 1;

    if (parsedA.hasSport && parsedB.hasSport) {
      // Sort by sport alphabetically
      const sportCompare = parsedA.sport.localeCompare(parsedB.sport);
      if (sportCompare !== 0) return sportCompare;

      // Sort by day chronologically
      const dayIndexA = DAYS.indexOf(parsedA.day);
      const dayIndexB = DAYS.indexOf(parsedB.day);
      if (dayIndexA !== dayIndexB) {
        if (dayIndexA === -1) return 1;
        if (dayIndexB === -1) return -1;
        return dayIndexA - dayIndexB;
      }

      // Sort by division reverse alphabetically
      const divIndexA = DIVISIONS.indexOf(parsedA.division);
      const divIndexB = DIVISIONS.indexOf(parsedB.division);
      if (divIndexA !== divIndexB) {
        if (divIndexA === -1) return 1;
        if (divIndexB === -1) return -1;
        return divIndexA - divIndexB;
      }

      // Sort by other identifier alphabetically
      return parsedA.otherIdentifier.localeCompare(parsedB.otherIdentifier);
    }

    // Both items without sport - sort by year/month logic, then alphabetically
    const yearA = extractYear(a);
    const yearB = extractYear(b);
    const monthA = extractMonth(a);
    const monthB = extractMonth(b);

    // Items with years first
    if (yearA && !yearB) return -1;
    if (!yearA && yearB) return 1;

    if (yearA && yearB) {
      if (yearA !== yearB) return yearA - yearB;
      
      // Same year, sort by month if available
      if (monthA && !monthB) return -1;
      if (!monthA && monthB) return 1;
      if (monthA && monthB && monthA !== monthB) return monthA - monthB;
    }

    // Items with months (no year) come before items without months
    if (monthA && !monthB) return -1;
    if (!monthA && monthB) return 1;

    // Default alphabetical
    return a.localeCompare(b);
  });
};

/**
 * Parse a label to extract components for sorting
 */
const parseLabelForSorting = (label) => {
  const parts = label.split(' - ');
  
  // Try to identify sport from known sports
  const sports = ['Dodgeball', 'Kickball', 'Pickleball', 'Bowling'];
  const sportPart = parts.find(part => 
    sports.some(sport => part.toLowerCase().includes(sport.toLowerCase())) ||
    /\s+and\s+/.test(part) // Multi-sport
  );

  // Try to identify day
  const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const dayPart = parts.find(part => days.includes(part));

  // Try to identify division
  const divisionPart = parts.find(part => part.includes('Division'));
  const division = divisionPart ? divisionPart.replace(' Division', '') : '';

  // Other identifier is remaining parts
  const otherParts = parts.filter(part => 
    part !== sportPart && part !== dayPart && part !== divisionPart
  );

  return {
    hasSport: !!sportPart,
    sport: sportPart || '',
    day: dayPart || '',
    division: division,
    otherIdentifier: otherParts.join(' - ')
  };
};

/**
 * Extract year from a string
 */
const extractYear = (text) => {
  const currentYear = new Date().getFullYear();
  const yearMatch = text.match(/\b(20\d{2}|\d{2})\b/);
  if (!yearMatch) return null;
  
  let year = parseInt(yearMatch[1]);
  if (year < 100) {
    // Convert 2-digit year to 4-digit
    year += year < 50 ? 2000 : 1900;
  }
  
  return year;
};

/**
 * Extract month from a string and return month index (0-11)
 */
const extractMonth = (text) => {
  const months = [
    'january', 'february', 'march', 'april', 'may', 'june',
    'july', 'august', 'september', 'october', 'november', 'december'
  ];
  
  const lowerText = text.toLowerCase();
  for (let i = 0; i < months.length; i++) {
    if (lowerText.includes(months[i])) {
      return i;
    }
  }
  
  return null;
};
