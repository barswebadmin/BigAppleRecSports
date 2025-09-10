# Parse Registration Info - Automated Testing

## 🎯 Overview

This directory contains automated tests for the `parse-registration-info` Google Apps Script project. Tests run locally during development and automatically in CI/CD pipelines.

## 🚀 Quick Start

### **Run Tests Locally**
```bash
# From GoogleAppsScripts/tests directory
./test_parse_registration_comprehensive.sh

# Or run Node.js tests directly
cd parse-registration-info
npm test
```

### **Install Dependencies**
```bash
cd GoogleAppsScripts/tests/parse-registration-info
npm install
```

## 📁 Structure

```
GoogleAppsScripts/tests/parse-registration-info/
├── package.json              # Node.js dependencies and scripts
├── test-runner.js            # Main automated test runner
├── README.md                 # This documentation
└── node_modules/             # Installed dependencies (created by npm install)
```

## 🧪 Test Categories

### **1. Date Parsing Tests**
- Standard date formats (MM/DD/YYYY, M/D/YYYY)
- Invalid date handling
- Empty date handling

### **2. Flags Parsing Tests** 
- **Buddy signup detection** (your specific "Buddy Sign Ups" case)
- Day parsing from text
- Flag extraction from descriptions

### **3. Location Normalization Tests**
- John Jay College canonicalization
- Unknown location passthrough

### **4. Price Parsing Tests**
- Standard price formats ($45, $45.50)
- Price extraction from descriptive text

### **5. Write Validation Tests**
- **Data validation failure detection** (catches "Buddy Signup" vs "Buddy Sign-up" mismatches)
- Write attempt tracking
- Failure reason reporting

### **6. End-to-End Integration Tests**
- Complete parsing pipeline validation
- Real-world data scenarios

## 🔧 Key Features

### **✅ Catches Your Specific Issue**
The tests specifically validate the "Buddy Signup" vs "Buddy Sign-up" data validation issue:

```javascript
// Tests detect when target sheet data validation rules change values
const parserOutput = 'Buddy Signup';      // What parser generates
const targetExpected = 'Buddy Sign-up';   // What sheet actually accepts
const validationFails = parserOutput !== targetExpected; // ✅ Detected!
```

### **✅ CI/CD Integration**
- Runs automatically on push to GitHub
- Integrates with existing `run_all_tests.sh` framework
- Fails CI builds if tests fail

### **✅ Local Development**
- Fast feedback during development
- No need for Google Apps Script editor
- Works offline

## 🛠️ Technology Stack

- **Node.js**: Test execution environment
- **JavaScript**: Test language (compatible with Google Apps Script)
- **Mock APIs**: Simulates Google Apps Script environment
- **Shell Scripts**: Integration with existing test framework

## 📊 Test Execution Flow

1. **Shell script** (`test_parse_registration_comprehensive.sh`) is called
2. **Node.js availability** is checked
3. **Dependencies** are installed if needed
4. **Test runner** (`test-runner.js`) executes all tests
5. **Results** are reported with pass/fail status
6. **Exit code** indicates overall success/failure

## 🔍 Debugging Tests

### **Run Specific Test Types**
```bash
node test-runner.js --type=unit         # Unit tests only
node test-runner.js --type=integration  # Integration tests only
```

### **Verbose Output**
```bash
node test-runner.js --verbose
```

### **Watch Mode** (during development)
```bash
npm run test:watch
```

## 📋 Adding New Tests

### **1. Add Test Function**
```javascript
// In test-runner.js
function testNewFeature() {
  console.log(`\n${colors.blue}${colors.bold}🆕 New Feature Tests${colors.reset}`);
  
  runTest('Test new feature behavior', () => {
    const result = newFunction_('test input');
    assertEquals(result, 'expected output');
  });
}
```

### **2. Call from Main**
```javascript
// In main() function
testNewFeature();
```

### **3. Load Required Functions**
```javascript
// In loadGASFunctions()
const gasFiles = [
  // ... existing files
  'new-feature/newFeature.gs'
];
```

## 🚨 Important Notes

### **No Google Apps Script Editor Required**
- All tests run locally or in CI
- No manual execution in Google Apps Script
- No dependency on Google Sheets API for testing

### **Mock Environment**
- Google Apps Script APIs are mocked for testing
- Real sheet interactions are simulated
- Safe to run without affecting production data

### **CI/CD Enforcement**
- Tests must pass for PRs to be merged
- Prevents deployment of broken code
- Catches regressions automatically

## 📚 Related Documentation

- [Backend Testing Guide](../../../docs/testing/README.md)
- [CI/CD Workflows](../../../.github/workflows/)
- [Google Apps Scripts Tests](../run_all_tests.sh)
