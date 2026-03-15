/**
 * Input validation utilities
 * Pure functions for validating user inputs and form data
 */

/**
 * Validate signup parameters
 */
export function validateSignupParams(params) {
  const firstName = params.firstName?.trim() || null;
  const lastName = params.lastName?.trim() || null;
  const email = params.email?.trim().toLowerCase() || null;
  const phone = params.phone?.trim() || null;
  const customerId = params.customerId?.trim() || null;
  const productId = params.productId?.trim() || null;
  const productName = params.productName?.trim() || null;
  const submittedAt = new Date().toISOString();

  // Validation
  if (!firstName || firstName.length < 1) {
    return { valid: false, message: 'First name is required' };
  }

  if (!lastName || lastName.length < 1) {
    return { valid: false, message: 'Last name is required' };
  }

  if (!email || !email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
    return { valid: false, message: 'Valid email address is required' };
  }

  if (!phone || phone.length < 10) {
    return { valid: false, message: 'Valid phone number is required' };
  }

  if (!productId) {
    return { valid: false, message: 'Product ID is required' };
  }

  return {
    valid: true,
    data: { firstName, lastName, email, phone, customerId, productId, productName, submittedAt }
  };
}

/**
 * Check if email/customerId already exists on waitlist for this product
 */
export function checkExistingEntry(sheetsClient, email, customerId, productId) {
  try {
    const allProductsData = sheetsClient.getAllProductsData();
    const productData = allProductsData.get(productId);

    if (!productData) {
      return { exists: false, position: null };
    }

    // Check by email first
    if (email) {
      const emailLower = email.toLowerCase().trim();
      const existingEntry = productData.byEmail.get(emailLower);
      if (existingEntry) {
        return {
          exists: true,
          position: existingEntry.id,
          method: 'email'
        };
      }
    }

    // Check by customer ID
    if (customerId) {
      const customerIdTrim = customerId.toString().trim();
      const existingEntry = productData.byCustomerId.get(customerIdTrim);
      if (existingEntry) {
        return {
          exists: true,
          position: existingEntry.id,
          method: 'customerId'
        };
      }
    }

    return { exists: false, position: null };

  } catch (error) {
    console.error('Error checking existing entry:', error);
    return { exists: false, position: null, error: error.message };
  }
}

/**
 * Validate position check parameters
 */
export function validatePositionCheckParams(params) {
  const email = params.email?.trim().toLowerCase() || null;
  const productId = params.productId?.trim() || null;
  const customerId = params.customerId?.trim() || null;

  if (!email && !customerId) {
    return { valid: false, message: 'Email or Customer ID is required' };
  }

  if (!productId) {
    return { valid: false, message: 'Product ID is required' };
  }

  return {
    valid: true,
    data: { email, customerId, productId }
  };
}

/**
 * Validate product parameters
 */
export function validateProductParams(params) {
  const productId = params.productId?.trim() || null;

  if (!productId) {
    return { valid: false, message: 'Product ID is required' };
  }

  return { valid: true, data: { productId } };
}

/**
 * Validate customer parameters
 */
export function validateCustomerParams(params) {
  const email = params.email?.trim().toLowerCase() || null;
  const customerId = params.customerId?.trim() || null;

  if (!email && !customerId) {
    return { valid: false, message: 'Email or Customer ID is required' };
  }

  return { valid: true, data: { email, customerId } };
}