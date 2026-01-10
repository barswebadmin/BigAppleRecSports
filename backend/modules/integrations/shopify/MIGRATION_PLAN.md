# Shopify Integration Migration & Cleanup Plan

## Current State Analysis

### ✅ **KEEP & MODERNIZE** (New sgqlc-based stack)

#### **Clients**
- ✅ `client/shopify_sgqlc_client.py` - **KEEP** - Modern GraphQL client using sgqlc
- ✅ `models/sgqlc_models/` - **KEEP** - New Pydantic + sgqlc bridge models
  - `customer_pydantic.py`, `order_pydantic.py`, `product_pydantic.py`
  - `sgqlc_bridge.py` - **KEEP** (just refactored)
  - `sgqlc_query.py` - **KEEP** - Query builder using sgqlc

#### **Models (New)**
- ✅ `models/responses.py` - **KEEP** - `ShopifyResponse` model (useful for error handling)
- ✅ `models/requests.py` - **KEEP** - `FetchOrderRequest` (still used)

### ⚠️ **REFACTOR & MIGRATE** (Has value but needs updating)

#### **Builders**
- ⚠️ `builders/shopify_query_builders.py` - **REFACTOR**
  - Has inventory mutations (`build_adjust_inventory_mutation`) - **KEEP**
  - Has product queries (`get_product_details_query`) - **MIGRATE to sgqlc**
  - Old order query builder - **REPLACE with sgqlc_query.py**

- ⚠️ `builders/shopify_customer_utils.py` - **REFACTOR**
  - `get_customer_with_tags()` - **MIGRATE to new service**
  - `add_tag_to_customer()` - **MIGRATE to new service**
  - `get_customers_batch()` - **MIGRATE to new service**
  - `create_segment()` - **MIGRATE to new service**
  - `create_discount_code()` - **MIGRATE to new service** (or move to domain service)

- ⚠️ `builders/shopify_order_utils.py` - **REFACTOR**
  - `cancel_order()` - **MIGRATE to new service**
  - `create_refund()` - **MIGRATE to new service**
  - `get_order_details()` - **REPLACE with sgqlc models**

- ⚠️ `builders/shopify_request_builders.py` - **PARTIALLY KEEP**
  - `build_order_fetch_request_payload()` - **REPLACE with sgqlc_query.py**
  - Field selection helpers - **REPLACE with sgqlc recursive selection**

#### **Parsers**
- ⚠️ `parsers/parse_shopify_response.py` - **KEEP** - Useful error classification
- ⚠️ `parsers/mappers.py` - **REVIEW** - May be redundant with sgqlc bridge
- ⚠️ `parsers/order_mapper.py` - **REVIEW** - May be redundant with sgqlc bridge

### ❌ **DEPRECATE & DELETE** (Redundant or obsolete)

#### **Clients**
- ❌ `client/shopify_client.py` - **DEPRECATE** - Old REST/GraphQL string-based client
  - Replaced by `shopify_sgqlc_client.py`
  - Still used by: `shopify_service.py`, `shopify_cli.py`, `OrdersService`
  - **Migration**: Update all callers to use `ShopifySGQLCClient`

- ❌ `client/shopify_config.py` - **DELETE** - Old `ShopifyConfig` class
  - **Note**: There are TWO `ShopifyConfig` classes:
    1. `backend/config/shopify.py` - **KEEP** (used by global config system)
    2. `backend/modules/integrations/shopify/client/shopify_config.py` - **DELETE** (old, redundant)
  - Replaced by `backend/config.py` (global config) which uses `backend/config/shopify.py`
  - **Action**: Find all usages of `client/shopify_config.py`, replace with `config.Shopify.*`, then delete

- ❌ `client/shopify_service.py` - **DEPRECATE** - Old service using old client
  - Only has `fetch_order()` and mock responses
  - **Action**: Replace with new `ShopifyService` in `services/`

- ❌ `client/shopify_cli.py` - **REVIEW** - CLI tool, may be obsolete if bars_cli replaces it

#### **Models (Old)**
- ❌ `models/customers.py` - **DELETE** - Old Pydantic model
  - Replaced by `sgqlc_models/customer_pydantic.py`
  - **Action**: Check for imports, migrate, delete

