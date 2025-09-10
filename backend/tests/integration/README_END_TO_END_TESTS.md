# End-to-End Refund Flow Integration Tests

This document describes the comprehensive integration test suite for the BARS refund system, covering every possible path through the workflow.

## 🎯 **Test Coverage Overview**

The test suite covers **ALL** refund system flows:

### **Initial Request Validation**
- ❌ **Invalid Order Number** → 406 error + Slack notification
- ⚠️ **Email Mismatch** → 409 error + Slack warning with edit/deny options  
- 🔄 **Duplicate Refund** → 409 error + Slack notification with pending/completed amounts
- ✅ **Valid Requests** → 200 success + full Slack message with action buttons

### **Refund Calculation Timing Tiers**
- 🕒 **>2 weeks before season** → 95% refund / 100% credit
- 🕒 **<2 weeks, before start** → 90% refund / 95% credit
- 🕒 **Week 1 started** → 80% refund / 85% credit
- 🕒 **Week 2 started** → 70% refund / 75% credit
- 🕒 **Week 3 started** → 60% refund / 65% credit
- 🕒 **Week 4 started** → 50% refund / 55% credit
- 🕒 **After Week 5** → $0 refund/credit

### **Order Management Flows**
- 🚫 **Cancel Order → Proceed** → Order cancelled in Shopify + status update
- ➡️ **Do Not Cancel → Proceed** → Order remains active + status update
- 🔄 **Edit Request Details** → Modal for updating order#/email + re-validation

### **Refund Processing Flows**
- 💰 **Process Refund** → Create refund in Shopify + inventory options
- 💳 **Custom Amount** → Modal for custom refund amount + processing
- 🚫 **Do Not Provide Refund** → No refund issued + inventory options

### **Inventory Management**
- 📦 **Restock Variant** → Restore inventory + completion message
- ❌ **Do Not Restock** → Skip inventory + completion message

### **Denial Flows**
- 🚫 **Deny Request** → Modal for custom denial message + email sending
- 📧 **Denial Email** → GAS webhook for customer notification

### **Error Handling**
- ❌ **Shopify API Failures** → Graceful error handling + status updates
- ❌ **Slack API Failures** → Error reporting + retry logic
- ❌ **Invalid Data** → Validation errors + user feedback

## 🏗️ **Test Structure**

### **File Organization**
```
backend/tests/integration/
├── test_end_to_end_refund_flows.py     # Main test suite
├── README_END_TO_END_TESTS.md          # This documentation
└── run_integration_tests.py            # Test runner script
```

### **Test Class Structure**
```python
class TestEndToEndRefundFlows:
    def setup_method(self):           # Mock setup for each test
        # Shopify API mocks
        # Slack API mocks  
        # Test data templates
        # Expected message templates
    
    # === INITIAL REQUEST FLOWS ===
    def test_invalid_order_number_flow(self)
    def test_email_mismatch_flow(self)
    def test_duplicate_refund_pending_flow(self)
    def test_valid_refund_request_early_timing(self)
    def test_valid_credit_request_early_timing(self)
    
    # === TIMING TIER TESTS ===
    @pytest.mark.parametrize("submission_date,expected_amount,expected_tier", [...])
    def test_refund_timing_tiers(self)
    
    # === ORDER CANCELLATION FLOWS ===
    def test_cancel_order_button_flow(self)
    def test_proceed_without_cancel_flow(self)
    
    # === REFUND PROCESSING FLOWS ===
    def test_process_refund_flow(self)
    def test_no_refund_flow(self)
    
    # === INVENTORY RESTOCK FLOWS ===
    def test_restock_inventory_flow(self)
    def test_do_not_restock_flow(self)
    
    # === DENIAL FLOWS ===
    def test_deny_request_modal_flow(self)
    def test_deny_request_submission_flow(self)
    
    # === ERROR HANDLING ===
    def test_order_cancellation_failure(self)
    def test_refund_creation_failure(self)
    
    # === UPDATE REQUEST DETAILS ===
    def test_edit_request_details_modal(self)
    def test_edit_request_details_success_submission(self)
    
    # === MESSAGE CONSISTENCY ===
    def test_message_format_consistency(self)
    def test_refund_vs_credit_message_differences(self)
```

