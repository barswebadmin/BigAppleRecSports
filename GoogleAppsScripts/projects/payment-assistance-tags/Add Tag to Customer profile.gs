function getOrCreateShopifyCustomer(email) {
  // Step 1: Try to fetch the existing customer
  const query = {
    query: `query GetCustomerId($identifier: CustomerIdentifierInput!) {
      customerByIdentifier(identifier: $identifier) { id firstName lastName tags }
    }`,
    variables: { identifier: { emailAddress: email } }
  };

  const responseData = fetchShopify(query);
  Logger.log(`🔍 Shopify Query Response: ${JSON.stringify(responseData, null, 2)}`);

  if (responseData?.customerByIdentifier) {
    // ✅ Customer exists, return details
    const customerDetails = {
      email: email,
      gid: responseData.customerByIdentifier.id,
      firstName: responseData.customerByIdentifier.firstName || null,
      lastName: responseData.customerByIdentifier.lastName || null,
      tagsArray: responseData.customerByIdentifier.tags || [],
      newOrReturning: "returning"
    };

    Logger.log(`✅ Found existing customer: ${JSON.stringify(customerDetails)}`);
    return customerDetails;
  }

  // Step 2: Customer not found, create a new one
  Logger.log(`⚠️ Customer not found. Attempting to create a new customer for email: ${email}`);

  const createMutation = {
    query: `mutation customerCreate($input: CustomerInput!) {
      customerCreate(input: $input) {
        userErrors { field message }
        customer { id }
      }
    }`,
    variables: {
      input: {
        email: email
      }
    }
  };

  const createResponse = fetchShopify(createMutation);
  Logger.log(`🔍 Shopify Create Response: ${JSON.stringify(createResponse, null, 2)}`);

  if (createResponse?.customerCreate?.customer?.id) {
    // ✅ New customer created successfully
    const newCustomer = {
      email: email,
      gid: createResponse.customerCreate.customer.id,
      tagsArray: createResponse.customerCreate.customer.tags || [],
      newOrReturning: "new"
    };

    Logger.log(`✅ Successfully created new customer: ${JSON.stringify(newCustomer)}`);
    return newCustomer;
  } else {
    // ❌ Error creating customer
    const errorMessages = createResponse?.customerCreate?.userErrors?.map(e => `${e.field}: ${e.message}`).join(", ") || "Unknown error";
    Logger.log(`❌ Error creating customer: ${errorMessages}`);
    return { gid: null, tagsArray: [], error: errorMessages };
  }
}

const addTagToCustomerProfile = ({playerDetails, discountDetails}) => {
  const fetchedCustomerDetails = getOrCreateShopifyCustomer(playerDetails.email)
  Logger.log(`this tag! ${discountDetails.tag}`)
  if (!fetchedCustomerDetails.gid) {
    return { success: false, message: `❌ No Shopify customer found for '${playerDetails.email}'.` };
  }

  const updatedTags = [...fetchedCustomerDetails.tagsArray, discountDetails.tag];
  return addDiscountTagToCustomerTags({ 
    customerDetails: fetchedCustomerDetails, 
    updatedTags, 
    discountDetails,
    newOrReturning: fetchedCustomerDetails.newOrReturning
  });
}

function addDiscountTagToCustomerTags({ customerDetails, updatedTags, discountDetails, newOrReturning }) {
  Logger.log(`updatedTags!: ${updatedTags}`)
  const mutation = {
    query: `mutation updateCustomerMetafields($input: CustomerInput!) { 
      customerUpdate(input: $input) { customer { id tags } userErrors { message field } } 
    }`,
    variables: { input: { id: customerDetails.gid, tags: updatedTags } }
  };

  const responseData = fetchShopify(mutation);
  Logger.log(`🛠 Shopify Mutation Response: ${JSON.stringify(responseData, null, 2)}`);

  if (!responseData) {
    Logger.log("❌ Error fetching customer details.");
    return { gid: null, tagsArray: [] };
  }

  if (responseData.customerUpdate?.userErrors?.length) {
    Logger.log(`❌ Shopify Errors: ${JSON.stringify(responseData.customerUpdate?.userErrors)}`);
    return { success: false, message: "Tag not added successfully to Customer. Please check details and try again." };
  } else {

    return {
      success: true,
      newOrReturning: newOrReturning,
      message: `✅ Processed successfully: ${customerDetails.firstName} ${customerDetails.lastName} (${customerDetails.email}) has been provided with a ${discountDetails.type}, which allows them to use the discount code: \n
      ${discountDetails.code} 
      \n \n 
      They have been emailed with details, and the executive-board@ alias has been CC'd!`
    };
  }
}
