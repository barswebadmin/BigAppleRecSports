/**
 * Validate email format
 * @param {string} email
 * @return {{success:boolean,message:string}}
 */
function validateEmail(email) {
  // 1+ chars + '@' + 1+ chars + '.' + 2+ chars, no spaces
  var ok = typeof email === 'string' && /^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(email);
  return {
    success: ok,
    message: ok ? '' : "'" + String(email) + "' is not a valid email address. Please try again."
  };
}

/**
 * Validate order number (length >= 5)
 * @param {string} order
 * @return {{success:boolean,message:string}}
 */
function validateOrderNumber(order) {
  var ok = typeof order === 'string' && /^\d{5,}$/.test(order);
  return {
    success: ok,
    message: ok ? '' : "'" + String(order) + "' is not a valid order number. Please try again. Sign into your accout if unsure."
  };
}

/**
 * Combined validator for client
 * @param {string} email
 * @param {string} order
 * @return {{ok:boolean,email:{success:boolean,message:string},order:{success:boolean,message:string}}}
 */
function validateInputs(email, order) {
  var e = validateEmail(email);
  var o = validateOrderNumber(order);
  return { ok: e.success && o.success, email: e, order: o };
}


