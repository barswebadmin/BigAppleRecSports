/**
 * Insert sorted choices into the form item
 * @param {FormItem} formItem - The form item (Multiple Choice or List)
 * @param {string[]} sortedLabels - Array of sorted label strings
 */
const addProductOptionToWaitlistForm = (formItem, sortedLabels) => {
  // Google Forms supports two different item types for selectable options:
  // Multiple Choice (radio buttons) and List (dropdown). Each has different APIs for managing choices.
  const mc = (formItem.getType() === FormApp.ItemType.MULTIPLE_CHOICE) ? formItem.asMultipleChoiceItem() : null;
  const dd = (formItem.getType() === FormApp.ItemType.LIST) ? formItem.asListItem() : null;
  if (!mc && !dd) throw new Error(`Form item must be Multiple Choice or Dropdown.`);

  // Create new choices from sorted labels
  const newChoices = sortedLabels.map(label =>
    mc ? mc.createChoice(label) : dd.createChoice(label)
  );

  // Update the form with sorted options
  if (mc) {
    mc.setChoices(newChoices);
  } else {
    dd.setChoices(newChoices);
  }
};

/**
 * Reset the waitlist form to default state with only the sentinel option
 */
const returnToDefault = () => {
  const { formItem } = getFormAndItem();

  // Set only the sentinel option
  addProductOptionToWaitlistForm(formItem, [NO_WAITLISTS_SENTINEL]);

  return { message: 'Successfully reset waitlist form to default state', sentinel: NO_WAITLISTS_SENTINEL };
};
