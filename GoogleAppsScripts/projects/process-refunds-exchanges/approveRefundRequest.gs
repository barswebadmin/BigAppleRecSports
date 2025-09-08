function approveRefundRequest( requestData, channelId, threadTs, slackUserName ) {
  
  const {rawOrderNumber, orderId, refundAmount, oldRefundAmount} = requestData
  const rowData = getRequestDetailsFromOrderNumber(rawOrderNumber)
  
  const { requestSubmittedAt, requestorEmail, refundOrCredit, requestNotes, requestorFirstName,requestorLastName } = rowData

  const formattedOrderNumber = normalizeOrderNumber(rawOrderNumber)

  const sheetLink = getRowLink(rawOrderNumber);

  const fetchedOrder = fetchShopifyOrderDetails({orderName: normalizeOrderNumber(rawOrderNumber), email: null})
  const { product, customer } = fetchedOrder.data

  const { title, productId, descriptionHtml, variants } = product
  const [seasonStartDate, _] = extractSeasonDates(descriptionHtml)

  const safeProductUrl = product?.productId ? getProductUrl(product) : 'https://admin.shopify.com/store/09fe59-3/products';
  const safeOrderUrl = orderId && formattedOrderNumber ? getOrderUrl(orderId, formattedOrderNumber) : '#';

  cancelShopifyOrder(orderId)

  if (refundOrCredit === 'credit') {
    try {
      createShopifyStoreCredit({ formattedOrderNumber, orderId, refundAmount })
    } catch(error) {
        MailApp.sendEmail({
          to: DEBUG_EMAIL,
          subject: "❌ Error creating store credit inside approveRefundRequest()",
          htmlBody: `<pre>${error.stack}</pre>`
        });
    }
  } else {
      createShopifyRefund(orderId, refundAmount)
  }

  const optionalAdjustedRefundText = oldRefundAmount ?
    `Original request was calculated at a refund amount of $${formatTwoDecimalPoints(oldRefundAmount)}, but processed at the amount above.`
    :
    ''
  

  const inventoryOrder = ['veteran', 'early', 'open', 'waitlist'];

  const inventoryList = {
    'veteran': {
      name: "Veteran Registration",
      variantId: variants.find(el => el.variantName.toLowerCase().includes('veteran'))?.variantId,
      inventory: variants.find(el => el.variantName.toLowerCase().includes('veteran'))?.inventory,
      inventoryId: variants.find(el => el.variantName.toLowerCase().includes('veteran'))?.inventoryItemId,
    },
    'early': {
      name: "Early Registration",
      variantId: variants.find(el => el.variantName.toLowerCase().includes('wtnb') || el.variantName.toLowerCase().includes('trans'))?.variantId,
      inventory: variants.find(el => el.variantName.toLowerCase().includes('wtnb') || el.variantName.toLowerCase().includes('trans'))?.inventory,
      inventoryId: variants.find(el => el.variantName.toLowerCase().includes('wtnb') || el.variantName.toLowerCase().includes('trans'))?.inventoryItemId,
    },
    'open': {
      name: "Open Registration",
      variantId: variants.find(el => el.variantName.toLowerCase().includes('open'))?.variantId,
      inventory: variants.find(el => el.variantName.toLowerCase().includes('open'))?.inventory,
      inventoryId: variants.find(el => el.variantName.toLowerCase().includes('open'))?.inventoryItemId,
    },
    'waitlist': {
      name: "Coming Off Waitlist Registration",
      variantId: variants.find(el => el.variantName.toLowerCase().includes('waitlist'))?.variantId,
      inventory: variants.find(el => el.variantName.toLowerCase().includes('waitlist'))?.inventory,
      inventoryId: variants.find(el => el.variantName.toLowerCase().includes('waitlist'))?.inventoryItemId,
    }
  };

  const inventoryText = `📦 *Season Start Date for <${safeProductUrl}|${title}> is ${seasonStartDate}.*\n
  *Current Inventory:*\n` +
    inventoryOrder
      .filter(key => inventoryList[key].inventory !== undefined) // only include available variants
      .map(key => {
        const { name, inventory } = inventoryList[key];
        const text = typeof inventory === "number"
          ? `${inventory} spots available`
          : "Error fetching current inventory";
        return `• *${name}*: ${text}`;
      })
      .join('\n');


  const updatedBlocks = [
    { type: "divider" },
    {
      type: "section",
      text: {
        type: "mrkdwn",
        text: [
          `✅ *Request to provide a $${refundAmount} ${refundOrCredit} for Order ${safeOrderUrl} for ${requestorFirstName} ${requestorLastName} has been processed by ${slackUserName}*`,
          optionalAdjustedRefundText,
          `🔗 *<${sheetLink}|View Request in Google Sheets>*`,
          inventoryText,
          "*Restock Inventory?*"
        ].join('\n')
      }
    },
    {
      type: "actions",
      elements: createRestockInventoryButtons({ orderId, refundAmount, formattedOrderNumber, inventoryList, inventoryOrder, slackUserName })
    },
    { type: "divider" }
  ];

  const updatedPayload = {
    channel: channelId,
    ts: threadTs,
    blocks: updatedBlocks,
    text: `✅ Request has been processed by ${slackUserName}`
  };

  const result = updateSlackMessage(slackRefundsChannel, updatedPayload)

  

  if (result.ok) {
    if (!requestorEmail) {
      throw new Error('Missing requestorEmail — cannot send confirmation email.');
    }
    // const formattedAmount = `$${formatTwoDecimalPoints(refundAmount)}`

    // const storeCreditText = `
    // You should now see a store credit of ${formattedAmount} that you can use toward a future BARS registration.</p>

    // <p>Your store credit does not expire, but it is not transferable, so remember to register next time using this <i>same</i> email address for the credit to apply properly. Please also note that this store credit does not guarantee your registration - you must register successfully during the appropriate registration window next time in order to secure your spot.</p>`
    
    // const refundText = `You should see ${formattedAmount} issued back to your original form of payment within a few days.</p>`

    // const barsLogoUrl = "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/122824_BARS_Logo_Full-Black.png?v=1741951481";
    // const barsLogoBlob = UrlFetchApp
    //                     .fetch(barsLogoUrl)
    //                     .getBlob()
    //                     .setName("barsLogo");
    // MailApp.sendEmail({
    //   to: requestorEmail,
    //   replyTo: 'refunds@bigapplerecsports.com',
    //   subject: `Big Apple Rec Sports - ${capitalize(refundOrCredit)} for Order ${formattedOrderNumber}`,
    //   htmlBody: `<p>Hi ${requestorFirstName},</p>
    //     <p>Your registration has been canceled, and your request for ${refundOrCredit.toLowerCase() === "refund" ? "a refund" : "store credit"} has been processed successfully. ${refundOrCredit === 'refund' ? refundText : storeCreditText}
        
    //     <p>Hope to see you on the field, court, or alley again soon! If you have any questions, please reach out to <a style='color:blue' href='mailto:refunds@bigapplerecsports.com'>refunds@bigapplerecsports.com</a></p>
        
    //     --<br>
    //     <p>
    //       Warmly,<br>
    //       <span style='font-weight:bold;font-size:20px'>Joe Randazzo </span><span style='font-size:14px'>(he/him)</span> <br>
    //       <span style='font-style:italic;font-size:14px'>Vice Commissioner (and good hugger)</span>
    //     </p>
    //     <img src="cid:barsLogo" style="width:225px; height:auto;">`,
    //   inlineImages: { barsLogo: barsLogoBlob }
    // })

    try {
      markOrderAsProcessed(rawOrderNumber);
    } catch (e) {
      const message = [
        `<b>Error marking order as processed</b>`,
        `<pre>${e.message || e.toString()}</pre>`,
        `<b>Stack trace:</b><pre>${e.stack || 'No stack trace available'}</pre>`,
        `<b>Order:</b> ${rawOrderNumber}`
      ].join('<br><br>');

      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: "Refunds - Error marking order as processed",
        htmlBody: message
      });
    }
  }

  if (!result.ok) {
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: "❌ Failed to update Slack message",
      htmlBody: `Slack update failed for request:\n<pre>Payload: ${JSON.stringify(updatedPayload, null, 2)}</pre>\n\nError: ${result.error}`
    });
  }
}

