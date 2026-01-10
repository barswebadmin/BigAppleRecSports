# Shopify GraphQL Models

Type-safe Pydantic models for Shopify entities with proper forward references to avoid circular imports.

## Structure

```
models/
├── __init__.py          # Central exports, auto-resolves forward refs
├── common.py            # Shared models (PageInfo, Address)
├── customer.py          # Customer models
└── order.py             # Order models
```

## Usage

### Basic Import

```python
from models import CustomerModel, OrderModel

# Forward references are automatically resolved
customer = CustomerModel(
    id="gid://shopify/Customer/123",
    firstName="John",
    lastName="Doe",
    orders=OrdersConnectionModel(...)  # ✅ Works!
)

order = OrderModel(
    id="gid://shopify/Order/456",
    name="#1001",
    customer=CustomerModel(...)  # ✅ Works!
)
```

### How Forward References Work

**In `customer.py`:**
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .order import OrdersConnectionModel  # Only for type checkers

class CustomerModel(BaseModel):
    orders: Optional["OrdersConnectionModel"] = None  # String annotation
```

**In `order.py`:**
```python
if TYPE_CHECKING:
    from .customer import CustomerModel  # Only for type checkers

class OrderModel(BaseModel):
    customer: Optional["CustomerModel"] = None  # String annotation
```

**Key Points:**
1. `TYPE_CHECKING` is `False` at runtime, so imports don't execute
2. String annotations (`"OrdersConnectionModel"`) defer resolution
3. `model_rebuild()` resolves strings to actual types at runtime
4. No circular import because imports only happen in `TYPE_CHECKING` block

## Example: Query Customer with Orders

```python
from models import CustomerModel, OrdersConnectionModel
from shared_utils import get_shopify_config, make_graphql_request

config = get_shopify_config("production")

query = """
query {
    customer(id: "gid://shopify/Customer/123") {
        id
        firstName
        lastName
        orders(first: 5) {
            edges {
                cursor
                node {
                    id
                    name
                    createdAt
                }
            }
        }
    }
}
"""

response = make_graphql_request({"query": query}, config)
customer_data = response["data"]["customer"]

# Parse into typed model
customer = CustomerModel(**customer_data)

# Access orders (forward reference resolved)
for order in customer.recent_orders:
    print(f"Order: {order.name}")
```

## Example: Query Order with Customer

```python
from models import OrderModel, CustomerModel

query = """
query {
    order(id: "gid://shopify/Order/456") {
        id
        name
        customer {
            id
            firstName
            lastName
            email
        }
    }
}
"""

response = make_graphql_request({"query": query}, config)
order_data = response["data"]["order"]

# Parse into typed model
order = OrderModel(**order_data)

# Access customer (forward reference resolved)
if order.customer:
    print(f"Customer: {order.customer.full_name}")
```

## Adding New Models

When adding a new model that references existing ones:

1. **Create the model file:**
```python
# models/product.py
from typing import TYPE_CHECKING, Optional
from pydantic import BaseModel

if TYPE_CHECKING:
    from .order import OrderModel  # Forward reference

class ProductModel(BaseModel):
    id: str
    title: str
    # No circular import needed!
```

2. **Update `__init__.py`:**
```python
from .product import ProductModel

def resolve_forward_refs():
    # ... existing code ...
    ProductModel.model_rebuild()  # Add this
```

3. **Use string annotations for forward refs:**
```python
class SomeModel(BaseModel):
    related: Optional["OtherModel"] = None  # String, not direct import
```

## Benefits

✅ **No Circular Imports**: `TYPE_CHECKING` prevents runtime circular dependencies  
✅ **Type Safety**: IDEs and type checkers still understand the relationships  
✅ **Clean Separation**: Each entity in its own file  
✅ **Auto-Resolution**: Forward refs resolved automatically on import  


