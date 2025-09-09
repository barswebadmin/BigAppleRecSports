const getSlackMessageText = ({
  requestorName,
  requestorEmail,
  refundOrCredit,
  requestNotes,
  fetchedOrder,
  rawOrderNumber
}) => {
  
  const optionalRequestNotes = requestNotes ? `*Notes provided by requestor*: ${requestNotes} \n` : '';
  const requestType = refundOrCredit === 'refund' ? '💵 Refund back to original form of payment' : `🎟️ Store Credit to use toward a future order`
  const googleSheetReferenceRow = getRowLink(rawOrderNumber, SHEET_ID, SHEET_GID);

  const rowData = getRequestDetailsFromOrderNumber(rawOrderNumber)
  const { requestSubmittedAt } = rowData

  const barsLogoUrl = "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/122824_BARS_Logo_Full-Black.png?v=1741951481";
  const barsLogoBlob = UrlFetchApp
                      .fetch(barsLogoUrl)
                      .getBlob()
                      .setName("barsLogo");

  if (!fetchedOrder.success) {

    MailApp.sendEmail({
      to: requestorEmail,
      replyTo: 'refunds@bigapplerecsports.com',
      subject: `Big Apple Rec Sports - Error with ${capitalize(refundOrCredit)} Request for Order ${rawOrderNumber}`,
      htmlBody: `<p>Hi ${requestorName.first},</p>
        <p>Your request for a ${refundOrCredit} has <b>not</b> been processed successfully. Your provided order number could not be found in our system - remember to please enter only <i>one</i> order number (submit each request separately) and ensure there are only digits. Please confirm you submitted your request using the same email address as is associated with your order - <a href="${SHOPIFY_LOGIN_URL}">Sign In to see your order history</a> to find the correct order number if necessary - and try again.
        <br><br>
        If you believe this is in error, please reach out to <b>refunds@bigapplerecsports.com</b>.</p>
        
        --<br>
        <p>
          Warmly,<br>
          <b>BARS Leadership</b>
        </p>
        <img src="cid:barsLogo" style="width:225px; height:auto;">`,
      inlineImages: { barsLogo: barsLogoBlob }
    })

    return {
      text: `❌ *Refund Request Submitted with Error*`,
      blocks: [
        { type: "divider" },
        {
          type: "section",
          text: {
            type: "mrkdwn",
            text: `❌ *Error with Refund Request - Order Not Found in Shopify* \n\n
            *Request Type*: ${requestType} \n
            *Request Submitted At*: ${formatDateAndTime(requestSubmittedAt)} \n
            📧 *Requested by:* ${requestorName.first} ${requestorName.last} (${requestorEmail})\n
            🔎 *Order Number Provided:* ${rawOrderNumber} - this order cannot be found in Shopify\n
            ${optionalRequestNotes}
            📩 *The requestor has been emailed to please provide correct order info. No action needed at this time.*\n
            🔗 *<${googleSheetReferenceRow}|View Request in Google Sheets>* \n`
          }
        },
        { type: "divider" }
      ]
    };
  }

  const { orderId, orderName, totalAmountPaid, customer, product, orderCreatedAt } = fetchedOrder.data;

  const emailMatches = customer.email === requestorEmail

  const productTitle = product.title
  const earlyVariant = product.variants.find(
    variant => variant.variantName.toLowerCase().includes("trans")
  )
  const originalCost = earlyVariant?.price || totalAmountPaid

  const [seasonStartDate, offDatesStr] = extractSeasonDates(product.descriptionHtml)
  if (!seasonStartDate) {
    Logger.log("❌ Season Start Date could not be extracted from order.");

    const refundAmount = refundOrCredit === "refund" ? formatTwoDecimalPoints(totalAmountPaid * .9) : formatTwoDecimalPoints(totalAmountPaid * .95)
    
    const fallbackMessage = {
      text: `⚠️ *Refund Request Missing Season Info*`,
      blocks: [
        { type: "divider" },
        {
          type: "section",
          text: {
            type: "mrkdwn",
            text: `⚠️ *Refund Request Found in Shopify but Missing Season Info (or Product Is Not a Regular Season)*\n\n
            *Requested by*: ${requestorName.first} ${requestorName.last} (${requestorEmail})\n
            *Order Number Provided*: ${getOrderUrl(orderId, orderName)}\n
            *Product Title*: ${productTitle}\n
            *Total Paid:* $${formatTwoDecimalPoints(totalAmountPaid)}\n
            ⚠️ *Could not parse 'Season Dates' from this order's description (in order to calculate a refund amount).*\n
            Please verify the product and either contact the requestor or process anyway.\n
            🔗 *<${googleSheetReferenceRow}|View Request in Google Sheets>* \n
            *Attn*: ${getSlackGroupId(productTitle)}`
          }
        },
        {
          type: "actions",
          elements: [
            createConfirmButton({ emailMatches, orderId, orderName, requestorName, requestorEmail, refundOrCredit, refundAmount, rawOrderNumber }),
            createRefundDifferentAmountButton({ orderId, orderName, requestorName, requestorEmail, refundOrCredit, refundAmount, rawOrderNumber }),
            createCancelButton({ rawOrderNumber })
          ]
        },
        { type: "divider" }
      ]
    };

    return fallbackMessage;
  }
  
  Logger.log(`variables: ${JSON.stringify(seasonStartDate)}, ${JSON.stringify(offDatesStr)}, ${formatTwoDecimalPoints(totalAmountPaid)}, ${refundOrCredit}`)
  const [refundAmount, refundText] = getRefundDue(seasonStartDate, offDatesStr, formatTwoDecimalPoints(originalCost), refundOrCredit)
  
  Logger.log(`result: ${formatTwoDecimalPoints(refundAmount)}, ${refundText}`)
  Logger.log(`matches? ${emailMatches}`)
  Logger.log(`*Email Associated with Order:* ${customer.email}`)

  if (!emailMatches) {

    MailApp.sendEmail({
      to: requestorEmail,
      replyTo: 'refunds@bigapplerecsports.com',
      subject: `Big Apple Rec Sports - Error with ${capitalize(refundOrCredit)} Request for Order ${rawOrderNumber}`,
      htmlBody: `<p>Hi ${requestorName.first},</p>
        <p>Your request for a ${refundOrCredit} has <b>not</b> been processed successfully. The email associated with the order number did not match the email you provided in the request. Please confirm you submitted your request using the same email address as is associated with your order - <a href="${SHOPIFY_LOGIN_URL}">Sign In to see your order history</a> to find the correct order number - and try again.
        <br><br>
        If you believe this is in error, please reach out to <b>refunds@bigapplerecsports.com</b>.</p>
        
        --<br>
        <p>
          Warmly,<br>
          <b>BARS Leadership</b>
        </p>
        <img src="cid:barsLogo" style="width:225px; height:auto;">`,
      inlineImages: { barsLogo: barsLogoBlob }
    })

    return {
      text: `❌ *Refund Request Submitted with Error*`,
      blocks: [
        { type: "divider" },
        {
          type: "section",
          text: {
            type: "mrkdwn",
            text: `❌ *Error with Refund Request - Email provided did not match order* \n\n
            *Request Type*: ${requestType} \n
            *Request Submitted At*: ${formatDateAndTime(requestSubmittedAt)} \n
            📧 *Requested by:* ${requestorName.first} ${requestorName.last} (${requestorEmail})\n
            *Email Associated with Order:* ${customer.email}\n
            *Order Number:* ${getOrderUrl(orderId, orderName)}\n
            ${optionalRequestNotes}
            📩 *The requestor has been emailed to please provide correct order info. No action needed at this time.*\n
            🔗 *<${googleSheetReferenceRow}|View Request in Google Sheets>* \n`
          }
        },
        { type: "divider" }
      ]
    };
  }

  const headerText = "📌 *New Refund Request!*\n"

  const bodyText = `${headerText}
  *Request Type*: ${requestType}\n
  📧 *Requested by:* ${requestorName.first} ${requestorName.last} (${requestorEmail}) \n
  *Request Submitted At*: ${formatDateAndTime(requestSubmittedAt)} \n
  *Order Number:* ${getOrderUrl(orderId, orderName)}\n
  *Order Created At:* ${formatDateAndTime(orderCreatedAt)} \n
  *Sport/Season/Day:* <${getProductUrl(product)}|${productTitle}>\n
  *Season Start Date*: ${seasonStartDate}\n
  *Total Paid:* $${formatTwoDecimalPoints(totalAmountPaid)}\n
  ${refundText}
  ${optionalRequestNotes}
  🔗 *<${googleSheetReferenceRow}|View Request in Google Sheets>* \n
  *Attn*: ${getSlackGroupId(productTitle)}`;

  Logger.log(`bodyText: ${JSON.stringify(bodyText,null,2)}`)

  const elements = [
    createConfirmButton({ emailMatches, orderId, orderName, requestorName, requestorEmail, refundOrCredit, refundAmount, rawOrderNumber }),
    createRefundDifferentAmountButton({ orderId, orderName, requestorName, requestorEmail, refundOrCredit, refundAmount, rawOrderNumber }),
    createCancelButton({ orderId, orderName, requestorName, requestorEmail, refundOrCredit, rawOrderNumber })
  ].filter(Boolean);

  Logger.log(`elements: ${JSON.stringify(elements,null,2)}`)

  Logger.log(`blocks before returning: ${JSON.stringify({
    text: headerText,
    blocks: [
      { type: "divider" },
      {
        type: "section",
        text: {
          type: "mrkdwn",
          text: bodyText
        }
      },
      { type: "actions", elements },
      { type: "divider" }
    ]
  },null,2)}`)

  return {
    text: headerText,
    blocks: [
      { type: "divider" },
      {
        type: "section",
        text: {
          type: "mrkdwn",
          text: bodyText
        }
      },
      { type: "actions", elements },
      { type: "divider" }
    ]
  };
}

function sendInitialRefundRequestToSlack(fetchedOrder, rawOrderNumber, requestorName, requestorEmail, refundOrCredit, requestNotes) {

  const slackMessage = getSlackMessageText({ 
    requestorName,
    requestorEmail,
    refundOrCredit,
    requestNotes,
    fetchedOrder,
    rawOrderNumber
  })

  Logger.log("🧪 Slack message block payload:", JSON.stringify(slackMessage, null, 2));

  try {
    sendSlackMessage(getSlackRefundsChannel(), slackMessage);
  } catch (error) {
    Logger.log(`❌ Error sending Slack message: ${error.message}`);
    sendSlackMessage(getSlackRefundsChannel(), { text: `⚠️ Slack Error: ${error.message}` });
  }
}