function approveRefundRequestDebugVersion( requestData, channelId, threadTs, slackUserName ) {
  
  const {rawOrderNumber, orderId, refundAmount, oldRefundAmount} = requestData
  const rowData = getRequestDetailsFromOrderNumber(rawOrderNumber)
  
  const { requestSubmittedAt, requestorEmail, refundOrCredit, requestNotes, requestorFirstName,requestorLastName } = rowData

  const formattedOrderNumber = normalizeOrderNumber(rawOrderNumber)

  const sheetLink = getRowLink(rawOrderNumber);

  const fetchedOrder = fetchShopifyOrderDetails({orderName: normalizeOrderNumber(rawOrderNumber), email: null})
  const { product, customer } = fetchedOrder.data

  const { title, productId, descriptionHtml, variants } = product
  const [seasonStartDate, _] = extractSeasonDates(descriptionHtml)

  const safeProductUrl = product?.productId ? getProductUrl(product) : 'https://admin.shopify.com/store/09fe59-3/products';
  const safeOrderUrl = orderId && formattedOrderNumber ? getOrderUrl(orderId, formattedOrderNumber) : '#';

  if (refundOrCredit === 'credit') {
    try {
      createShopifyStoreCreditDebugVersion({ formattedOrderNumber, orderId, refundAmount })
    } catch(error) {
        MailApp.sendEmail({
          to: DEBUG_EMAIL,
          subject: `❌ Error creating store credit inside approveRefundRequest() for order ${formattedOrderNumber}`,
          htmlBody: `<pre>${error.stack}</pre>`
        });
    }
  } else {
      createShopifyRefundDebugVersion(orderId, refundAmount)
  }

  const optionalAdjustedRefundText = oldRefundAmount ?
    `Original request was calculated at a refund amount of $${formatTwoDecimalPoints(oldRefundAmount)}, but processed at the amount above.`
    :
    ''
  

  const inventoryOrder = ['veteran', 'early', 'open', 'waitlist'];

  const inventoryList = {
    'veteran': {
      name: "Veteran Registration",
      variantId: variants.find(el => el.variantName.toLowerCase().includes('veteran'))?.variantId,
      inventory: variants.find(el => el.variantName.toLowerCase().includes('veteran'))?.inventory,
      inventoryId: variants.find(el => el.variantName.toLowerCase().includes('veteran'))?.inventoryItemId,
    },
    'early': {
      name: "Early Registration",
      variantId: variants.find(el => el.variantName.toLowerCase().includes('wtnb') || el.variantName.toLowerCase().includes('trans'))?.variantId,
      inventory: variants.find(el => el.variantName.toLowerCase().includes('wtnb') || el.variantName.toLowerCase().includes('trans'))?.inventory,
      inventoryId: variants.find(el => el.variantName.toLowerCase().includes('wtnb') || el.variantName.toLowerCase().includes('trans'))?.inventoryItemId,
    },
    'open': {
      name: "Open Registration",
      variantId: variants.find(el => el.variantName.toLowerCase().includes('open'))?.variantId,
      inventory: variants.find(el => el.variantName.toLowerCase().includes('open'))?.inventory,
      inventoryId: variants.find(el => el.variantName.toLowerCase().includes('open'))?.inventoryItemId,
    },
    'waitlist': {
      name: "Coming Off Waitlist Registration",
      variantId: variants.find(el => el.variantName.toLowerCase().includes('waitlist'))?.variantId,
      inventory: variants.find(el => el.variantName.toLowerCase().includes('waitlist'))?.inventory,
      inventoryId: variants.find(el => el.variantName.toLowerCase().includes('waitlist'))?.inventoryItemId,
    }
  };

  const inventoryText = `📦 *Season Start Date for <${safeProductUrl}|${title}> is ${seasonStartDate}.*\n
  *Current Inventory:*\n` +
    inventoryOrder
      .filter(key => inventoryList[key].inventory !== undefined) // only include available variants
      .map(key => {
        const { name, inventory } = inventoryList[key];
        const text = typeof inventory === "number"
          ? `${inventory} spots available`
          : "Error fetching current inventory";
        return `• *${name}*: ${text}`;
      })
      .join('\n');


  const updatedBlocks = [
    { type: "divider" },
    {
      type: "section",
      text: {
        type: "mrkdwn",
        text: [
          `✅ *Request to provide a $${refundAmount} ${refundOrCredit} for Order ${safeOrderUrl} for ${requestorFirstName} ${requestorLastName} has been processed by ${slackUserName}*`,
          optionalAdjustedRefundText,
          `🔗 *<${sheetLink}|View Request in Google Sheets>*`,
          inventoryText,
          "*Restock Inventory?*"
        ].join('\n')
      }
    },
    {
      type: "actions",
      elements: createRestockInventoryButtons({ orderId, refundAmount, formattedOrderNumber, inventoryList, inventoryOrder, slackUserName })
    },
    { type: "divider" }
  ];

  const updatedPayload = {
    channel: channelId,
    ts: threadTs,
    blocks: updatedBlocks,
    text: `✅ Request has been processed by ${slackUserName}`
  };

  MailApp.sendEmail({
    to: DEBUG_EMAIL,
    subject: "REFUNDS DEBUG - updatedPayload",
    htmlBody: `attempting to update: \n ${JSON.stringify(updatedPayload,null,2)}`
  });

  
}