- ❌ `models/orders.py` - **DELETE** - Old Pydantic model  
  - Replaced by `sgqlc_models/order_pydantic.py`
  - **Action**: Check for imports, migrate, delete

- ❌ `models/products/products.py` - **DELETE** - Old simple Product model
  - Replaced by `sgqlc_models/product_pydantic.py`
  - **Action**: Check for imports, migrate, delete

- ⚠️ `models/products/product_creation_request/` - **KEEP** - Domain-specific request models
  - These are BARS-specific, not pure Shopify
  - **Action**: Keep but may need updates for new service

#### **Builders (Obsolete)**
- ❌ `builders/shopify_url_builders.py` - **KEEP** - URL building is still useful
- ❌ `builders/shopify_service_methods_to_update.py` - **DELETE** - Appears to be scratch/notes file
- ❌ `builders/fetch_order_details.graphql` - **DELETE** - Replaced by sgqlc models
- ❌ `builders/raw_curl_requests.js` - **DELETE** - Scratch file

## Functionality Inventory

### **Currently Exists (Old Stack)**

#### **Customers**
- ✅ Get customer by email (`shopify_customer_utils.py`)
- ✅ Get customer with tags (`shopify_customer_utils.py`)
- ✅ Add tag to customer (`shopify_customer_utils.py`)
- ✅ Batch get customers (`shopify_customer_utils.py`)
- ✅ Create customer segment (`shopify_customer_utils.py`)
- ✅ Create discount code (`shopify_customer_utils.py`) - **Note**: This is BARS domain logic

#### **Orders**
- ✅ Fetch order by ID/number/email (`shopify_client.py`, `shopify_request_builders.py`)
- ✅ Cancel order (`shopify_order_utils.py`)
- ✅ Create refund (`shopify_order_utils.py`)
- ✅ Get order details (`shopify_order_utils.py`)

#### **Products**
- ✅ Get product details (`shopify_query_builders.py`)
- ✅ Product creation request models (`product_creation_request/`)
- ✅ Product creation/update - **FOUND in `backend/modules/products/services/`**
  - Uses old `ShopifyClient` - **NEEDS MIGRATION**
  - `create_product()` - Creates product via GraphQL
  - `create_variants()` - Creates variants
  - `update_variant_rest()` - Updates variant via REST (should migrate to GraphQL)

#### **Inventory**
- ✅ Adjust inventory (`shopify_query_builders.py`)
- ✅ Get inventory item (`shopify_query_builders.py`)

### **Recently Built (New Stack)**

#### **Customers**
- ✅ `get_customer_by_identifier()` in CLI - **MOVE to service**
- ✅ sgqlc Customer models with full field support
- ✅ Query builder in `sgqlc_query.py`

#### **Orders**
- ✅ sgqlc Order models with full field support
- ✅ Query builder in `sgqlc_query.py`
- ✅ `get_order_by_identifier()` in bars-scripts - **MOVE to service**

#### **Products**
- ✅ sgqlc Product models with full field support
- ⚠️ Query builder - **NEEDS IMPLEMENTATION**

## bars-scripts Migration Analysis

### **Scripts to CLI Commands Mapping**

#### **Customer Commands** (`bars shopify customer`)
1. ✅ `get_customer_details.py` → `bars shopify customer get` (✅ **DONE**)
2. ⚠️ `update_customer_identifier.py` → `bars shopify customer update-identifier`
   - Updates email or phone
   - Uses `customerUpdate` mutation
   - **Service Method**: `ShopifyService.customers.update_identifier(customer_id, email=None, phone=None)`

3. ⚠️ `get_pronouns.py` → `bars shopify customer get-pronouns`
   - Extracts pronouns from order line item properties
   - Searches through customer's orders
   - **Service Method**: `ShopifyService.customers.get_pronouns(customer_id)` (or via orders)

4. ⚠️ `get_bday.py` → `bars shopify customer get-birthday`
   - Extracts date of birth from order line item properties
   - **Service Method**: `ShopifyService.customers.get_birthday(customer_id)` (or via orders)

