# Customer Properties Refactor Plan

## Analysis: What Should Move to Backend Service

### ✅ **MOVE TO BACKEND SERVICE** (Service Orchestration & API Calls)

#### 1. `get_order_line_item_properties(shopify_service, order_id)`
**Current:** Calls `shopify_service.get_order_by_identifier()` then extracts properties  
**Should become:** `shopify_service.get_order_line_item_properties(order_id: str) -> List[Dict[str, str]]`

**Rationale:**
- Makes service API calls
- Encapsulates order data access pattern
- Reusable across different contexts (CLI, API, other services)
- Service should own data extraction from its own responses

**Implementation:**
```python
# In ShopifyService
def get_order_line_item_properties(self, order_id: str) -> List[Dict[str, str]]:
    """Get line item custom attributes for an order."""
    orders = self.get_order_by_identifier(
        {"query": f"id:{order_id}", "first": 1},
        line_items_first=50
    )
    if not orders:
        return []
    
    order = orders[0]
    properties = []
    line_items_conn = getattr(order, 'lineItems', None)
    if not line_items_conn:
        return []
    
    nodes = getattr(line_items_conn, 'nodes', None)
    if not nodes:
        return []
    
    for line_item in nodes:
        custom_attrs = getattr(line_item, 'customAttributes', None)
        if custom_attrs:
            for attr in custom_attrs:
                key = getattr(attr, 'key', '')
                value = getattr(attr, 'value', '')
                if key and value:
                    properties.append({"key": key, "value": value})
    
    return properties
```

---

#### 2. `fetch_birthdays_with_names(shopify_service, order_ids)`
**Current:** Orchestrates concurrent calls to `get_order_line_item_properties()`  
**Should become:** `shopify_service.get_customer_birthdays_from_orders(order_ids: List[str]) -> List[Tuple[str, str, str]]`

**Rationale:**
- Orchestrates multiple service calls (concurrent fetching)
- Service should own concurrent execution patterns
- Returns structured data (not raw properties)
- Reusable business logic

**Implementation:**
```python
# In ShopifyService
def get_customer_birthdays_from_orders(self, order_ids: List[str]) -> List[Tuple[str, str, str]]:
    """Fetch birthdays with names from multiple orders concurrently.
    
    Returns:
        List of (birthday, first_name, last_name) tuples
    """
    import concurrent.futures
    from bars_cli.commands.shopify._shared.customer_properties import extract_birthday_with_name
    
    birthday_records = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_order = {
            executor.submit(self.get_order_line_item_properties, order_id): order_id
            for order_id in order_ids
        }
        
        for future in concurrent.futures.as_completed(future_to_order):
            try:
                properties = future.result()
                records = extract_birthday_with_name(properties)
                birthday_records.extend(records)
            except Exception as e:
                logger.error(f"Error fetching order: {e}")
    
    return birthday_records
```

---

#### 3. `fetch_pronouns_with_names(shopify_service, orders_with_dates)`
**Current:** Orchestrates concurrent calls to `get_order_line_item_properties()`  
**Should become:** `shopify_service.get_customer_pronouns_from_orders(orders_with_dates: List[Tuple[str, str]]) -> List[Tuple[str, str, str, str]]`

**Rationale:**
- Same as above - orchestrates service calls
- Returns structured data
- Service should own concurrent execution

**Implementation:**
```python
# In ShopifyService
def get_customer_pronouns_from_orders(self, orders_with_dates: List[Tuple[str, str]]) -> List[Tuple[str, str, str, str]]:
    """Fetch pronouns with names and dates from multiple orders concurrently.
    
    Returns:
        List of (pronouns, first_name, last_name, created_at) tuples
    """
    import concurrent.futures
    from bars_cli.commands.shopify._shared.customer_properties import extract_pronouns_with_name
    
    pronouns_records = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_order = {
            executor.submit(self.get_order_line_item_properties, order_id): (order_id, created_at)
            for order_id, created_at in orders_with_dates
        }
        
        for future in concurrent.futures.as_completed(future_to_order):
            order_id, created_at = future_to_order[future]
            try:
                properties = future.result()
                records = extract_pronouns_with_name(properties)
                for pronouns, first_name, last_name in records:
                    pronouns_records.append((pronouns, first_name, last_name, created_at))
            except Exception as e:
                logger.error(f"Error fetching order {order_id}: {e}")
    
    return pronouns_records
```

