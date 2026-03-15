/**
 * Core Shopify product creation logic
 * Sends directly to Shopify GraphQL API (no backend intermediary)
 *
 * @fileoverview Shopify API integration for product and variant creation
 * @requires ../../shared-utilities/secretsUtils.gs
 * @requires ../../shared-utilities/ShopifyUtils.gs
 */

import { getSecret } from '../../shared-utilities/secretsUtils.js';
import { formatDateLong, formatDateTimeLong } from '../../helpers/formatValidators.js';

/**
 * Normalize a value to {raw, formatted} shape for use in the description template.
 * Accepts Date objects, strings, or already-shaped {raw, formatted} objects.
 */
function toDisplayObj(value, isDateTime = false) {
  if (!value) return null;
  // Already shaped
  if (value && typeof value === 'object' && !Array.isArray(value) && !(value instanceof Date) && 'raw' in value) {
    return value;
  }
  const raw = value instanceof Date ? value.toISOString() : String(value);
  const formatted = value instanceof Date
    ? (isDateTime ? formatDateTimeLong(value) : formatDateLong(value))
    : String(value);
  return { raw, formatted };
}

/**
 * Helper function to format team assignment for display
 */
export function formatTeamAssignment(assignment) {
  if (!assignment?.formatted) return '';
  switch(assignment.formatted) {
    case 'randomized': return 'Randomized Teams';
    case 'randomizedWithBuddy': return 'Sign-up with a buddy (randomized otherwise)';
    case 'draft': return 'Draft';
    case 'ladder': return 'Ladder';
    case 'none': return '';
    default: return assignment.formatted;
  }
}

/**
 * Get sport-specific image URL
 */
export function getImageUrl(sport) {
  return "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/ComingSoon.png?v=1773021037";
}

/**
 * Main function to create Shopify product from parsed data
 * Sends directly to Shopify GraphQL API
 */
