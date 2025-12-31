/**
 * Google Forms helper functions
 */


/**
 * Get the form and the target form item
 * @returns {{form: Form, formItem: FormItem}}
 */
const getFormAndItem = () => {
  const form = FormApp.getActiveForm();
  if (!form) throw new Error('No active form found.');

  const items = form.getItems().filter(it => it.getTitle && it.getTitle() === QUESTION_TITLE);
  if (!items.length) throw new Error(`No question found with the title "${QUESTION_TITLE}".`);

  const item = items.find(i => i.getType() === FormApp.ItemType.MULTIPLE_CHOICE)
            || items.find(i => i.getType() === FormApp.ItemType.LIST)
            || items[0];

  return { form, formItem: item };
};

/**
 * Get current choices from a form item
 * @param {FormItem} formItem - The form item (Multiple Choice or List)
 * @returns {Choice[]} Array of current choices
 */
const getCurrentChoices = (formItem) => {
  // Google Forms supports two different item types for selectable options:
  // Multiple Choice (radio buttons) and List (dropdown). Each has different APIs for managing choices.
  const mc = (formItem.getType() === FormApp.ItemType.MULTIPLE_CHOICE) ? formItem.asMultipleChoiceItem() : null;
  const dd = (formItem.getType() === FormApp.ItemType.LIST) ? formItem.asListItem() : null;
  if (!mc && !dd) throw new Error(`"${QUESTION_TITLE}" must be Multiple Choice or Dropdown.`);

  return mc ? mc.getChoices() : dd.getChoices();
};

/**
 * Remove sentinel option if it's the only choice
 * @param {Choice[]} choices - Current form choices
 * @returns {Choice[]} Cleaned choices
 */
const removeSearchedSentinelIfNeeded = (choices) => {
  if (choices.length === 1 && choices[0].getValue() === NO_WAITLISTS_SENTINEL) {
    return [];
  }
  return choices;
};