---

#### 4. `process_customer_birthday(shopify_service, customer)`
**Current:** High-level orchestration - extracts order IDs, then fetches birthdays  
**Should become:** `shopify_service.get_customer_birthdays(customer_id: str) -> List[Tuple[str, str, str]]`

**Rationale:**
- High-level business operation
- Coordinates multiple service calls
- Should be a single service method for convenience
- Can accept customer_id instead of customer object (more flexible)

**Implementation:**
```python
# In ShopifyService
def get_customer_birthdays(self, customer_id: str) -> List[Tuple[str, str, str]]:
    """Get customer birthdays from their orders.
    
    Args:
        customer_id: Customer ID (gid://shopify/Customer/...)
        
    Returns:
        List of (birthday, first_name, last_name) tuples, sorted by birthday then name
    """
    # Get customer with orders
    customer = self.get_customer_by_identifier(
        {"query": f"id:{customer_id.split('/')[-1]}", "first": 1},
        orders_first=5
    )[0]
    
    # Extract order IDs
    order_ids = self._extract_order_ids_from_customer(customer)
    
    if not order_ids:
        return []
    
    # Fetch birthdays
    birthday_records = self.get_customer_birthdays_from_orders(order_ids)
    
    # Sort by birthday, then by name
    return sorted(birthday_records, key=lambda x: (x[0], x[1], x[2]))
```

---

#### 5. `process_customer_pronouns(shopify_service, customer)`
**Current:** High-level orchestration - extracts order IDs with dates, then fetches pronouns  
**Should become:** `shopify_service.get_customer_pronouns(customer_id: str) -> List[Tuple[str, str, str, str]]`

**Rationale:**
- Same as above - high-level business operation
- Should be a service method

**Implementation:**
```python
# In ShopifyService
def get_customer_pronouns(self, customer_id: str) -> List[Tuple[str, str, str, str]]:
    """Get customer pronouns from their orders.
    
    Args:
        customer_id: Customer ID (gid://shopify/Customer/...)
        
    Returns:
        List of (pronouns, first_name, last_name, created_at) tuples, sorted by most recent first
    """
    # Get customer with orders
    customer = self.get_customer_by_identifier(
        {"query": f"id:{customer_id.split('/')[-1]}", "first": 1},
        orders_first=5
    )[0]
    
    # Extract order IDs with dates
    orders_with_dates = self._extract_order_ids_with_dates_from_customer(customer)
    
    if not orders_with_dates:
        return []
    
    # Fetch pronouns
    pronouns_records = self.get_customer_pronouns_from_orders(orders_with_dates)
    
    # Sort by created_at (most recent first), then by name
    return sorted(pronouns_records, key=lambda x: (x[3], x[1], x[2]), reverse=True)
```

---

### ❌ **KEEP IN CLI/SHARED** (Pure Data Extraction Utilities)

#### 1. `extract_birthday_with_name(properties)`
**Keep in:** `bars_cli/commands/shopify/_shared/customer_properties.py`

**Rationale:**
- Pure data extraction function (no service calls)
- Works on already-extracted properties list
- Utility function that can be used by service methods
- No dependencies on service structure

**Usage:** Service methods can import and use this

---

#### 2. `extract_pronouns_with_name(properties)`
**Keep in:** `bars_cli/commands/shopify/_shared/customer_properties.py`

**Rationale:**
- Same as above - pure data extraction
- Utility function

---

#### 3. `get_customer_orders(customer)`
**Keep in:** `bars_cli/commands/shopify/_shared/customer_properties.py` (or move to service as private helper)

**Rationale:**
- Simple data extraction from customer object
- Could be a private helper in service: `_extract_order_ids_from_customer()`
- Or keep in shared if used by CLI formatting logic

**Recommendation:** Move to service as private helper `_extract_order_ids_from_customer()`

---

#### 4. `get_customer_orders_with_dates(customer)`
**Keep in:** `bars_cli/commands/shopify/_shared/customer_properties.py` (or move to service as private helper)