export function createProductFromRowData(rowObject) {
  const { 
    sportName, dayOfPlay, division, season, year, location, price,
    seasonStartDate, seasonEndDate, totalWeeks,
    leagueStartTime, leagueEndTime, alternativeStartTime, alternativeEndTime,
    levelOfPlay, teamAssignment, dodgeballBallType, gameDuration,
    newPlayerOrientationDateTime, scoutNightDateTime,
    openingPartyDate, rainDate, closingPartyDate, offDates, offDatesCommaSeparated,
    vetRegistrationStartDateTime, tnbWtnbRegistrationStartDateTime, openRegistrationStartDateTime,
    leagueContactEmail, vetStatusDeterminedBy
  } = rowObject;

  Logger.log(`Creating product from row: \n ${JSON.stringify(rowObject, null, 2)}`);

  // Normalize all date/time fields to {raw, formatted} objects for use in the template
  const seasonStartDateObj = toDisplayObj(seasonStartDate, false);
  const seasonEndDateObj = toDisplayObj(seasonEndDate, false);
  const leagueStartTimeObj = toDisplayObj(leagueStartTime, false);
  const leagueEndTimeObj = toDisplayObj(leagueEndTime, false);
  const alternativeStartTimeObj = toDisplayObj(alternativeStartTime, false);
  const alternativeEndTimeObj = toDisplayObj(alternativeEndTime, false);
  const newPlayerOrientationDateTimeObj = toDisplayObj(newPlayerOrientationDateTime, true);
  const scoutNightDateTimeObj = toDisplayObj(scoutNightDateTime, true);
  const openingPartyDateObj = toDisplayObj(openingPartyDate, false);
  const rainDateObj = toDisplayObj(rainDate, false);
  const closingPartyDateObj = toDisplayObj(closingPartyDate, false);
  const vetRegistrationObj = toDisplayObj(vetRegistrationStartDateTime, true);
  const tnbWtnbRegistrationObj = toDisplayObj(tnbWtnbRegistrationStartDateTime, true);
  const openRegistrationObj = toDisplayObj(openRegistrationStartDateTime, true);

  // location is already {raw, formatted} from parseLocation
  const locationFormatted = (location && typeof location === 'object') ? (location.formatted || location.raw) : (location || '');

  // offDates is an array of Date objects; build comma-separated display string
  const offDatesDisplay = (() => {
    const formatNoYear = (d) => {
      const full = formatDateLong(d); // "May 24, 2026"
      return full.replace(/,\s*\d{4}$/, ''); // → "May 24"
    };
    if (offDatesCommaSeparated) {
      // strip year from each comma-separated date string
      return offDatesCommaSeparated.split(',').map(s => s.trim().replace(/,?\s*\d{4}$/, '')).join(', ');
    }
    if (Array.isArray(offDates) && offDates.length > 0) {
      return offDates.map(formatNoYear).filter(Boolean).join(', ');
    }
    return '';
  })();

  const dayAllCaps = dayOfPlay.toUpperCase();
  const sportAllCaps = sportName.toUpperCase();
  const dodgeballBallTypeAllCaps = dodgeballBallType ? dodgeballBallType.toUpperCase() : '';
  
  // Build the product title with season start date in M/D format
  const regStartsDate = seasonStartDate 
    ? `${seasonStartDate.getMonth() + 1}/${seasonStartDate.getDate()}`
    : '';
  const productTitle = `[REG STARTS ${regStartsDate}] Big Apple ${sportName} - ${dayOfPlay} - ${division} Division - ${season} ${year}`;
  
  // Build the descriptionHtml
  const descriptionHtml = `
    <p></p>
    <h1>${dayAllCaps} ${dodgeballBallTypeAllCaps} ${sportAllCaps}</h1>
    <p></p>
    <h1>${division} Division ${levelOfPlay?.formatted ? `(${levelOfPlay.formatted})` : ''}</h1>
    <p><br/></p>

    ${division === 'WTNB+' ? `<p>Open to <u>women, trans, and nonbinary identifying players</u> of all skill levels.</p>` : ''}

    <p><h2><span>LEAGUE DETAILS:</span></h2></p>
    <ul>
      ${levelOfPlay?.formatted ? `<li><p><span><strong>Level of Play</strong>: ${levelOfPlay.formatted}</span></p>${levelOfPlay.formatted === 'Social' ? `<ul><li><i>*While matches will be scored and season standings recorded, this league will stress the social aspect of the sport over competitiveness.</i></li></ul>` : ''}</li>` : ''}
      ${formatTeamAssignment(teamAssignment) ? `<li><p><span><strong>Team Assignment</strong>: ${formatTeamAssignment(teamAssignment)}</span></p></li>` : ''}
      ${division === 'WTNB+' ? `<li><p><span><strong>Type</strong>: Created for our Women/Trans/Nonbinary (WTNB+) Community</span></p></li>` : ''}
      ${newPlayerOrientationDateTimeObj?.raw ? 
        `<li><p><strong><span>New Player Orientation</span></strong><span>: ${newPlayerOrientationDateTimeObj.formatted ?? newPlayerOrientationDateTimeObj.raw}</span></p></li>` 
        : 
        ''
      }
      ${scoutNightDateTimeObj?.raw ? 
        `<li><p><strong><span>Scout Night</span></strong><span>: ${scoutNightDateTimeObj.formatted ?? scoutNightDateTimeObj.raw}</span></p></li>` 
        : 
        ''
      }
      ${openingPartyDateObj?.raw ? 
        `<li><p><strong><span>Opening Party</span></strong><span>: ${openingPartyDateObj.formatted ?? openingPartyDateObj.raw}</span></p></li>` 
        : 
        ''
      }
      <li>
        <p><strong><span>Season Dates</span></strong><span>: ${seasonStartDateObj?.formatted ?? ''} – ${seasonEndDateObj?.formatted ?? ''} (${totalWeeks != null ? `${totalWeeks} weeks` : ''}${offDatesDisplay ? `, off ${offDatesDisplay}` : ''})</span></p>
        <ul>
          <li>
            <p><span><strong>Day/Time:</strong> ${dayOfPlay}s ${leagueStartTimeObj?.formatted ?? ''} – ${leagueEndTimeObj?.formatted ?? ''}${gameDuration ? ` (1 game per night, ${gameDuration} per game)` : ''} ${alternativeStartTimeObj?.formatted ? `(and sometimes ${alternativeStartTimeObj.formatted} - ${alternativeEndTimeObj?.formatted ?? ''}, varies each week)` : ''}</span></p>
            ${levelOfPlay?.formatted === 'Social' ? `` : ''}
          </li>
        </ul>
      </li>
      ${closingPartyDateObj?.raw ? 
        `<li><p><strong><span>Closing Party${rainDateObj?.raw ? ' (tentative, pending Rain Date)' : ''}</span></strong><span>: ${closingPartyDateObj.formatted ?? closingPartyDateObj.raw}</span></p></li>` 
        : 
        ''
      }
      ${rainDateObj?.raw ? 
        `<li><p><strong><span>Rain Date</span></strong><span>: ${rainDateObj.formatted ?? rainDateObj.raw}</span></p></li>` 
        : 
        ''
      }
      <li>
        <p><span><strong>Location:</strong> ${locationFormatted}</span></p>
      </li>
      <li>
        <p><span><strong>Price</strong>: $${price != null ? price : ''}</span></p>
      </li>
      
    </ul>
    <br/>

    <p><h2><span>REGISTRATION DATES/TIMES:</span></h2></p>
    <ul>
      ${(vetRegistrationObj?.raw && vetRegistrationObj?.formatted && !vetRegistrationObj.formatted.includes('Invalid Date')) ? `
        <li>
          <p>
            <span><b>Vet Registration:</b> ${vetRegistrationObj.formatted}
              <br/><small>(Vet status is earned by missing <i>no more</i> than the <b>greater of 25% or 2 weeks</b> of the <b>${vetStatusDeterminedBy || 'most recent season'}</b> of that sport/day/division. Vet status cannot be transferred between players or between different sports/days. All players who are eligible to register during the Veteran Registration period will be notified in advance by email.)</small>
            </span>
          </p>
        </li>` : ''
      }
      ${tnbWtnbRegistrationObj?.formatted ? `<li><p><span><b>${division === 'Open' ? 'W' : ''}TNB+ &amp; BIPOC Early Registration</b>: ${tnbWtnbRegistrationObj.formatted}</span></p></li>` : ''}
      <li>
        <p>
          <span><b>Open Registration:</b> ${openRegistrationObj?.formatted ?? ''}</span>
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

    <p>Have questions? Email <a href='mailto:${leagueContactEmail}' style='color:blue'>${leagueContactEmail}</a></p>
  `;
  
  const variantDefs = [
    ...(vetRegistrationStartDateTime ? [{ name: "Veteran Registration" }] : []),
    { name: "Early Registration" },
    { name: "Open Registration" },
    { name: "Waitlist Registration" },
  ];

  const query = JSON.stringify({
    query: `mutation productCreate($input: ProductCreateInput!, $media: [CreateMediaInput!]) {
      productCreate(product: $input, media: $media) {
        product {
          id
          title
        }
        userErrors {
          field
          message
        }
      }
    }`,
    variables: {
      media: [
        {
          mediaContentType: "IMAGE",
          originalSource: getImageUrl(sportName)
        }
      ],
      input: {
        handle: `${year}-${season.toLowerCase()}-${sportName.toLowerCase()}-${dayOfPlay.toLowerCase()}-${division.toLowerCase().split('+')[0]}div`,
        title: productTitle,
        status: "ACTIVE",
        category: "gid://shopify/TaxonomyCategory/sg-4",
        tags: [
          sportName.toLowerCase(),
          division === 'WTNB+' ? 'wtnb-division' : 'open-division'
        ],
        descriptionHtml: descriptionHtml,
        productOptions: [
          { name: "Registration Type", values: variantDefs.map(v => ({ name: v.name })) }
        ]
      }
    }
  });

  Logger.log("📋 GraphQL Query to be sent:");
  Logger.log(query);

  let response;
  try {
    response = UrlFetchApp.fetch(getSecret('SHOPIFY_GRAPHQL_URL'), {
      method: "post",
      contentType: "application/json",
      headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_ACCESS_TOKEN') },
      payload: query,
      muteHttpExceptions: true
    });
  } catch (fetchErr) {
    const msg = `Network error calling Shopify: ${fetchErr.message}`;
    Logger.log(`❌ ${msg}`);
    SpreadsheetApp.getUi().alert(`❌ ${msg}`);
    return { success: false, error: msg };
  }

  const responseCode = response.getResponseCode();
  const responseText = response.getContentText();

  if (responseCode !== 200) {
    Logger.log(`❌ Shopify returned HTTP ${responseCode}. Body: ${responseText}`);
    SpreadsheetApp.getUi().alert(`❌ Shopify returned HTTP ${responseCode}. Check logs for details.`);
    return { success: false, error: `HTTP ${responseCode}` };
  }

  let responseData;
  try {
    responseData = JSON.parse(responseText);
  } catch (_parseErr) {
    Logger.log(`❌ Failed to parse Shopify response: ${responseText}`);
    SpreadsheetApp.getUi().alert("❌ Could not parse Shopify response. Check logs.");
    return { success: false, error: "Invalid JSON response" };
  }

  Logger.log(`🧪 Full Shopify productCreate response: ${JSON.stringify(responseData, null, 2)}`);

  // Top-level errors (auth failures, type mismatches, malformed queries)
  if (responseData.errors?.length) {
    const errorMessages = responseData.errors.map(e => e.message || JSON.stringify(e)).join("\n");
    Logger.log(`❌ Shopify top-level errors: ${JSON.stringify(responseData.errors, null, 2)}`);
    SpreadsheetApp.getUi().alert(`❌ Shopify API error:\n\n${errorMessages}`);
    return { success: false, error: errorMessages };
  }

  const userErrors = responseData.data?.productCreate?.userErrors || [];
  if (userErrors.length) {
    const errorMessages = userErrors.map(err => `${err.field}: ${err.message}`).join("\n");
    Logger.log(`❌ productCreate userErrors: ${JSON.stringify(userErrors, null, 2)}`);
    SpreadsheetApp.getUi().alert(`❌ Product creation failed:\n\n${errorMessages}`);
    return { success: false, error: errorMessages };
  }

  const productGid = responseData.data?.productCreate?.product?.id;
  const productIdDigitsOnly = productGid?.split("/")?.pop();
  const productUrl = productIdDigitsOnly
    ? `https://admin.shopify.com/store/09fe59-3/products/${productIdDigitsOnly}`
    : '';

  if (!productUrl) {
    const msg = "Shopify returned success but no product ID in response. Product may not have been created — check Shopify admin.";
    Logger.log(`❌ ${msg} Full response: ${JSON.stringify(responseData, null, 2)}`);
    SpreadsheetApp.getUi().alert(`❌ ${msg}`);
    return { success: false, error: msg };
  }

  // Shopify auto-creates the first variant when productOptions are set.
  // Query the product to get that existing variant's ID, then update it
  // and bulk-create the remaining variants.
  const fetchVariantsQuery = JSON.stringify({
    query: `query getProductVariants($id: ID!) {
      product(id: $id) {
        variants(first: 10) {
          nodes { id title inventoryItem { id } }
        }
      }
    }`,
    variables: { id: productGid }
  });

  let fetchVariantsResponse;
  try {
    fetchVariantsResponse = UrlFetchApp.fetch(getSecret('SHOPIFY_GRAPHQL_URL'), {
      method: "post",
      contentType: "application/json",
      headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_ACCESS_TOKEN') },
      payload: fetchVariantsQuery,
      muteHttpExceptions: true
    });
  } catch (fetchErr) {
    Logger.log(`⚠️ Could not fetch existing variants: ${fetchErr.message}`);
    SpreadsheetApp.getUi().alert(`⚠️ Product created but could not fetch variants.\n${productUrl}`);
    return { success: true, data: { productUrl, productId: productIdDigitsOnly } };
  }

  let fetchVariantsData;
  try {
    fetchVariantsData = JSON.parse(fetchVariantsResponse.getContentText());
  } catch (_e) {
    Logger.log(`⚠️ Could not parse variant fetch response`);
    return { success: true, data: { productUrl, productId: productIdDigitsOnly } };
  }

  const existingVariants = fetchVariantsData.data?.product?.variants?.nodes || [];
  Logger.log(`🔍 Existing variants after productCreate: ${JSON.stringify(existingVariants)}`);

  // The auto-created variant is the first one — update it in place
  const autoVariant = existingVariants[0];
  if (!autoVariant) {
    Logger.log(`⚠️ No existing variants found on new product`);
    SpreadsheetApp.getUi().alert(`⚠️ Product created but no variants found.\n${productUrl}`);
    return { success: true, data: { productUrl, productId: productIdDigitsOnly } };
  }

  // Update the auto-created variant (price, tax, shipping)
  const updateQuery = JSON.stringify({
    query: `mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
      productVariantsBulkUpdate(productId: $productId, variants: $variants) {
        productVariants { id title inventoryItem { id } }
        userErrors { field message }
      }
    }`,
    variables: {
      productId: productGid,
      variants: [{
        id: autoVariant.id,
        price: String(price),
        compareAtPrice: String(price),
        taxable: false,
        inventoryItem: { tracked: true, requiresShipping: false }
      }]
    }
  });

  try {
    const updateResp = UrlFetchApp.fetch(getSecret('SHOPIFY_GRAPHQL_URL'), {
      method: "post",
      contentType: "application/json",
      headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_ACCESS_TOKEN') },
      payload: updateQuery,
      muteHttpExceptions: true
    });
    const updateData = JSON.parse(updateResp.getContentText());
    Logger.log(`🔧 Variant update response: ${JSON.stringify(updateData)}`);
    // Merge inventoryItem.id back so the post-creation loop can use it
    const updatedVariant = updateData.data?.productVariantsBulkUpdate?.productVariants?.[0];
    if (updatedVariant?.inventoryItem?.id) {
      existingVariants[0] = { ...existingVariants[0], inventoryItem: updatedVariant.inventoryItem };
    }
  } catch (e) {
    Logger.log(`⚠️ Variant update error: ${e.message}`);
  }

  // Build variants — skip the first one (already exists as auto-created)
  const remainingVariantDefs = variantDefs.slice(1);

  let createdVariants = existingVariants; // start with what we have

  if (remainingVariantDefs.length > 0) {
    const variantQuery = JSON.stringify({
      query: `mutation productVariantsBulkCreate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
        productVariantsBulkCreate(productId: $productId, variants: $variants) {
          productVariants { id title inventoryItem { id } }
          userErrors { field message }
        }
      }`,
      variables: {
        productId: productGid,
        variants: remainingVariantDefs.map(v => ({
          price: String(price),
          compareAtPrice: String(price),
          taxable: false,
          inventoryItem: { tracked: true, requiresShipping: false },
          optionValues: [{ optionName: "Registration Type", name: v.name }]
        }))
      }
    });

    let variantResponse;
    try {
      variantResponse = UrlFetchApp.fetch(getSecret('SHOPIFY_GRAPHQL_URL'), {
        method: "post",
        contentType: "application/json",
        headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_ACCESS_TOKEN') },
        payload: variantQuery,
        muteHttpExceptions: true
      });
    } catch (fetchErr) {
      const msg = `Product created but variant creation network error: ${fetchErr.message}`;
      Logger.log(`⚠️ ${msg}`);
      SpreadsheetApp.getUi().alert(`⚠️ ${msg}\n${productUrl}`);
      return { success: true, data: { productUrl, productId: productIdDigitsOnly } };
    }

    let variantData;
    try {
      variantData = JSON.parse(variantResponse.getContentText());
    } catch (_e) {
      Logger.log(`⚠️ Could not parse variant response: ${variantResponse.getContentText()}`);
      return { success: true, data: { productUrl, productId: productIdDigitsOnly } };
    }

    Logger.log(`🧪 productVariantsBulkCreate response: ${JSON.stringify(variantData, null, 2)}`);

    if (variantData.errors?.length) {
      const msg = variantData.errors.map(e => e.message || JSON.stringify(e)).join("\n");
      Logger.log(`⚠️ productVariantsBulkCreate top-level errors: ${msg}`);
      SpreadsheetApp.getUi().alert(`⚠️ Product created but variant API error:\n${msg}\n${productUrl}`);
      return { success: true, data: { productUrl, productId: productIdDigitsOnly } };
    }

    const variantErrors = variantData.data?.productVariantsBulkCreate?.userErrors || [];
    if (variantErrors.length) {
      const msg = variantErrors.map(e => `${e.field}: ${e.message}`).join("\n");
      Logger.log(`⚠️ Variant creation errors: ${msg}`);
      SpreadsheetApp.getUi().alert(`⚠️ Product created but variant had errors:\n${msg}\n${productUrl}`);
      return { success: true, data: { productUrl, productId: productIdDigitsOnly } };
    }

    const newVariants = variantData.data?.productVariantsBulkCreate?.productVariants || [];
    createdVariants = [...existingVariants, ...newVariants];
  }

  // Force-set taxable=false, requiresShipping=false, tracked=true on every variant.
  // These must be applied via dedicated mutations — bulk input fields are not reliable.
  for (const variant of createdVariants) {
    const variantId = variant.id;
    const invItemId = variant.inventoryItem?.id;

    // 1. taxable=false via productVariantUpdate (CRITICAL — must not be missed)
    try {
      const taxResp = UrlFetchApp.fetch(getSecret('SHOPIFY_GRAPHQL_URL'), {
        method: "post",
        contentType: "application/json",
        headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_ACCESS_TOKEN') },
        payload: JSON.stringify({
          query: `mutation productVariantUpdate($input: ProductVariantInput!) {
            productVariantUpdate(input: $input) {
              productVariant { id taxable }
              userErrors { field message }
            }
          }`,
          variables: { input: { id: variantId, taxable: false } }
        }),
        muteHttpExceptions: true
      });
      const taxData = JSON.parse(taxResp.getContentText());
      Logger.log(`💰 taxable update ${variantId}: ${JSON.stringify(taxData.data?.productVariantUpdate?.productVariant)}`);
      const taxErrors = taxData.data?.productVariantUpdate?.userErrors || [];
      if (taxErrors.length) Logger.log(`⚠️ taxable update errors: ${JSON.stringify(taxErrors)}`);
    } catch (e) {
      Logger.log(`⚠️ productVariantUpdate error for ${variantId}: ${e.message}`);
    }

    // 2. requiresShipping=false + tracked=true via inventoryItemUpdate
    if (invItemId) {
      try {
        const invResp = UrlFetchApp.fetch(getSecret('SHOPIFY_GRAPHQL_URL'), {
          method: "post",
          contentType: "application/json",
          headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_ACCESS_TOKEN') },
          payload: JSON.stringify({
            query: `mutation inventoryItemUpdate($id: ID!, $input: InventoryItemInput!) {
              inventoryItemUpdate(id: $id, input: $input) {
                inventoryItem { id tracked requiresShipping }
                userErrors { field message }
              }
            }`,
            variables: { id: invItemId, input: { tracked: true, requiresShipping: false } }
          }),
          muteHttpExceptions: true
        });
        const invData = JSON.parse(invResp.getContentText());
        Logger.log(`📦 inventoryItemUpdate ${invItemId}: ${JSON.stringify(invData.data?.inventoryItemUpdate?.inventoryItem)}`);
        const invErrors = invData.data?.inventoryItemUpdate?.userErrors || [];
        if (invErrors.length) Logger.log(`⚠️ inventoryItem update errors: ${JSON.stringify(invErrors)}`);
      } catch (e) {
        Logger.log(`⚠️ inventoryItemUpdate error for ${invItemId}: ${e.message}`);
      }
    }
  }

  const findVariant = (name) => createdVariants.find(v => v.title === name)?.id || null;

  const veteranVariantGid  = vetRegistrationStartDateTime ? findVariant("Veteran Registration") : null;
  const earlyVariantGid    = findVariant("Early Registration");
  const openVariantGid     = findVariant("Open Registration");
  const waitlistVariantGid = findVariant("Waitlist Registration");

  if (!openVariantGid) {
    Logger.log(`⚠️ Product created but Open Registration variant not found. Variants: ${JSON.stringify(createdVariants)}`);
    SpreadsheetApp.getUi().alert(`⚠️ Product created but variant not found in response.\n${productUrl}`);
    return { success: true, data: { productUrl, productId: productIdDigitsOnly } };
  }

  Logger.log(`✅ Product created: ${productUrl} | variants: ${JSON.stringify(createdVariants.map(v => v.title))}`);

  // Publish to Online Store immediately
  try {
    const publishResp = UrlFetchApp.fetch(getSecret('SHOPIFY_GRAPHQL_URL'), {
      method: "post",
      contentType: "application/json",
      headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_ACCESS_TOKEN') },
      payload: JSON.stringify({
        query: `mutation publishablePublish($id: ID!, $input: [PublicationInput!]!) {
          publishablePublish(id: $id, input: $input) {
            publishable { availablePublicationsCount { count } }
            userErrors { field message }
          }
        }`,
        variables: {
          id: productGid,
          input: [{ publicationId: "gid://shopify/Publication/79253667934" }]
        }
      }),
      muteHttpExceptions: true
    });
    const publishData = JSON.parse(publishResp.getContentText());
    const publishErrors = publishData.data?.publishablePublish?.userErrors || [];
    if (publishErrors.length) {
      Logger.log(`⚠️ publishablePublish errors: ${JSON.stringify(publishErrors)}`);
    } else {
      Logger.log(`📢 Product published to Online Store: ${productGid}`);
    }
  } catch (e) {
    Logger.log(`⚠️ publishablePublish error: ${e.message}`);
  }

  // Success — caller handles UI notification

  return {
    success: true,
    data: {
      productUrl,
      productId: productIdDigitsOnly,
      veteranVariantGid,
      earlyVariantGid,
      openVariantGid,
      waitlistVariantGid
    }
  };
}
/**
 * Get variant ID from product
 */
