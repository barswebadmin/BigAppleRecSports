/**
 * Validation helper functions
 */

/**
 * Validate incoming POST request data
 * @param {{productUrl?: string, sport?: string, day?: string, division?: string, otherIdentifier?: string}} params
 */
const validateIncomingData = ({ productUrl, sport, day, division, otherIdentifier }) => {
  // Check for required productUrl
  if (!productUrl || typeof productUrl !== 'string' || productUrl.trim() === '') {
    throw new Error('productUrl is required and must be a non-empty string');
  }

  // Check that at least one other field is present and non-empty
  const otherFields = [sport, day, division, otherIdentifier].filter(field =>
    field && typeof field === 'string' && field.trim() !== ''
  );

  if (otherFields.length === 0) {
    throw new Error('At least one of sport, day, division, or otherIdentifier must be provided as a non-empty string');
  }
};

/**
 * Check if an option already exists in the form
 * @param {FormItem} formItem - The form item (Multiple Choice or List)
 * @param {string} label - The label to check for
 */
const checkForDuplicateOption = (formItem, label) => {
  const existingChoices = getCurrentChoices(formItem);
  const existingLabels = existingChoices.map(choice => choice.getValue());

  if (existingLabels.includes(label)) {
    throw new Error(`Option "${label}" already exists in the waitlist form`);
  }
};
