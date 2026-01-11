
/**
 * Retrieve a secret from PropertiesService
 * @param {string} key - The secret key
 * @returns {string} The secret value
 */
function getSecret(key) {
  const value = PropertiesService.getScriptProperties().getProperty(key);
  if (!value) {
    throw new Error(`Secret '${key}' not found. Make sure it's set up in PropertiesService.`);
  }
  return value;
}

function showLinkDialog(url) {
  const htmlOutput = HtmlService.createHtmlOutput(`
    <div style="font-family: Arial; padding: 1em;">
      <p>Click below to open the link:</p>
      <a href="${url}" target="_blank">${url}</a>
      <p>Do the following on that page:</p>
      <ul>
        <li>Uncheck "Charge tax on this product"</li>
        <li>Check "Track inventory"</li>
        <li>Uncheck "This is a physical product"</li>
      </ul>
      <p>Once done, go back into the Shopify Actions in the menu bar and run "Create Variants and Schedule Changes"</p>
    </div>
  `)
  .setWidth(300)
  .setHeight(400);

  SpreadsheetApp.getUi().showModalDialog(htmlOutput, 'Open Link');
}



