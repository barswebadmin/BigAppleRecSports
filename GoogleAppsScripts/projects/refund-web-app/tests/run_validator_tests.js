#!/usr/bin/env node
/* Minimal validator tests for GAS validators.gs using Node VM */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

function loadValidators() {
  const filePath = path.join(__dirname, '../src/validators.gs');
  const code = fs.readFileSync(filePath, 'utf8');
  const context = {};
  vm.createContext(context);
  new vm.Script(code, { filename: 'validators.gs' }).runInContext(context);
  const { validateEmail, validateOrderNumber, validateInputs } = context;
  if (typeof validateEmail !== 'function' || typeof validateOrderNumber !== 'function') {
    throw new Error('Validators not loaded properly');
  }
  return { validateEmail, validateOrderNumber, validateInputs };
}

function run() {
  const { validateEmail, validateOrderNumber } = loadValidators();
  let failures = 0;
  const tests = [];

  function t(name, fn) {
    tests.push({ name, fn });
  }

  function expect(cond, msg) {
    if (!cond) throw new Error(msg || 'Assertion failed');
  }

  // Email tests (1+ before @, 1+ after @, dot, 2+ TLD; no spaces)
  t('email valid: a@b.cd', () => {
    const r = validateEmail('a@b.cd');
    expect(r.success === true, 'expected valid');
  });
  t('email valid: john@example.com', () => {
    const r = validateEmail('john@example.com');
    expect(r.success === true, 'expected valid');
  });
  t('email invalid: missing tld length', () => {
    const r = validateEmail('a@b.c');
    expect(r.success === false, 'expected invalid');
    expect(r.message && r.message.length > 0, 'expected message');
  });
  t('email invalid: no local part', () => {
    const r = validateEmail('@example.com');
    expect(r.success === false, 'expected invalid');
  });
  t('email invalid: space in address', () => {
    const r = validateEmail('a b@c.com');
    expect(r.success === false, 'expected invalid');
  });

  // Order number tests (digits only, length >= 5)
  t('order valid: 12345', () => {
    const r = validateOrderNumber('12345');
    expect(r.success === true, 'expected valid');
  });
  t('order valid: 00000', () => {
    const r = validateOrderNumber('00000');
    expect(r.success === true, 'expected valid');
  });
  t('order invalid: too short', () => {
    const r = validateOrderNumber('1234');
    expect(r.success === false, 'expected invalid');
  });
  t('order invalid: non-digit char', () => {
    const r = validateOrderNumber('12a45');
    expect(r.success === false, 'expected invalid');
  });
  t('order invalid: empty', () => {
    const r = validateOrderNumber('');
    expect(r.success === false, 'expected invalid');
  });

  // Execute tests
  for (const { name, fn } of tests) {
    try {
      fn();
      console.log(`✅ ${name}`);
    } catch (e) {
      failures += 1;
      console.log(`❌ ${name}: ${e.message || e}`);
    }
  }

  if (failures > 0) {
    console.log(`\n❌ ${failures} test(s) failed`);
    process.exit(1);
  } else {
    console.log('\n✅ All validator tests passed');
  }
}

run();