#### **Order Commands** (`bars shopify order`)
1. ✅ `get_order_details.py` → `bars shopify order get` (✅ **DONE** - in `get_order_details_pydantic.py`)
2. ⚠️ `cancel_order.py` → `bars shopify order cancel`
   - Cancels order with options (notify, refund, restock, reason)
   - **Service Method**: `ShopifyService.orders.cancel(order_id, notify=False, refund=False, restock=False, reason="CUSTOMER")`

3. ⚠️ `refund_order.py` → `bars shopify order refund`
   - Creates refund (credit or original payment)
   - **Service Method**: `ShopifyService.orders.create_refund(order_id, amount, refund_type="refund", notify=True)`

4. ⚠️ `cancel_and_refund.py` → `bars shopify order cancel-and-refund`
   - Combined workflow: cancel then refund
   - **Service Method**: Uses `cancel()` + `create_refund()` sequentially

5. ⚠️ `restock_order.py` → `bars shopify order restock`
   - Restocks inventory for order line items
   - Interactive variant selection
   - **Service Method**: `ShopifyService.orders.restock(order_id, variant_quantities: Dict[str, int])`

6. ⚠️ `apply_discount_to_orders.py` → `bars shopify order apply-discount`
   - Applies discount via Order Editing API
   - Batch processing support
   - **Service Method**: `ShopifyService.orders.apply_discount(order_id, discount_type, discount_value)`

7. ⚠️ `product_orders.py` → `bars shopify order list-by-product`
   - Gets all orders for a product (CSV export)
   - Pagination support
   - **Service Method**: `ShopifyService.orders.get_by_product(product_id, cursor=None)`

8. ⚠️ `analyze_order_refunds.py` → `bars shopify order analyze-refunds`
   - Analyzes CSV for refund eligibility
   - Uses discount calculator logic
   - **Note**: This is BARS domain logic (discount calculation), may belong in separate service

#### **Product Commands** (`bars shopify product`)
1. ⚠️ `get_product_details.py` → `bars shopify product get`
   - Get product by ID or handle
   - **Service Method**: `ShopifyService.products.get_by_id()` / `get_by_handle()`

#### **Page Commands** (`bars shopify page`)
1. ⚠️ `shopify_get_page.py` → `bars shopify page get`
   - Fetches page content by handle
   - Supports theme template fetching
   - **Service Method**: `ShopifyService.pages.get(handle)` / `get_theme_asset(theme_id, asset_key)`

2. ⚠️ `shopify_update_about_page.py` → `bars shopify page update-about`
   - Updates About Us page leadership images
   - Bulk CSV updates, single block updates, image uploads
   - **Service Method**: `ShopifyService.pages.update_about_page(updates: List[Dict])`

#### **Utility Commands** (Not Shopify-specific)
1. ⚠️ `compare_csv.py` → `bars utils compare-csv`
   - Compares two CSV files
   - **Note**: Not Shopify-specific, may belong in general utils

### **Shared Utilities to Migrate**

#### **From `shared_utils.py`:**
1. ✅ `load_environment()` - **ALREADY IN** `backend/config.py`
2. ✅ `get_shopify_config()` - **ALREADY IN** `backend/config.py` (via `config.Shopify.*`)
3. ⚠️ `make_graphql_request()` - **REPLACE WITH** `ShopifySGQLCClient.execute()`
4. ⚠️ `fetch_order()` - **MIGRATE TO** `ShopifyService.orders.get_by_identifier()`
5. ⚠️ `cancel_order()` - **MIGRATE TO** `ShopifyService.orders.cancel()`
6. ⚠️ `create_refund()` - **MIGRATE TO** `ShopifyService.orders.create_refund()`
7. ⚠️ `CUSTOMER_FIELDS`, `ORDER_FIELDS`, `PRODUCT_FIELDS` - **REPLACE WITH** sgqlc recursive field selection

#### **From `inventory_utils.py`:**
1. ⚠️ `fetch_order_line_items()` - **MIGRATE TO** `ShopifyService.orders.get_line_items()`
2. ⚠️ `fetch_all_product_variants()` - **MIGRATE TO** `ShopifyService.products.get_variants()`
3. ⚠️ `get_inventory_item_id()` - **MIGRATE TO** `ShopifyService.inventory.get_item_id()`
4. ⚠️ `update_variant_inventory()` - **MIGRATE TO** `ShopifyService.inventory.adjust()`
5. ⚠️ `prompt_restock_selection()` - **KEEP IN CLI** (interactive prompt logic)