## 📋 **Expected Slack Message Formats**

Each test includes **commented examples** of the expected final Slack messages. Here are the key formats:

### **🚫 Order Not Found**
```
🚫 **ORDER NOT FOUND** 🚫

📦 **Order Number:** #99999
📧 **Requested by:** John Doe (john.doe@example.com)
🎯 **Refund Type:** refund
📝 **Notes:** Customer needs refund due to scheduling conflict

❌ Order #99999 was not found in Shopify. Please verify the order number and try again.

📋 **Next Steps:**
• Verify the order number with the customer
• Check if the order was placed in a different system
• Contact customer to confirm correct order details
```

### **⚠️ Email Mismatch**
```
⚠️ **EMAIL MISMATCH DETECTED** ⚠️

📦 **Order Number:** <https://admin.shopify.com/store/test/orders/5875167625310|#42234>
📧 **Requested by:** <https://admin.shopify.com/store/test/customers/6875123456789|John Doe> (john.doe@example.com)
📧 **Order Email:** different.email@example.com (<https://admin.shopify.com/store/test/customers/search?query=different.email@example.com|Click here to view orders associated with different.email@example.com>)
🎯 **Refund Type:** refund
📝 **Notes:** Customer needs refund due to scheduling conflict

❌ The email provided does not match the order's customer email.
Please either view orders above to edit with the correct details, reach out to the requestor to confirm, or click Deny Request to notify the player their request has been denied due to mismatching details.

📋 **Available Actions:**
• Edit Request Details - Update order number or email
• Deny Request - Send denial email to requestor
```

### **✅ Valid Initial Request**
```
🎯 **REFUND REQUEST** 🎯

📦 **Order Number:** <https://admin.shopify.com/store/test/orders/5875167625310|#42234>
📧 **Requested by:** <https://admin.shopify.com/store/test/customers/6875123456789|John Doe> (john.doe@example.com)
🎯 **Refund Type:** refund
📝 **Notes:** Customer needs refund due to scheduling conflict

🏷️ **Product:** <https://admin.shopify.com/store/test/products/7350462185566|Pickleball Monday>
📅 **Season Start Date:** 10/15/24
📅 **Order Date:** 09/09/25 at 1:16 AM
💰 **Original Amount Paid:** $100.00

💵 **Estimated Refund Due:** $95.00
(This request is calculated to have been submitted more than 2 weeks before week 1 started. 95% after 0% penalty + 5% processing fee)

📋 **Next Steps:**
• **Cancel Order → Proceed** - Cancel the order and continue with refund
• **Do Not Cancel Order → Proceed** - Keep order active and continue
• **Deny Request** - Deny the refund request
```

### **✅ Final Completion**
```
✅ **REFUND COMPLETED** ✅

📦 **Order Number:** <https://admin.shopify.com/store/test/orders/5875167625310|#42234>
📧 **Requested by:** <https://admin.shopify.com/store/test/customers/6875123456789|John Doe> (john.doe@example.com)
🎯 **Refund Type:** refund
📝 **Notes:** Customer needs refund due to scheduling conflict

🏷️ **Product:** <https://admin.shopify.com/store/test/products/7350462185566|Pickleball Monday>
📅 **Order Date:** 09/09/25 at 1:16 AM
💰 **Original Amount Paid:** $100.00

💵 **Refund Provided:** $95.00

🚀 **Order Canceled** by <@U1234567890>
💰 **Refunded by** <@U1234567890>
📦 **Inventory Restocked:** Early Bird variant by <@U1234567890>

✅ **Process Complete**
```

## 🧪 **Running the Tests**

