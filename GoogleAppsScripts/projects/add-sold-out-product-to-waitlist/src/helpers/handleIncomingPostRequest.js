/**
 * Handle incoming POST request and coordinate the waitlist form update process
 * @param {{productUrl?: string, sport?: string, day?: string, division?: string, otherIdentifier?: string}} params
 */
const handleIncomingPostRequest = ({ productUrl, sport, day, division, otherIdentifier }) => {
  // Validate required fields
  validateIncomingData({ productUrl, sport, day, division, otherIdentifier });

  // Create the formatted label
  const label = createFormattedLabel({ sport, day, division, otherIdentifier });

  // Get form and validate it exists
  const { form, formItem } = getFormAndItem();

  // Check for duplicate options
  checkForDuplicateOption(formItem, label);

  // Get current choices and clean if needed
  const currentChoices = getCurrentChoices(formItem);
  const cleanedChoices = removeSearchedSentinelIfNeeded(currentChoices);

  // Create sorted choices with new option
  const allLabels = [...cleanedChoices.map(choice => choice.getValue()), label];
  const sortedLabels = sortWaitlistLabels(allLabels);

  // Update the form with sorted options
  addProductOptionToWaitlistForm(formItem, sortedLabels);

  return { message: `Successfully added "${label}" to waitlist form`, label };
};