### **Existing Backend Models**

#### **SGQLC Models** (✅ Ready to use):
- `Customer`, `CustomerConnection` (from `sgqlc_models/customer_pydantic.py`)
- `Order`, `OrderConnection` (from `sgqlc_models/order_pydantic.py`)
- `Product`, `ProductConnection` (from `sgqlc_models/product_pydantic.py`)
- `LineItem`, `LineItemConnection`
- `Refund`, `RefundTransaction`
- `MoneySet`, `MoneySetWrapper`
- `InventoryItem`
- `Image`, `ImageConnection`
- `Metafield`, `MetafieldConnection`
- `Collection`, `CollectionConnection`

#### **Response Models**:
- `ShopifyResponse` (from `models/responses.py`) - Error handling wrapper
- `ShopifyListModel` (from `sgqlc_models/common_pydantic.py`) - List wrapper with pagination

#### **Request Models**:
- `FetchOrderRequest` (from `models/requests.py`)

#### **Query Builder**:
- `Query` class (from `sgqlc_models/sgqlc_query.py`) - Recursive field selection

### **Migration Order (Priority)**

#### **Phase 1: Core Service Methods** (High Priority - Foundation)
1. ✅ `get_customer_by_identifier()` - **DONE**
2. ⚠️ `get_order_by_identifier()` - **NEXT** (similar pattern to customer)
3. ⚠️ `cancel_order()` - **HIGH** (frequently used)
4. ⚠️ `create_refund()` - **HIGH** (frequently used)
5. ⚠️ `get_product_by_id()` / `get_product_by_handle()` - **MEDIUM**

#### **Phase 2: Customer Operations** (High Priority)
1. ⚠️ `update_customer_identifier()` - Update email/phone
2. ⚠️ `get_pronouns()` - Extract from order properties (may need order service first)
3. ⚠️ `get_birthday()` - Extract from order properties (may need order service first)

#### **Phase 3: Order Operations** (High Priority)
1. ⚠️ `restock_order()` - Restock inventory (needs inventory service)
2. ⚠️ `apply_discount_to_orders()` - Order Editing API
3. ⚠️ `get_by_product()` - List orders for product (pagination)

#### **Phase 4: Inventory Operations** (Medium Priority)
1. ⚠️ `adjust_inventory()` - Core inventory mutation
2. ⚠️ `get_inventory_item()` - Get inventory item ID
3. ⚠️ `get_variants()` - Get all product variants

#### **Phase 5: Product Operations** (Medium Priority)
1. ⚠️ `get_variants()` - Already mentioned in inventory
2. ⚠️ `update_product()` - Update product fields
3. ⚠️ `update_product_tags()` - Update tags

#### **Phase 6: Page Operations** (Low Priority)
1. ⚠️ `get_page()` - Fetch page content
2. ⚠️ `update_about_page()` - Specialized page update

#### **Phase 7: Analysis/Reporting** (Low Priority)
1. ⚠️ `analyze_order_refunds()` - CSV analysis (BARS domain logic)
2. ⚠️ `compare_csv.py` - General utility (not Shopify-specific)

## Migration Plan

### **Phase 1: Create New Service Structure** (High Priority)

1. **Create `services/` directory**
   ```
   backend/modules/integrations/shopify/services/
   ├── __init__.py
   └── shopify_service.py
   ```

2. **Create `ShopifyService` class**
   - Use `ShopifySGQLCClient` (not old `ShopifyClient`)
   - Follow `SlackService` pattern (Table of Contents)
   - Organize by resource: customers, orders, products, inventory

3. **Move `get_customer_by_identifier()` from CLI**
   - Remove Click dependencies
   - Return typed results (sgqlc Type instances or Pydantic models)
   - Handle errors with exceptions (not Click exceptions)

### **Phase 2: Core Order Operations** (High Priority - Foundation)

1. **Migrate `get_order_by_identifier()` from bars-scripts**:
   - Move from `get_order_details_pydantic.py` to `ShopifyService.orders.get_by_identifier()`
   - Support ID, number, email identifiers (similar to customer)
   - Use `Query.build_order_query()` with recursive field selection
   - **CLI Command**: `bars shopify order get <identifier>`

