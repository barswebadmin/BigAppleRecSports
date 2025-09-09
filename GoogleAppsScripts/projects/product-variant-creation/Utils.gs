const GRAPHQL_URL = "https://09fe59-3.myshopify.com/admin/api/2025-01/graphql.json"
const REST_URL = "https://09fe59-3.myshopify.com/admin/api/2024-04";

const capitalize = str => str[0].toUpperCase() + str.slice(1)

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