export function getVariantId(productGid) {
  const query = `
    query {
      product(id: "${productGid}") {
        variants(first: 1) { nodes { id } }
      }
    }`;

  let response;
  try {
    response = UrlFetchApp.fetch(getSecret('SHOPIFY_GRAPHQL_URL'), {
      method: "POST",
      contentType: "application/json",
      headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_ACCESS_TOKEN') },
      payload: JSON.stringify({ query }),
      muteHttpExceptions: true
    });
  } catch (_err) {
    Logger.log(`❌ getVariantId network error: ${err.message}`);
    return null;
  }

  let data;
  try {
    data = JSON.parse(response.getContentText());
  } catch (_err) {
    Logger.log(`❌ getVariantId parse error: ${response.getContentText()}`);
    return null;
  }

  Logger.log(`🔍 getVariantId response: ${JSON.stringify(data, null, 2)}`);
  const variantId = data.data?.product?.variants?.nodes[0]?.id || null;
  if (!variantId) Logger.log(`❌ No variant found in Shopify response for product ${productGid}`);
  return variantId;
}

/**
 * Update variant settings (tax, shipping)
 */
export function updateVariantSettings(variantId) {
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

  let response;
  try {
    response = UrlFetchApp.fetch(getSecret('SHOPIFY_GRAPHQL_URL'), {
      method: "POST",
      contentType: "application/json",
      headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_ACCESS_TOKEN') },
      payload: JSON.stringify(mutation),
      muteHttpExceptions: true
    });
  } catch (_err) {
    Logger.log(`❌ updateVariantSettings network error: ${err.message}`);
    return;
  }

  let data;
  try {
    data = JSON.parse(response.getContentText());
  } catch (_err) {
    Logger.log(`❌ updateVariantSettings parse error: ${response.getContentText()}`);
    return;
  }

  Logger.log(`🔧 updateVariantSettings response: ${JSON.stringify(data, null, 2)}`);
  const errors = data.data?.productVariantUpdate?.userErrors || [];
  if (errors.length) {
    Logger.log(`❌ updateVariantSettings userErrors: ${JSON.stringify(errors, null, 2)}`);
  }
}

