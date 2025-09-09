const restockInventory = ({ requestData, actionId, channelId, threadTs, slackUserName }) => {
  const { inventoryItemId, orderId, refundAmount, orderNumber, approverName } = requestData;
  const requestDetails = getRequestDetailsFromOrderNumber(orderNumber);
  const { requestorFirstName, requestorLastName, refundOrCredit, rawOrderNumber } = requestDetails;
  const sheetLink = getRowLink(rawOrderNumber, SHEET_ID, SHEET_GID);
  const LOCATION_ID = "61802217566";

  let inventoryStatus = "*No inventory was restocked.*";
  let wasSuccessful = false;

  try {
    if (actionId !== "do_not_restock") {
      const mutation = {
        query: `
          mutation inventoryAdjustQuantities($input: InventoryAdjustQuantitiesInput!) {
            inventoryAdjustQuantities(input: $input) {
              userErrors { field message }
              inventoryAdjustmentGroup {
                createdAt
                reason
                changes { name delta }
              }
            }
          }`,
        variables: {
          input: {
            reason: "movement_created",
            name: "available",
            changes: [
              {
                delta: 1,
                inventoryItemId,
                locationId: `gid://shopify/Location/${LOCATION_ID}`
              }
            ]
          }
        }
      };

      const response = fetchShopify(mutation).data;

      if (!response?.inventoryAdjustQuantities || response.inventoryAdjustQuantities.userErrors?.length) {
        const errors = response.inventoryAdjustQuantities.userErrors;
        throw new Error(`Shopify user errors: ${JSON.stringify(errors, null, 2)}`);
      }

      const rawVariantSlug = actionId.replace(/^restock[_\s]?/, '').toLowerCase();
      const isWaitlist = rawVariantSlug.includes("waitlist");
      const variantSlug = isWaitlist ? "waitlist" : rawVariantSlug.replace(/\s+/g, '_');

      inventoryStatus = `✅ *Inventory restocked to ${capitalize(variantSlug)} successfully by ${slackUserName}.*` +
        (isWaitlist ? `\n🔗 *<${WAITLIST_RESPONSES_URL}|Open Waitlist to let someone in>*` : '');
      wasSuccessful = true;
    }

  } catch (error) {
    inventoryStatus = `❌ *Inventory restock failed.*`;
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: `❌ Shopify Inventory Restock Error for Order ${orderNumber}`,
      htmlBody: `<b>Error:</b><br><pre>${error.stack || error.toString()}</pre>`
    });
  }

  const updatedBlock = {
    type: "section",
    text: {
      type: "mrkdwn",
      text: `✅ *Request to provide a $${formatTwoDecimalPoints(refundAmount)} ${refundOrCredit} for Order ${getOrderUrl(orderId, orderNumber)} for ${requestorFirstName} ${requestorLastName} has been processed by ${approverName}.*\n\n${inventoryStatus}\n\n🔗 *<${sheetLink}|View Request in Google Sheets>*`
    }
  };

  updateSlackMessage(getSlackRefundsChannel(), {
    channel: channelId,
    ts: threadTs,
    blocks: [{ type: "divider" }, updatedBlock, { type: "divider" }],
    text: wasSuccessful
      ? `✅ Refund and inventory process complete.`
      : `⚠️ Refund processed, but inventory restock failed.`
  });
};