### **Using the Test Runner**
```bash
# Run all integration tests
python run_integration_tests.py all

# Run specific scenario
python run_integration_tests.py scenario invalid_order
python run_integration_tests.py scenario email_mismatch
python run_integration_tests.py scenario valid_refund

# Run by category
python run_integration_tests.py category initial
python run_integration_tests.py category processing
python run_integration_tests.py category restock

# Show help
python run_integration_tests.py help
```

### **Using Pytest Directly**
```bash
# Run all integration tests
pytest -v tests/integration/test_end_to_end_refund_flows.py

# Run specific test
pytest -v -k "test_invalid_order_number_flow" tests/integration/test_end_to_end_refund_flows.py

# Run with coverage
pytest --cov=services --cov=routers tests/integration/test_end_to_end_refund_flows.py
```

## 🏷️ **Mock Strategy**

### **Shopify API Mocks**
- ✅ Order fetching (valid, invalid, email mismatch)
- ✅ Existing refund detection (none, pending, completed)
- ✅ Customer data retrieval
- ✅ Refund creation
- ✅ Order cancellation
- ✅ Inventory restocking
- ✅ Product variant retrieval

### **Slack API Mocks**
- ✅ Message sending
- ✅ Message updating
- ✅ Modal opening
- ✅ Signature verification
- ✅ User interaction payloads

### **External Service Mocks**
- ✅ GAS webhook calls
- ✅ Email sending
- ✅ Timestamp parsing

## 🔍 **Test Validation**

Each test validates:

### **API Response Codes**
- ✅ 200 for successful requests
- ✅ 406 for order not found
- ✅ 409 for email mismatch and duplicates
- ✅ 500 for server errors

### **Shopify Integration**
- ✅ Correct API calls made
- ✅ Proper error handling
- ✅ Data transformation accuracy

### **Slack Integration**
- ✅ Message format consistency
- ✅ Button data preservation
- ✅ User tagging format
- ✅ Hyperlink structure

### **Message Content**
- ✅ Required information present
- ✅ Consistent formatting
- ✅ Proper status updates
- ✅ Action button accuracy

## 🚀 **Pre-Refactoring Safety**

These tests provide **comprehensive coverage** to ensure refactoring doesn't break core logic:

### **Protected Functionality**
- ✅ All request validation paths
- ✅ Every Slack message format
- ✅ All button interaction flows
- ✅ Error handling scenarios
- ✅ Edge cases and timing tiers

### **Refactoring Confidence**
- 🔄 **Service Layer Reorganization** → Tests verify external behavior remains consistent
- 🔄 **Code Structure Changes** → Tests catch any logic breaks
- 🔄 **Message Format Updates** → Tests show exactly what changed
- 🔄 **API Modifications** → Tests validate contract compliance

## 📈 **Benefits**

### **Development**
- 🎯 **Clear Requirements** → Each test documents expected behavior
- 🐛 **Bug Prevention** → Comprehensive edge case coverage
- 🔄 **Safe Refactoring** → Change code with confidence
- 📋 **Living Documentation** → Tests show current system behavior

### **Quality Assurance** 
- ✅ **End-to-End Verification** → Full workflow testing
- 🔍 **Message Format Validation** → Consistent user experience
- ⚡ **Fast Feedback** → Automated testing catches issues early
- 📊 **Coverage Metrics** → Know what's tested and what isn't

### **Maintenance**
- 🎯 **Targeted Testing** → Run specific scenarios during development
- 🔧 **Easy Debugging** → Isolated test failures point to specific issues
- 📈 **Regression Prevention** → Historical behavior preserved
- 🚀 **Deployment Confidence** → Comprehensive pre-deployment validation

---

## 🎉 **Ready for Refactoring!**

With this comprehensive test suite in place, you can confidently refactor and reorganize the refund system code knowing that any breaking changes will be immediately detected. The tests serve as both **safety net** and **living documentation** of the expected system behavior.

Run the tests frequently during refactoring to ensure all core logic remains intact! 🚀
