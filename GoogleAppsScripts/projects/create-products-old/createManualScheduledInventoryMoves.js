function createManualScheduledInventoryMoves() {
  const ui = SpreadsheetApp.getUi();
  const apiEndpoint = API_DESTINATION === 'AWS' ? getSecret('AWS_CREATE_PRODUCT_ENDPOINT') : 'https://chubby-grapes-trade.loca.lt/products/create';

  const productUrlRes = ui.prompt("Enter the Product URL", ui.ButtonSet.OK_CANCEL);
  if (productUrlRes.getSelectedButton() !== ui.Button.OK) return;
  const productUrl = productUrlRes.getResponseText().trim();
  const productIdDigitsOnly = productUrl.split("/").pop();
  const productGid = `gid://shopify/Product/${productIdDigitsOnly}`;

  const graphqlEndpoint = getSecret('SHOPIFY_GRAPHQL_URL');

  const graphqlQuery = `
    query GetProductVariants($productId: ID!) {
      product(id: $productId) {
        id
        title
        variants(first: 100) {
          edges {
            node {
              id
              title
            }
          }
        }
      }
    }`;

  const payload = {
    query: graphqlQuery.replace(/\n/g, ' ').replace(/\s+/g, ' '),
    variables: { productId: productGid }
  };

  const shopifyResponse = UrlFetchApp.fetch(graphqlEndpoint, {
    method: 'post',
    contentType: 'application/json',
    headers: {
      'Content-Type': 'application/json',
      'X-Shopify-Access-Token': getSecret('SHOPIFY_TOKEN')
    },
    payload: JSON.stringify(payload)
  });

  Logger.log(`shopifyResponse: ${JSON.stringify(shopifyResponse,null,2)}`)

  const responseData = JSON.parse(shopifyResponse.getContentText());
  Logger.log(`responseData: ${JSON.stringify(responseData,null,2)}`)
  const product = responseData.data.product;
  const variantList = product.variants.edges.map((edge, index) => {
    return `${index + 1}. ${edge.node.title}`;
  }).join("\n");

  const variants = product.variants.edges.map(edge => ({
    title: edge.node.title,
    id: edge.node.id
  }));

  const sourceRes = ui.prompt("Enter the NUMBER of the SOURCE variant from the following list: \n" + variantList, ui.ButtonSet.OK_CANCEL);
  if (sourceRes.getSelectedButton() !== ui.Button.OK) return;
  const sourceIndex = parseInt(sourceRes.getResponseText().trim(), 10) - 1;

  const destRes = ui.prompt("Enter the NUMBER of the DESTINATION variant from the following list: \n" + variantList, ui.ButtonSet.OK_CANCEL);
  if (destRes.getSelectedButton() !== ui.Button.OK) return;
  const destIndex = parseInt(destRes.getResponseText().trim(), 10) - 1;

  if (isNaN(sourceIndex) || isNaN(destIndex) || !variants[sourceIndex] || !variants[destIndex]) {
    ui.alert("❌ Invalid variant number(s). Please ensure they are valid.");
    return;
  }

  const sourceGid = variants[sourceIndex].id;
  const destGid = variants[destIndex].id;
  const sourceTitle = variants[sourceIndex].title;
  const destTitle = variants[destIndex].title;

  const sport = product.title.replace("Big Apple ", "").split(" ").shift();
  const sportSlug = mapSportToAbbreviation(sport);
  const groupName = `move-inventory-between-variants-${sportSlug}`;

  const dateRes = ui.prompt("Enter the date for the schedule (YYYY-MM-DD)", ui.ButtonSet.OK_CANCEL);
  if (dateRes.getSelectedButton() !== ui.Button.OK) return;
  const date = dateRes.getResponseText().trim();

  const timeRes = ui.prompt("Enter the time for the schedule (HH:MM in 24h format)", ui.ButtonSet.OK_CANCEL);
  if (timeRes.getSelectedButton() !== ui.Button.OK) return;
  const time = timeRes.getResponseText().trim();

  // Assume ET input and convert to UTC
  const inputET = `${date} ${time}:00`;
  const etTimestamp = Utilities.parseDate(inputET, "America/New_York", "yyyy-MM-dd HH:mm:ss");
  const newDatetime = etTimestamp.toISOString().split(".")[0]; // UTC ISO format, no ms

  const truncatedSource = sourceTitle.replace(/[^a-zA-Z0-9]/g, '').slice(0, 10);
  const truncatedDest = destTitle.replace(/[^a-zA-Z0-9]/g, '').slice(0, 15);
  const scheduleName = `manual-move-${productIdDigitsOnly}-${sportSlug}-${truncatedSource}-to-${truncatedDest}`;

  const requestPayload = {
    action: "create-scheduled-inventory-movements",
    scheduleName,
    groupName,
    productUrl,
    sourceVariant: {type: "custom", name: sourceTitle, gid: sourceGid},
    destinationVariant: {type: "custom", name: destTitle, gid: destGid},
    newDatetime,
    actionAfterCompletion: "DELETE"
  };

  const options = {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(requestPayload),
    muteHttpExceptions: true
  };

  try {
    const response = UrlFetchApp.fetch(apiEndpoint, options);
    const responseBody = JSON.parse(response.getContentText());
    Logger.log(`✅ Response for ${scheduleName}: ${response.getContentText()}`);

    if (responseBody.message?.includes("successful") || response.getResponseCode() === 201) {
      ui.alert("✅ Manual inventory move scheduled successfully!");
    } else {
      ui.alert("⚠️ Request sent, but check Logs for response details.");
    }
  } catch (err) {
    Logger.log(`❌ Error sending request: ${err}`);
    ui.alert("❌ Failed to send manual inventory move request. Check Logs for details.");
  }
}