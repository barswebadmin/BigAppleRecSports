/**
 * Label creation and formatting functions
 */

/**
 * Create formatted label from components
 * @param {{sport?: string, day?: string, division?: string, otherIdentifier?: string}} params
 * @returns {string} Formatted label
 */
export const createFormattedLabel = ({ sport, day, division, otherIdentifier }) => {
  const parts = [];

  if (sport) parts.push(sport);
  if (day) parts.push(day);
  if (division) parts.push(`${division} Division`);
  if (otherIdentifier) parts.push(otherIdentifier);

  return parts.join(' - ');
};