/**
 * Enable inventory tracking for variant
 */
export function enableInventoryTracking(variantIdDigitsOnly) {
  const url = `${getSecret('SHOPIFY_REST_URL')}/variants/${variantIdDigitsOnly}.json`;
  const payload = {
    variant: {
      id: parseInt(variantIdDigitsOnly, 10),
      inventory_management: "shopify"
    }
  };

  let response;
  try {
    response = UrlFetchApp.fetch(url, {
      method: "PUT",
      contentType: "application/json",
      headers: { "X-Shopify-Access-Token": getSecret('SHOPIFY_ACCESS_TOKEN') },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    });
  } catch (_err) {
    Logger.log(`❌ enableInventoryTracking network error: ${err.message}`);
    return;
  }

  let data;
  try {
    data = JSON.parse(response.getContentText());
  } catch (_err) {
    Logger.log(`❌ enableInventoryTracking parse error: ${response.getContentText()}`);
    return;
  }

  Logger.log(`📦 enableInventoryTracking response: ${JSON.stringify(data, null, 2)}`);
  if (response.getResponseCode() !== 200) {
    Logger.log(`❌ enableInventoryTracking HTTP ${response.getResponseCode()}: ${JSON.stringify(data, null, 2)}`);
  }
}

/**
 * Schedule product publication
 */
export function scheduleProductPublication(productIdDigitsOnly, _rawRegistrationStartDateTime) {
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
      "X-Shopify-Access-Token": getSecret('SHOPIFY_ACCESS_TOKEN')
    },
    payload: query
  };

  try {
    const response = UrlFetchApp.fetch(getSecret('SHOPIFY_GRAPHQL_URL'), options);
    const responseData = JSON.parse(response.getContentText());
    Logger.log(`***publish function response***: ${JSON.stringify(responseData, null, 2)}`);

    const pubErrors = responseData.data?.productPublish?.userErrors || [];
    if (pubErrors.length) {
      Logger.log(`❌ productPublish errors: ${JSON.stringify(pubErrors)}`);
    }
  } catch (error) {
    Logger.log(`❌ Error in scheduling publication: ${error.message}`);
  }
}