**Rationale:**
- Same as above
- Could be `_extract_order_ids_with_dates_from_customer()`

**Recommendation:** Move to service as private helper `_extract_order_ids_with_dates_from_customer()`

---

## Recommended Service Methods

Add to `ShopifyService`:

```python
# ============================================================================
# CUSTOMER PROPERTIES (from order line items)
# ============================================================================

def get_order_line_item_properties(self, order_id: str) -> List[Dict[str, str]]:
    """Get line item custom attributes for an order."""
    # Implementation above

def get_customer_birthdays_from_orders(self, order_ids: List[str]) -> List[Tuple[str, str, str]]:
    """Fetch birthdays from multiple orders concurrently."""
    # Implementation above

def get_customer_pronouns_from_orders(self, orders_with_dates: List[Tuple[str, str]]) -> List[Tuple[str, str, str, str]]:
    """Fetch pronouns from multiple orders concurrently."""
    # Implementation above

def get_customer_birthdays(self, customer_id: str) -> List[Tuple[str, str, str]]:
    """Get customer birthdays from their orders (high-level convenience method)."""
    # Implementation above

def get_customer_pronouns(self, customer_id: str) -> List[Tuple[str, str, str, str]]:
    """Get customer pronouns from their orders (high-level convenience method)."""
    # Implementation above

# Private helpers
def _extract_order_ids_from_customer(self, customer: Any) -> List[str]:
    """Extract order IDs from customer object."""
    # Implementation from get_customer_orders()

def _extract_order_ids_with_dates_from_customer(self, customer: Any) -> List[Tuple[str, str]]:
    """Extract order IDs with dates from customer object."""
    # Implementation from get_customer_orders_with_dates()
```

---

## Updated CLI Usage

After refactor, CLI would use:

```python
# In get_customer_cmd.py
if enhance and customers:
    for customer in customers:
        customer_id = getattr(customer, 'id', '')
        
        if json_output:
            # Add to customer data structure
            birthdays = shopify_service.get_customer_birthdays(customer_id)
            pronouns = shopify_service.get_customer_pronouns(customer_id)
            # Add to JSON output
        else:
            # Display formatted output
            birthdays = shopify_service.get_customer_birthdays(customer_id)
            pronouns = shopify_service.get_customer_pronouns(customer_id)
            
            if birthdays:
                console.print("\n[bold cyan]🎂 Birthdays from Orders:[/bold cyan]")
                for bday, first, last in birthdays:
                    name = f"{first} {last}".strip() or "N/A"
                    console.print(f"  {bday} - {name}")
            
            if pronouns:
                console.print("\n[bold cyan]🏳️‍🌈 Pronouns from Orders:[/bold cyan]")
                for pro, first, last, created_at in pronouns:
                    name = f"{first} {last}".strip() or "N/A"
                    console.print(f"  {pro} - {name} (order: {created_at})")
```

---

## Summary

**Move to Service (5 functions):**
1. ✅ `get_order_line_item_properties()` → `shopify_service.get_order_line_item_properties()`
2. ✅ `fetch_birthdays_with_names()` → `shopify_service.get_customer_birthdays_from_orders()`
3. ✅ `fetch_pronouns_with_names()` → `shopify_service.get_customer_pronouns_from_orders()`
4. ✅ `process_customer_birthday()` → `shopify_service.get_customer_birthdays()`
5. ✅ `process_customer_pronouns()` → `shopify_service.get_customer_pronouns()`

**Keep in CLI/Shared (4 functions):**
1. ❌ `extract_birthday_with_name()` - Pure utility, keep in shared
2. ❌ `extract_pronouns_with_name()` - Pure utility, keep in shared
3. ⚠️ `get_customer_orders()` - Move to service as private helper `_extract_order_ids_from_customer()`
4. ⚠️ `get_customer_orders_with_dates()` - Move to service as private helper `_extract_order_ids_with_dates_from_customer()`

**Benefits:**
- Service owns all API orchestration
- CLI becomes simpler (just calls service methods)
- Service methods reusable across contexts
- Better separation of concerns
- Easier to test service methods independently