2. **Migrate `cancel_order()` from `shared_utils.py`**:
   - Move to `ShopifyService.orders.cancel()`
   - Support all options: notify, refund, restock, reason
   - **CLI Command**: `bars shopify order cancel <order-number> [--notify] [--refund] [--restock] [--reason]`

3. **Migrate `create_refund()` from `shared_utils.py`**:
   - Move to `ShopifyService.orders.create_refund()`
   - Support credit and original payment refunds
   - Handle transaction selection automatically
   - **CLI Command**: `bars shopify order refund <order-number> <amount> [--type credit|refund]`

### **Phase 3: Customer Operations** (High Priority)

1. **Migrate `update_customer_identifier()` from bars-scripts**:
   - Move to `ShopifyService.customers.update_identifier()`
   - Support email and phone updates
   - **CLI Command**: `bars shopify customer update-identifier <id> [--email] [--phone]`

2. **Migrate from `shopify_customer_utils.py`**:
   - `get_customer_with_tags()` → `ShopifyService.customers.get_with_tags()`
   - `add_tag_to_customer()` → `ShopifyService.customers.add_tag()`
   - `get_customers_batch()` → `ShopifyService.customers.get_batch()`
   - `create_segment()` → `ShopifyService.customers.create_segment()`

3. **Extract order properties** (depends on order service):
   - `get_pronouns()` → `ShopifyService.customers.get_pronouns()` (searches order properties)
   - `get_birthday()` → `ShopifyService.customers.get_birthday()` (searches order properties)
   - **CLI Commands**: `bars shopify customer get-pronouns <identifier>`, `bars shopify customer get-birthday <identifier>`

