const fetchShopify = (query, variables = {}) => {
  const options = {
    method: "POST",
    contentType: "application/json",
    headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_TOKEN') },
    payload: JSON.stringify({ query, variables })
  };
  const response = UrlFetchApp.fetch(GRAPHQL_URL, options);
  return JSON.parse(response.getContentText());
};

function createProductFromRow(rowObject) {

  const apiEndpoint = 'https://chubby-grapes-trade.loca.lt/api/products';

  const { rowNumber, sport, day, sportSubCategory, division, season, year, socialOrAdvanced, types, newPlayerOrientationDateTime, scoutNightDateTime, openingPartyDate, seasonStartDate, seasonEndDate, offDatesCommaSeparated, rainDate, closingPartyDate, sportStartTime, sportEndTime, alternativeStartTime, alternativeEndTime, location, price, vetRegistrationStartDateTime, earlyRegistrationStartDateTime, openRegistrationStartDateTime, numOfWeeks } = rowObject;

  Logger.log(`productCreate rowObject: \n ${JSON.stringify(rowObject,null,2)}`)

  if (API_DESTINATION === 'local') {
    try {
      const response = UrlFetchApp.fetch(apiEndpoint, {
        method: "post",
        contentType: "application/json",
        payload: JSON.stringify(rowObject),
        muteHttpExceptions: true
      });

      const responseText = response.getContentText();
      Logger.log(`📡 Response from backend: ${responseText}`);

      const status = response.getResponseCode();
      if (status === 200) {
        const parsed = JSON.parse(responseText);
        SpreadsheetApp.getUi().alert(`✅ Product created!\n${parsed.data.productUrl}`);
      } else {
        SpreadsheetApp.getUi().alert(`❌ Error from backend:\n${responseText}`);
      }

    } catch (err) {
      Logger.log("❌ Error during request:", err);
      SpreadsheetApp.getUi().alert(`❌ Request failed: ${err.message}`);
    }
  } else {
    const dayAllCaps = day.toUpperCase();
    const sportAllCaps = sport.toUpperCase();
    const sportSubCategoryAllCaps = sportSubCategory !== 'N/A' ? sportSubCategory.toUpperCase() : '';
    const typesCommaSeparated = types.split(",").join(", ");
    

    const getImageUrl = sport => {
      switch (sport) {
        case "Bowling":
          return "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/BARS_BowlingCrest_2025.png?v=1744213239";
        case "Dodgeball":
          return "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/AF92B4C5-5AA4-4B40-8774-F42937B7C631.png?v=1743883324";
        case "Kickball":
          return "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/Kickball_Open.png?v=1744224266";
        case "Pickleball":
          return "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/BARS_PickleballCrest_2025.png?v=1744213148";
      }
    }

    const getSportEmailAddress = sport => {
      return `<a href='mailto:${sport.toLowerCase()}@bigapplerecsports.com' style='color:blue'>${sport.toLowerCase()}@bigapplerecsports.com</a>`
    }

    const query = JSON.stringify({
      query: `mutation {
        productCreate(
          media: [
            {
              mediaContentType: IMAGE,
              originalSource: "${getImageUrl(sport)}"
            }
          ],
          product: {
            handle: "${year}-${season.toLowerCase()}-${sport.toLowerCase()}-${day.toLowerCase()}-${division.toLowerCase().split('+')[0]}div",
            title: "Big Apple ${sport} - ${day} - ${division} Division - ${season} ${year} (*Registration Not Yet Live - Please scroll down to description for dates*)",
            status: ACTIVE,
            category: "gid://shopify/TaxonomyCategory/sg-4",
            tags: ["${sport}", "${division === 'WTNB+' ? 'WTNB' : division} Division"],
            descriptionHtml: "
              <p></p>
              <h1>${dayAllCaps} ${sportSubCategoryAllCaps} ${sportAllCaps}</h1>
              <p></p>
              <h1>${division} Division ${socialOrAdvanced ? `(${socialOrAdvanced})` : ''}</h1>
              <p><br/></p>

              ${['WTNB+', 'Social'].includes(socialOrAdvanced) ? `
                <p>
                  ${division === 'WTNB+' ? 'Open to <u>women, trans, and non-binary identifying players</u> of all skill levels. ' : ''}
                  ${socialOrAdvanced === 'Social' ? 'While matches will be scored and season standings recorded, this league will stress the social aspect of the sport over competitiveness.' : ''}
                </p>` : ''
              }

              <p><h2><span>LEAGUE DETAILS:</span></h2></p>
              <ul>
                <li>
                  <p><span><strong>Type</strong>: ${division === 'WTNB+' ? 'Created for our Women/Trans/Non-Binary (WTNB+) Community, ' : ''} ${socialOrAdvanced}, ${typesCommaSeparated}</span></p>
                </li>
                ${!!newPlayerOrientationDateTime.raw ? 
                  `<li><p><strong><span>New Player Orientation</span></strong><span>: ${newPlayerOrientationDateTime.formatted ?? newPlayerOrientationDateTime.raw}</span></p></li>` 
                  : 
                  ''
                }
                ${!!scoutNightDateTime.raw ? 
                  `<li><p><strong><span>Scout Night</span></strong><span>: ${scoutNightDateTime.formatted ?? scoutNightDateTime.raw}</span></p></li>` 
                  : 
                  ''
                }
                ${!!openingPartyDate.raw ? 
                  `<li><p><strong><span>Opening Party</span></strong><span>: ${openingPartyDate.formatted ?? openingPartyDate.raw}</span></p></li>` 
                  : 
                  ''
                }
                <li>
                  <p><strong><span>Season Dates</span></strong><span>: ${seasonStartDate.formatted} – ${seasonEndDate.formatted} (${numOfWeeks} weeks${!!offDatesCommaSeparated ? `, off ${offDatesCommaSeparated}` : ''})</span></p>
                  <ul><li>
                    <p><span><strong>Day/Time:</strong> ${day}s ${sportStartTime.formatted} – ${sportEndTime.formatted} ${!!alternativeStartTime.formatted ? `(and sometimes ${alternativeStartTime.formatted} - ${alternativeEndTime.formatted}, varies each week)` : ''}</span></p>
                  </li></ul>
                </li>${!!rainDate.raw ? 
                  `<li><p><strong><span>Rain Date (played if a regular season date gets rained out)</span></strong><span>: ${rainDate.formatted ?? rainDate.raw}</span></p></li>` 
                  : 
                  ''
                }
                ${!!closingPartyDate.raw ? 
                  `<li><p><strong><span>Closing Party${sport.toLowerCase() === 'kickball' ? ' (tentative, depending on rain date)' : ''}</span></strong><span>: ${closingPartyDate.formatted ?? closingPartyDate.raw}</span></p></li>` 
                  : 
                  ''
                }
                <li>
                  <p><span><strong>Location:</strong> ${location}</span></p>
                </li>
                <li>
                  <p><span><strong>Price</strong>: $${price}</span></p>
                </li>
                
              </ul>
              <br/>

              <p><h2><span>REGISTRATION DATES/TIMES:</span></h2></p>
              <ul>
                ${!!vetRegistrationStartDateTime.formatted ? `
                  <li>
                    <p>
                      <span><b>Vet Registration:</b> ${vetRegistrationStartDateTime.formatted ?? vetRegistrationStartDateTime.raw}
                        <br/><small>(Vet status is earned by missing <i>no more</i> than the <b>greater of 25% or 2 weeks</b> of the <i>most recent season</i> of that sport/day/division. Vet status cannot be transferred between players or between different sports/days. All players who are eligible to register during the Veteran Registration period will be notified in advance by email.)</small>
                      </span>
                    </p>
                  </li>` : ''
                }
                <li>
                  <p>
                    <span><b>${division === 'Open' ? 'W' : ''}TNB+ &amp; BIPOC Early Registration</b>: ${earlyRegistrationStartDateTime.formatted}</span>
                  </p>
                </li>
                <li>
                  <p>
                    <span><b>Open Registration:</b> ${openRegistrationStartDateTime.formatted}</span>
                  </p>
                </li>
                <li><b>**Notes**:</b> 
                  <ul>
                    <li>You will only be able to add the product to your cart on the corresponding dates and times above</li>
                    <li>Registration takes place entirely online - please don't show up to the location in person when trying to register (you don't need to!)</li>
                  </ul>
                </li>
              </ul>
              <hr/>

              <p>By participating in any sport or event operated by BARS, players agree to the following:</p>
              <ul>
                <li>
                  <u><a href='https://cdn.shopify.com/s/files/1/0554/7553/5966/files/Waiver.pdf?v=1704060897' target='_blank' style='color:blue'>Waiver</a></u>
                </li>
                <li>
                  <u><a href='https://cdn.shopify.com/s/files/1/0554/7553/5966/files/Terms_of_Participation.pdf?v=1704060897' target='_blank' style='color:blue'>Terms of Participation</a></u>
                </li>
                <li>
                  <u><a href='https://cdn.shopify.com/s/files/1/0554/7553/5966/files/Player_Participation_Policies.pdf?v=1704060897' target='_blank' style='color:blue'>Player Participation Policies</a></u>
                </li>
                <li>
                  <u><a href='https://cdn.shopify.com/s/files/1/0554/7553/5966/files/ADA_Policy_With_No_Signature.docx.pdf?v=1704060738' target='_blank' style='color:blue'>Americans with Disabilities Act (ADA) Policy</a></u>
                </li>
                <li>
                  <u><a href='https://cdn.shopify.com/s/files/1/0554/7553/5966/files/Harassment_Discrimination_and_Bullying_Policy.pdf?v=1702339211' target='_blank' style='color:blue'>Harassment, Bullying, and Discrimination Policy</a></u>
                </li>
              </ul>

              <p>Have questions? Email ${getSportEmailAddress(sport)}</p>
            "
          }) {
            product {
              id
              title
            }
            userErrors {
              field
              message
            }
          }
        }`
    });

    const response = UrlFetchApp.fetch(GRAPHQL_URL, {
      method: "post",
      contentType: "application/json",
      headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_TOKEN') },
      payload: query
    });

    const responseData = JSON.parse(response.getContentText());
    Logger.log("🧪 Full Shopify Response: " + JSON.stringify(responseData, null, 2));
    const productGid = responseData.data?.productCreate?.product?.id
    const productIdDigitsOnly = productGid?.split("/")?.pop();
    const productUrl = productIdDigitsOnly ? `https://admin.shopify.com/store/09fe59-3/products/${productIdDigitsOnly}` : '';
    
    Utilities.sleep(1000);

    function getVariantId(productGid) {
      const query = `
        query {
          product(id: "${productGid}") {
            variants(first: 1) { nodes { id } }
          }
        }`;

      const response = fetchShopify(query);

      const variantId = response.data?.product?.variants?.nodes[0]?.id || null;
      if (!variantId) Logger.log("❌ No variant found in Shopify response:", response);
      return variantId;
    }

    // Step 3: Update Variant (Tax, Inventory, Shipping)
    function updateVariantSettings(variantId) {
      const mutation = {
        query: `
          mutation {
            productVariantUpdate(input: {
              id: "${variantId}",
              taxable: false,
              requiresShipping: false
            }) {
              userErrors { field message }
            }
          }`
      };

      const response = UrlFetchApp.fetch(`${REST_URL}/graphql.json`, {
        method: "POST",
        contentType: "application/json",
        headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_TOKEN') },
        payload: JSON.stringify(mutation)
      });

      const data = JSON.parse(response.getContentText());
      Logger.log("🔧 Variant Update: " + JSON.stringify(data, null, 2));
    }

    function enableInventoryTracking(variantIdDigitsOnly) {
      const url = `${REST_URL}/variants/${variantIdDigitsOnly}.json`;
      const payload = {
        variant: {
          id: parseInt(variantIdDigitsOnly, 10),
          inventory_management: "shopify"
        }
      };

      const response = UrlFetchApp.fetch(url, {
        method: "PUT",
        contentType: "application/json",
        headers: {
          "X-Shopify-Access-Token": getSecret('SHOPIFY_TOKEN')
        },
        payload: JSON.stringify(payload)
      });

      const data = JSON.parse(response.getContentText());
      Logger.log("📦 Inventory Management Set: " + JSON.stringify(data, null, 2));
    }

    // updateVariantBulk(productIdDigitsOnly, variantId);
    // updateVariant(variantId);

    
    
    function scheduleProductPublication(productIdDigitsOnly, rawRegistrationStartDateTime) {

      const formattedPublishDate = new Date(rawRegistrationStartDateTime).toISOString();

      const query = JSON.stringify({
        query: `mutation productPublish($input: ProductPublishInput!) {
          productPublish(input: $input) {
            product {
              id
            }
            userErrors {
              field
              message
            }
          }
        }`,
        variables: {
          input: {
            id: `gid://shopify/Product/${productIdDigitsOnly}`,
            productPublications: [{
              publicationId: 'gid://shopify/Publication/79253667934',
              publishDate: new Date().toISOString(),
              channelHandle: "online-store"
            }]
          }
        }
      });

      const options = {
        method: "POST",
        contentType: "application/json",
        headers: {
          "X-Shopify-Access-Token": getSecret('SHOPIFY_TOKEN')
        },
        payload: query
      };

      try {
        const response = UrlFetchApp.fetch('https://09fe59-3.myshopify.com/admin/api/2025-01/graphql.json', options);
        const responseData = JSON.parse(response.getContentText());
        Logger.log(`***publish function response***: ${JSON.stringify(responseData,null,2)}`)

        const pubErrors = responseData.data?.productPublish?.userErrors || [];
        if (pubErrors.length) {
          Logger.log(`❌ productPublish errors: ${JSON.stringify(pubErrors)}`);
        }
      } catch (error) {
        Logger.log(`❌ Error in scheduling publication: ${error.message}`);
      }
    }

    if (!!productUrl) {
      const productUrlIndex = sheetHeaders.indexOf('Product URL') + 1
      sheet.getRange(rowNumber, productUrlIndex).setFormula(`=HYPERLINK("${productUrl}", "${productUrl}")`);

      const variantId = getVariantId(productGid);
      
      if (variantId) {
        const variantIdDigitsOnly = variantId.split("/").pop();
        updateVariantSettings(variantId);
        enableInventoryTracking(variantIdDigitsOnly);
        const firstRegistrationStartDateTime = vetRegistrationStartDateTime.raw && vetRegistrationStartDateTime < earlyRegistrationStartDateTime ? vetRegistrationStartDateTime.raw : earlyRegistrationStartDateTime.raw  
        scheduleProductPublication(productIdDigitsOnly, firstRegistrationStartDateTime);
        createVariantsFromRow(rowObject)
        
        // showLinkDialog(productUrl)
      } else {
        Logger.log("❌ No variant found.");
      }

    } else {
      const userErrors = responseData.data?.productCreate?.userErrors || [];
      const errorMessages = userErrors.map(err => `${err.field}: ${err.message}`).join("\n");

      Logger.log("❌ Product creation failed. User errors: " + JSON.stringify(userErrors, null, 2));

      ui.alert(
        "❌ Product was not created properly. Please check the following errors:\n\n" +
        (errorMessages || "No detailed error message returned from Shopify.")
      );
    }
  }
}