4. **Note on `create_discount_code()`**:
   - This is BARS domain logic (leadership discounts)
   - **Decision**: Keep in `LeadershipService` or move to separate `DiscountService`?
   - **Recommendation**: Keep in `LeadershipService` (it's domain-specific)

### **Phase 4: Advanced Order Operations** (High Priority)

1. **Migrate `restock_order()` from `inventory_utils.py`**:
   - Move to `ShopifyService.orders.restock()`
   - Interactive variant selection (keep in CLI)
   - **CLI Command**: `bars shopify order restock <order-number>`

2. **Migrate `cancel_and_refund()` workflow**:
   - Combine `cancel()` + `create_refund()` in CLI
   - **CLI Command**: `bars shopify order cancel-and-refund <order-number> [--cancel-reason] [--refund-type]`

3. **Migrate `apply_discount_to_orders()`**:
   - Move to `ShopifyService.orders.apply_discount()`
   - Uses Order Editing API (orderEditBegin, orderEditAddLineItemDiscount, orderEditCommit)
   - **CLI Command**: `bars shopify order apply-discount <order-number> <discount-type> <discount-value>`

4. **Migrate `product_orders.py`**:
   - Move to `ShopifyService.orders.get_by_product()`
   - Support pagination
   - **CLI Command**: `bars shopify order list-by-product <product-id> [--csv-file]`

### **Phase 5: Inventory Operations** (Medium Priority)

1. **Migrate from `inventory_utils.py`**:
   - `fetch_all_product_variants()` → `ShopifyService.products.get_variants()`
   - `get_inventory_item_id()` → `ShopifyService.inventory.get_item_id()`
   - `update_variant_inventory()` → `ShopifyService.inventory.adjust()`

2. **Migrate from `shopify_query_builders.py`**:
   - `build_adjust_inventory_mutation()` → `ShopifyService.inventory.adjust()`
   - `build_get_inventory_item_and_quantity()` → `ShopifyService.inventory.get_item()`

### **Phase 6: Product Operations** (Medium Priority)

1. **Migrate `get_product_details.py`**:
   - Move to `ShopifyService.products.get_by_id()` / `get_by_handle()`
   - **CLI Command**: `bars shopify product get <id|handle>`

2. **Create product methods**:
   - `ShopifyService.products.create()` - Use `product_creation_request` models
   - `ShopifyService.products.update()`
   - `ShopifyService.products.update_tags()`

### **Phase 7: Page Operations** (Low Priority)

1. **Migrate `shopify_get_page.py`**:
   - Move to `ShopifyService.pages.get()` / `get_theme_asset()`
   - **CLI Command**: `bars shopify page get <handle> [--theme] [--asset]`

2. **Migrate `shopify_update_about_page.py`**:
   - Move to `ShopifyService.pages.update_about_page()`
   - **CLI Command**: `bars shopify page update-about [--bulk-update <csv>] [--block-id] [--upload-and-update]`

### **Phase 8: Analysis/Reporting** (Low Priority - BARS Domain)

1. **`analyze_order_refunds.py`**:
   - This is BARS domain logic (discount calculation)
   - **Recommendation**: Keep in separate service or `bars_cli/commands/analysis/`
   - Uses `shared-utilities/src/utils/discount_calculator.py`
   - **CLI Command**: `bars analysis order-refunds <csv-file> [--output]`

2. **`compare_csv.py`**:
   - General utility, not Shopify-specific
   - **Recommendation**: Move to `bars_cli/commands/utils/compare-csv`

### **Phase 9: Deprecate Old Stack** (Low Priority)

1. **Mark as deprecated**:
   - `client/shopify_client.py` - Add deprecation warnings
   - `client/shopify_service.py` - Add deprecation warnings
   - `models/customers.py`, `models/orders.py`, `models/products/products.py` - Add deprecation warnings

2. **Update all callers**:
   - `OrdersService` → Use new `ShopifyService`
   - `LeadershipService` → Use new `ShopifyService`
   - `ProductsService` / `create_product_complete_process` → Use new `ShopifyService`
   - Any other services using old client

3. **Delete deprecated files**:
   - `client/shopify_config.py` - **DELETE** (after migration)
   - `client/shopify_client.py` - **DELETE** (after migration)
   - `client/shopify_service.py` - **DELETE** (after migration)
   - `models/customers.py` - **DELETE** (after migration)
   - `models/orders.py` - **DELETE** (after migration)
   - `models/products/products.py` - **DELETE** (after migration)
   - `builders/shopify_service_methods_to_update.py` - **DELETE**
   - `builders/fetch_order_details.graphql` - **DELETE**
   - `builders/raw_curl_requests.js` - **DELETE**

## Recommended CLI Command Structure

```
bars shopify
├── customer
│   ├── get <identifier>                    # ✅ DONE
│   ├── update-identifier <id> [--email] [--phone]
│   ├── get-pronouns <identifier>
│   ├── get-birthday <identifier>
│   ├── add-tag <id> <tag>
│   └── get-with-tags <email>
├── order
│   ├── get <identifier>                    # ⚠️ NEXT
│   ├── cancel <order-number> [--notify] [--refund] [--restock] [--reason]
│   ├── refund <order-number> <amount> [--type credit|refund]
│   ├── cancel-and-refund <order-number> [--cancel-reason] [--refund-type]
│   ├── restock <order-number>
│   ├── apply-discount <order-number> <type> <value>
│   └── list-by-product <product-id> [--csv-file]
├── product
│   ├── get <id|handle>                     # ⚠️ TODO
│   ├── get-variants <product-id>
│   ├── create <product-data>
│   ├── update <product-id> <updates>
│   └── update-tags <product-id> <tags>
├── inventory
│   ├── adjust <variant-id> <delta> [--location-id] [--reason]
│   ├── get-item <variant-id>
│   └── get-item-id <variant-id>
└── page
    ├── get <handle> [--theme] [--asset]
    └── update-about [--bulk-update <csv>] [--block-id] [--upload-and-update]
```

## Recommended Service Structure

```python
# backend/modules/integrations/shopify/services/shopify_service.py

class ShopifyService:
    """
    Main Shopify service - Table of Contents for all Shopify operations.
    
    Pure Shopify operations only - no BARS domain logic.
    """
    
    def __init__(self, environment: str = "production"):
        self.client = ShopifySGQLCClient(environment=environment)
    
    # ============================================================================
    # CUSTOMERS
    # ============================================================================
    
    def get_customer_by_identifier(
        self,
        query_params: Dict[str, Any],  # From SHOPIFY_CUSTOMER_IDENTIFIER
        orders_first: int = 5
    ) -> List[Any]:  # Returns sgqlc Type instances
        """Get customer by email, ID, or name. ✅ DONE"""
        ...
    
    def update_identifier(
        self,
        customer_id: str,
        email: Optional[str] = None,
        phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update customer email or phone."""
        ...
    
    def get_with_tags(self, email: str) -> Optional[Dict[str, Any]]:
        """Get customer ID and tags by email."""
        ...
    
    def add_tag(self, customer_id: str, tag: str) -> bool:
        """Add tag to customer."""
        ...
    
    def get_batch(self, emails: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """Get multiple customers with tags in batch."""
        ...
    
    def create_segment(self, name: str, query: str) -> Optional[str]:
        """Create customer segment."""
        ...
    
    def get_pronouns(self, customer_id: str) -> Optional[str]:
        """Extract pronouns from customer's order line item properties."""
        ...
    
    def get_birthday(self, customer_id: str) -> Optional[str]:
        """Extract date of birth from customer's order line item properties."""
        ...
    
    # ============================================================================
    # ORDERS
    # ============================================================================
    
    def get_order_by_identifier(
        self,
        query_params: Dict[str, Any],  # Similar to customer identifier
        line_items_first: int = 5
    ) -> List[Any]:
        """Get order by ID, number, or email. ⚠️ NEXT"""
        ...
    
    def cancel(
        self,
        order_id: str,
        notify_customer: bool = False,
        refund: bool = False,
        restock: bool = False,
        reason: str = "CUSTOMER"
    ) -> Dict[str, Any]:
        """Cancel a Shopify order."""
        ...
    
    def create_refund(
        self,
        order_id: str,
        amount: float,
        refund_type: str = "refund",  # "credit" or "refund"
        notify: bool = True
    ) -> Dict[str, Any]:
        """Create refund for an order."""
        ...
    
    def restock(
        self,
        order_id: str,
        variant_quantities: Dict[str, int]  # variant_id -> quantity
    ) -> Dict[str, Any]:
        """Restock inventory for order line items."""
        ...
    
    def apply_discount(
        self,
        order_id: str,
        discount_type: str,  # "fixed" or "percentage"
        discount_value: float
    ) -> Dict[str, Any]:
        """Apply discount via Order Editing API."""
        ...
    
    def get_by_product(
        self,
        product_id: str,
        cursor: Optional[str] = None
    ) -> Tuple[List[Any], Optional[str]]:  # (orders, next_cursor)
        """Get all orders for a product with pagination."""
        ...
    
    # ============================================================================
    # PRODUCTS
    # ============================================================================
    
    def get_product_by_id(self, product_id: str) -> Optional[Any]:
        """Get product by ID."""
        ...
    
    def get_product_by_handle(self, handle: str) -> Optional[Any]:
        """Get product by handle."""
        ...
    
    def get_variants(self, product_id: str) -> List[Dict[str, Any]]:
        """Get all variants for a product."""
        ...
    
    def create_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new product."""
        ...
    
    def update_product(self, product_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing product."""
        ...
    
    def update_product_tags(self, product_id: str, tags: List[str]) -> Dict[str, Any]:
        """Update product tags."""
        ...
    
    # ============================================================================
    # INVENTORY
    # ============================================================================
    
    def adjust_inventory(
        self,
        inventory_item_id: str,
        delta: int,
        location_id: Optional[str] = None,  # Auto-detect if None
        reason: str = "correction"
    ) -> Dict[str, Any]:
        """Adjust inventory quantity."""
        ...
    
    def get_inventory_item(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """Get inventory item and quantity for a variant."""
        ...
    
    def get_inventory_item_id(self, variant_id: str) -> Optional[str]:
        """Get inventory item ID for a variant."""
        ...
    
    # ============================================================================
    # PAGES
    # ============================================================================
    
    def get_page(self, handle: str) -> Optional[Dict[str, Any]]:
        """Get page content by handle."""
        ...
    
    def get_theme_asset(self, theme_id: str, asset_key: str) -> Optional[Dict[str, Any]]:
        """Get theme template asset."""
        ...
    
    def update_about_page(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update About Us page leadership images."""
        ...
```

## Immediate Actions

1. ✅ **Create `services/shopify_service.py`** with `get_customer_by_identifier()`
2. ✅ **Update CLI** to use new service
3. ⚠️ **Find all `ShopifyConfig` usages** and replace with `config.Shopify.*`
4. ⚠️ **Mark old files as deprecated** with warnings
5. ⚠️ **Create migration checklist** for each deprecated file

## Summary & Key Findings

### **bars-scripts Analysis Summary**

**Total Scripts Analyzed**: 22 Python scripts

**Scripts Already Migrated** (✅):
- `get_customer_details.py` → `bars shopify customer get` ✅
- `get_customer_details_pydantic.py` → Same (✅)
- `get_order_details_pydantic.py` → Ready for migration (service method exists)

**Scripts Requiring Migration** (⚠️):
- **Customer**: 4 scripts (update-identifier, get-pronouns, get-birthday, + utils methods)
- **Order**: 6 scripts (get, cancel, refund, cancel-and-refund, restock, apply-discount, list-by-product)
- **Product**: 1 script (get)
- **Inventory**: 3 utilities (adjust, get-item, get-variants)
- **Page**: 2 scripts (get, update-about)
- **Analysis**: 2 scripts (analyze-refunds, compare-csv - BARS domain)

### **Shared Utilities Migration**

**From `shared_utils.py`** (7 functions):
- ✅ `load_environment()` - Already in `backend/config.py`
- ✅ `get_shopify_config()` - Already in `backend/config.py`
- ⚠️ `make_graphql_request()` - Replace with `ShopifySGQLCClient.execute()`
- ⚠️ `fetch_order()` - Migrate to `ShopifyService.orders.get_by_identifier()`
- ⚠️ `cancel_order()` - Migrate to `ShopifyService.orders.cancel()`
- ⚠️ `create_refund()` - Migrate to `ShopifyService.orders.create_refund()`
- ⚠️ Field constants - Replace with sgqlc recursive selection

**From `inventory_utils.py`** (5 functions):
- ⚠️ All 5 functions need migration to service methods

### **Backend Models Status**

**✅ Ready to Use**:
- All SGQLC models generated from Pydantic (Customer, Order, Product, LineItem, Refund, etc.)
- `ShopifyResponse` for error handling
- `Query` class for recursive field selection
- Bridge for bidirectional conversion

**⚠️ Needs Review**:
- Old models in `models/customers.py`, `models/orders.py`, `models/products/products.py` - **DELETE after migration**

### **Recommended Migration Order**

1. **Phase 1** (Foundation): ✅ Customer get (DONE) → Order get (NEXT)
2. **Phase 2** (Core Operations): Cancel order → Create refund
3. **Phase 3** (Customer Extensions): Update identifier → Extract properties
4. **Phase 4** (Advanced Orders): Restock → Apply discount → List by product
5. **Phase 5** (Inventory): Adjust → Get item → Get variants
6. **Phase 6** (Products): Get → Create → Update
7. **Phase 7** (Pages): Get → Update about
8. **Phase 8** (Analysis): Separate domain service

### **Key Decisions**

1. **BARS Domain Logic**: Keep `analyze_order_refunds` and discount calculation in separate service (not pure Shopify)
2. **Interactive Prompts**: Keep `prompt_restock_selection` in CLI (user interaction)
3. **Order Properties Extraction**: `get_pronouns` and `get_birthday` depend on order service - migrate after orders
4. **Page Operations**: Low priority, specialized use case
5. **CSV Comparison**: General utility, move to `bars_cli/commands/utils/`

## Notes

- **Leadership discounts**: Keep in `LeadershipService` (BARS domain, not pure Shopify)
- **Product creation**: The `product_creation_request` models are BARS-specific - keep them but use new service for Shopify API calls
- **Error handling**: Use `ShopifyResponse` model for consistent error handling
- **Type safety**: Prefer returning sgqlc Type instances, allow conversion to Pydantic via bridge
- **Shared utilities**: All `shared_utils.py` and `inventory_utils.py` functions should migrate to service methods
- **Field selection**: Replace hardcoded field strings with sgqlc recursive selection from `Query` class

